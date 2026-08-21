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

_ALL_LABELS = {"Document", "Person", "Org", "Ticket", "Project", "Fact", "Topic", "Deal", "Entity", "Metric"}

from company_brain import config
from company_brain.config import LIVE_DATA_DIR

# In-memory document text cache, for full_body lookups only
_DOCS_CACHE: Dict[str, Dict[str, Any]] = {}


def _get_docs_cache(workspace_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    global _DOCS_CACHE
    if not _DOCS_CACHE:
        # Follow the corpus the API is actually serving. This was hardcoded to the
        # 812-document gold file, so when THEIA_STAGED_DOCS points at the 25,812-doc
        # noisy corpus the other 25,000 documents missed the cache and fell through
        # to a branch that sets `text = title` -- which is why the inspector's
        # "SOURCE TEXT" was just the title repeated back.
        staged_path = Path(config.STAGED_DOCS_PATH)
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


def _search_doc_ids(
    search: str, limit: int, workspace_id: Optional[str] = None
) -> tuple[list, int]:
    """Resolve a free-text query to document ids across the entire staged corpus.

    Matching happens against the in-memory docs cache rather than in Cypher:
    HydraDB 0.1.0 has no usable string-predicate support for this shape, and the
    cache is already loaded to serve node details. Title matches rank above body
    matches so the most obviously relevant documents seed the graph.
    """
    needle = search.strip().lower()
    if not needle:
        return [], 0

    docs = _get_docs_cache(workspace_id=workspace_id)
    title_hits: list = []
    body_hits: list = []
    for doc_id, doc in docs.items():
        title = str(doc.get("title") or "").lower()
        if needle in title:
            title_hits.append(doc_id)
        elif needle in str(doc.get("text") or "").lower():
            body_hits.append(doc_id)

    ranked = title_hits + body_hits
    return ranked[:limit], len(ranked)


@router.get("/topology")
def get_graph_topology(
    doc_limit: int = Query(45, ge=5, le=100, description="Number of seed documents to expand"),
    labels: Optional[str] = Query(None, description="Comma-separated labels to include: Document,Person,Org,Ticket,Project,Topic,Deal,Fact"),
    search: Optional[str] = Query(None, description="Search all documents by title and body; seeds the subgraph from the matches"),
    refresh: bool = Query(False, description="Bypass the topology cache and re-query HydraDB"),
    workspace_id: Optional[str] = Query(None, description="Filter topology to a specific user/workspace"),
):
    """
    Returns a bounded seed subgraph (documents plus their MENTIONS/HAS_FACT
    neighbours) from HydraDB, structured for Cytoscape.js.
    """
    # Search resolves against the WHOLE corpus, then seeds the subgraph from the
    # documents that matched. It previously filtered the ~45 already-cached seed
    # documents by title, so a real query like "multipart" matched none of them
    # and the box returned an empty canvas for almost every term anyone typed.
    seed_doc_ids = None
    matched_total = None
    if search and search.strip():
        seed_doc_ids, matched_total = _search_doc_ids(search, doc_limit, workspace_id)
        if not seed_doc_ids:
            return {
                "nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0,
                "query": search.strip(), "matched_documents": 0,
            }

    try:
        seed = topology_cache.fetch_seed(
            doc_limit=doc_limit, refresh=refresh,
            workspace_id=workspace_id, seed_doc_ids=seed_doc_ids,
        )
    except Exception:
        return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0, "degraded": True}
    nodes, edges = seed["nodes"], seed["edges"]

    allowed_labels = set(labels.split(",")) & _ALL_LABELS if labels else set(_ALL_LABELS)
    nodes, edges = _filter_by_labels(nodes, edges, allowed_labels)

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

    if matched_total is not None:
        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "query": search.strip(),
            "matched_documents": matched_total,
        }

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
                    neighbours.append({"id": n["data"]["id"], "label": n["data"]["label"],
                                       "name": n["data"].get("name") or n["data"]["id"],
                                       "relationship": rel})
            except Exception:
                pass

            # The facts a document asserts are the single most interesting thing
            # about it, and the card omitted them entirely -- so a Document read as
            # a title plus a list of anonymous "MENTIONS Person" rows. Anchored
            # lookup, ~40ms.
            facts = []
            try:
                with GraphClient() as client:
                    rows = client.run(
                        "MATCH (d:Document {doc_id: $did})-[:HAS_FACT]->(f:Fact) "
                        "RETURN f.id AS id, f.subject AS subject, f.attribute AS attribute, "
                        "f.value AS value, f.created_at AS created_at LIMIT 12",
                        {"did": key},
                    )
                for r in rows:
                    subj, val = str(r.get("subject") or ""), str(r.get("value") or "")
                    if not subj or subj.strip().lower() == val.strip().lower():
                        continue  # tautology guard, same rule the query engine applies
                    facts.append({
                        "id": r.get("id"),
                        "subject": subj,
                        "attribute": r.get("attribute"),
                        "value": val,
                        "created_at": r.get("created_at") or "",
                    })
            except Exception:
                pass

            body = doc.get("text", "") or ""
            title = doc.get("title", "Document")
            return {
                "id": node_id,
                "label": "Document",
                "name": title,
                "source": doc.get("source", ""),
                "doc_id": key,
                "created_at": doc.get("created_at", ""),
                # Suppress the body when it is merely the title echoed back: showing
                # the same string twice under a "SOURCE TEXT" heading is worse than
                # showing nothing, because it implies the document has no content.
                "full_body": "" if body.strip() == title.strip() else body,
                "facts": facts,
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
                    neighbours.append({"id": n["data"]["id"], "label": n["data"]["label"],
                                       "name": n["data"].get("name") or n["data"]["id"],
                                       "relationship": "SUPERSEDES"})
            except Exception:
                pass
            if f.get("f.doc_id"):
                neighbours.append({"id": f"doc_{f['f.doc_id']}", "label": "Document",
                                   "name": f.get("d.title") or f["f.doc_id"],
                                   "relationship": "HAS_FACT"})
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
                neighbours.append({"id": n["data"]["id"], "label": n["data"]["label"],
                                       "name": n["data"].get("name") or n["data"]["id"],
                                       "relationship": rel})
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
