"""
server/routes/graph.py — Graph topology, subgraphs, and node inspection endpoints.

Backed by the real HydraDB graph via company_brain.graph.topology (previously
this module read data/staged_gold_docs.json and appended a handful of
hardcoded SAME_AS/SUPERSEDES literals -- it never queried HydraDB at all).
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException

from company_brain.graph.client import GraphClient
from company_brain.graph.topology import cache as topology_cache, _ID_PREFIX

router = APIRouter(prefix="/api/graph", tags=["Graph"])

_ALL_LABELS = {"Document", "Person", "Org", "Ticket", "Project", "Fact", "Topic", "Deal", "Entity"}

from company_brain.config import LIVE_DATA_DIR

# In-memory document text cache, for full_body lookups only
_DOCS_CACHE: Dict[str, Dict[str, Any]] = {}


def _get_docs_cache(workspace_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    global _DOCS_CACHE
    if not _DOCS_CACHE:
        staged_path = Path("data/staged_gold_docs.json")
        if staged_path.exists():
            with open(staged_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _DOCS_CACHE = data
                elif isinstance(data, list):
                    for d in data:
                        doc_id = d.get("doc_id")
                        if doc_id:
                            _DOCS_CACHE[doc_id] = d
    if workspace_id:
        live_staged_path = LIVE_DATA_DIR / workspace_id / "live_staged_docs.json"
        if live_staged_path.exists():
            try:
                with open(live_staged_path, "r", encoding="utf-8") as f:
                    live_data = json.load(f)
                    combined = dict(_DOCS_CACHE)
                    combined.update(live_data)
                    return combined
            except Exception:
                pass
    return _DOCS_CACHE


def _filter_by_labels(nodes: List[Dict], edges: List[Dict], allowed: set) -> tuple:
    """Keeps nodes whose label is allowed; keeps edges only if both endpoints survive."""
    kept_nodes = [n for n in nodes if n["data"]["label"] in allowed]
    kept_ids = {n["data"]["id"] for n in kept_nodes}
    kept_edges = [e for e in edges if e["data"]["source"] in kept_ids and e["data"]["target"] in kept_ids]
    return kept_nodes, kept_edges


@router.get("/topology")
def get_graph_topology(
    doc_limit: int = Query(45, ge=5, le=100, description="Number of seed documents to expand"),
    labels: Optional[str] = Query(None, description="Comma-separated labels to include: Document,Person,Org,Ticket,Project,Topic,Deal,Fact"),
    search: Optional[str] = Query(None, description="Filter documents by title (applies to the currently cached seed only)"),
    refresh: bool = Query(False, description="Bypass the topology cache and re-query HydraDB"),
    workspace_id: Optional[str] = Query(None, description="Filter topology to a specific user/workspace"),
):
    """
    Returns a bounded seed subgraph (documents plus their MENTIONS/HAS_FACT
    neighbours) from HydraDB, structured for Cytoscape.js.
    """
    try:
        seed = topology_cache.fetch_seed(doc_limit=doc_limit, refresh=refresh, workspace_id=workspace_id)
    except Exception:
        return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0, "degraded": True}
    nodes, edges = seed["nodes"], seed["edges"]

    allowed_labels = set(labels.split(",")) & _ALL_LABELS if labels else set(_ALL_LABELS)
    nodes, edges = _filter_by_labels(nodes, edges, allowed_labels)

    if search and search.strip():
        needle = search.strip().lower()
        doc_ids_kept = {
            n["data"]["id"] for n in nodes
            if n["data"]["label"] == "Document" and needle in n["data"]["name"].lower()
        }
        # Keep matching documents plus anything connected to them; drop unrelated documents.
        connected_to_match = {
            e["data"]["target"] if e["data"]["source"] in doc_ids_kept else e["data"]["source"]
            for e in edges
            if e["data"]["source"] in doc_ids_kept or e["data"]["target"] in doc_ids_kept
        }
        keep_ids = doc_ids_kept | connected_to_match
        nodes = [n for n in nodes if n["data"]["id"] in keep_ids]
        edges = [e for e in edges if e["data"]["source"] in keep_ids and e["data"]["target"] in keep_ids]

    # Layer in the full identity-resolution and supersession edge sets, but
    # only where both endpoints are already present in this seed -- keeps the
    # payload bounded while still surfacing SAME_AS/SUPERSEDES when relevant.
    node_ids = {n["data"]["id"] for n in nodes}
    if "Person" in allowed_labels:
        for e in topology_cache.fetch_same_as(workspace_id=workspace_id):
            if e["data"]["source"] in node_ids and e["data"]["target"] in node_ids:
                edges.append(e)
    if "Fact" in allowed_labels:
        for e in topology_cache.fetch_supersedes(workspace_id=workspace_id):
            if e["data"]["source"] in node_ids and e["data"]["target"] in node_ids:
                edges.append(e)

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


@router.get("/expand")
def expand_node(
    node_id: str = Query(..., description="Cytoscape node id, e.g. doc_<doc_id> or person_<int_id>"),
    label: str = Query(..., description="Node label: Document, Person, Org, Ticket, Project, or Fact"),
    workspace_id: Optional[str] = Query(None, description="Workspace isolation ID"),
):
    """
    Returns the 1-hop neighbourhood of a single node (anchored Cypher lookup,
    ~10-75ms) so the client can graft it onto the existing canvas without a
    full topology refetch.
    """
    if label not in _ALL_LABELS:
        raise HTTPException(status_code=400, detail=f"Unknown label '{label}'")

    prefix = f"{_ID_PREFIX.get(label, label.lower())}_"
    if not node_id.startswith(prefix):
        raise HTTPException(status_code=400, detail="node_id does not match the given label")
    key = node_id[len(prefix):]

    try:
        result = topology_cache.expand_node(label, key, workspace_id=workspace_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"HydraDB query failed: {exc}")

    return {
        "nodes": result["nodes"],
        "edges": result["edges"],
        "total_nodes": len(result["nodes"]),
        "total_edges": len(result["edges"]),
    }


@router.get("/node/{node_id}")
def get_node_details(
    node_id: str,
    workspace_id: Optional[str] = Query(None, description="Workspace isolation ID"),
):
    """
    Returns full property inspector details for a selected node, reading live
    property values from HydraDB (anchored by id) plus, for documents, the
    full source text from the staged corpus cache.
    """
    for label in _ALL_LABELS:
        prefix = f"{_ID_PREFIX.get(label, label.lower())}_"
        if not node_id.startswith(prefix):
            continue
        key = node_id[len(prefix):]

        if label == "Document":
            docs_cache = _get_docs_cache(workspace_id=workspace_id)
            doc = docs_cache.get(key)
            if not doc:
                # Fallback: Query HydraDB for this document node
                try:
                    with GraphClient() as client:
                        if workspace_id:
                            rows = client.run(
                                "MATCH (d:Document {doc_id: $did, workspace_id: $ws}) "
                                "RETURN d.doc_id, d.title, d.source, d.created_at",
                                {"did": key, "ws": workspace_id}
                            )
                        else:
                            rows = client.run(
                                "MATCH (d:Document {doc_id: $did}) "
                                "RETURN d.doc_id, d.title, d.source, d.created_at",
                                {"did": key}
                            )
                        if rows:
                            r = rows[0]
                            doc = {
                                "doc_id": r.get("d.doc_id", key),
                                "title": r.get("d.title", key),
                                "source": r.get("d.source", ""),
                                "created_at": r.get("d.created_at", ""),
                                "text": r.get("d.title", key),
                            }
                except Exception:
                    pass
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
            neighbours = []
            try:
                exp = topology_cache.expand_node("Document", key, workspace_id=workspace_id)
                for n in exp["nodes"][:12]:
                    rel = "HAS_FACT" if n["data"]["label"] == "Fact" else "MENTIONS"
                    neighbours.append({"id": n["data"]["id"], "label": n["data"]["label"], "relationship": rel})
            except Exception:
                pass
            return {
                "id": node_id,
                "label": "Document",
                "name": doc.get("title", "Document"),
                "source": doc.get("source", ""),
                "doc_id": key,
                "created_at": doc.get("created_at", ""),
                "full_body": doc.get("text", ""),
                "properties": {
                    "doc_id": key,
                    "source": doc.get("source", ""),
                    "file_name": doc.get("file_name", ""),
                },
                "connected_neighbors": neighbours,
            }

        if label == "Fact":
            try:
                with GraphClient() as client:
                    rows = client.run(
                        "MATCH (f:Fact {id: $fid}) "
                        "RETURN f.subject, f.attribute, f.value, f.trust_score, f.doc_id",
                        {"fid": int(key)},
                    )
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"HydraDB query failed: {exc}")
            if not rows:
                raise HTTPException(status_code=404, detail="Fact not found")
            f = rows[0]
            neighbours = []
            try:
                exp = topology_cache.expand_node("Fact", key, workspace_id=workspace_id)
                for n in exp["nodes"][:8]:
                    neighbours.append({"id": n["data"]["id"], "label": n["data"]["label"], "relationship": "SUPERSEDES"})
            except Exception:
                pass
            if f.get("f.doc_id"):
                neighbours.append({"id": f"doc_{f['f.doc_id']}", "label": "Document", "relationship": "HAS_FACT"})
            return {
                "id": node_id,
                "label": "Fact",
                "name": f"{f.get('f.subject','')} · {f.get('f.attribute','')} = {f.get('f.value','')}",
                "properties": {
                    "subject": f.get("f.subject", ""),
                    "attribute": f.get("f.attribute", ""),
                    "value": f.get("f.value", ""),
                    "trust_score": f.get("f.trust_score", ""),
                    "doc_id": f.get("f.doc_id", ""),
                },
                "connected_neighbors": neighbours,
            }

        # Person / Org / Ticket / Project / Topic / Deal / Entity
        try:
            with GraphClient() as client:
                try:
                    eid = int(key)
                except ValueError:
                    from company_brain.graph.schema import string_to_int_id
                    eid = string_to_int_id(key)

                if workspace_id:
                    rows = client.run(
                        f"MATCH (e:{label} {{id: $eid, workspace_id: $ws}}) RETURN e.name, e.source",
                        {"eid": eid, "ws": workspace_id},
                    )
                else:
                    rows = client.run(
                        f"MATCH (e:{label} {{id: $eid}}) RETURN e.name, e.source",
                        {"eid": eid},
                    )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"HydraDB query failed: {exc}")
        if not rows:
            raise HTTPException(status_code=404, detail=f"{label} not found")
        e = rows[0]
        neighbours = []
        try:
            exp = topology_cache.expand_node(label, key, workspace_id=workspace_id)
            for n in exp["nodes"][:12]:
                rel = "SAME_AS" if n["data"]["label"] == "Person" and label == "Person" else "MENTIONS"
                neighbours.append({"id": n["data"]["id"], "label": n["data"]["label"], "relationship": rel})
        except Exception:
            pass
        return {
            "id": node_id,
            "label": label,
            "name": e.get("e.name", node_id),
            "source": e.get("e.source", ""),
            "properties": {"id": key, "source": e.get("e.source", "")},
            "connected_neighbors": neighbours,
        }

    # Fallback for unrecognised id shapes.
    return {
        "id": node_id,
        "label": "Entity",
        "name": node_id.replace("_", " ").title(),
        "properties": {"entity_id": node_id},
        "connected_neighbors": [],
    }


# Warms the topology cache once, in the background, at process start (this
# module is imported exactly once by server/app.py) so the first dashboard
# load doesn't pay the ~0.8-1.6s cold-fetch cost.
topology_cache.warm()
