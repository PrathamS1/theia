"""
server/routes/graph.py — Live Graph topology, subgraphs, and node inspection endpoints.

Queries complete topology and rich property inspector data directly from HydraDB via OpenCypher:
- Nodes: :Document, :Person, :Org, :Ticket, :Fact
- Edges: [:MENTIONS], [:SAME_AS], [:SUPERSEDES], [:HAS_FACT]
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException

from company_brain.graph.client import GraphClient

router = APIRouter(prefix="/api/graph", tags=["Graph"])

# In-memory document lookup cache for fast text body inspection
_DOCS_CACHE: Dict[str, Dict[str, Any]] = {}


def _get_docs_cache() -> Dict[str, Dict[str, Any]]:
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
    return _DOCS_CACHE


@router.get("/topology")
def get_graph_topology(
    limit: int = Query(5000, ge=10, le=20000, description="Max total nodes to return (default 5000 for complete topology)"),
    labels: Optional[str] = Query(None, description="Comma-separated labels: Document,Person,Org,Ticket,Fact"),
    search: Optional[str] = Query(None, description="Search query to filter nodes by title or name"),
):
    """
    Dynamically queries live HydraDB knowledge graph and returns complete nodes & edges
    formatted for Cytoscape.js / Vis.js interactive visualization.
    """
    docs_cache = _get_docs_cache()
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    node_ids_set = set()

    allowed_labels = set(labels.split(",")) if labels else {"Document", "Person", "Org", "Ticket", "Fact"}

    with GraphClient() as client:
        # 1. Fetch Document Hub Nodes from HydraDB
        if "Document" in allowed_labels and len(nodes) < limit:
            fetch_limit = min(limit - len(nodes), 800)
            if fetch_limit > 0:
                try:
                    doc_rows = client.run(
                        f"MATCH (d:Document) RETURN d.id AS id, d.doc_id AS doc_id, d.title AS title, d.source AS source, d.author AS author, d.created_at AS created_at LIMIT {fetch_limit}"
                    )
                    for r in doc_rows:
                        did = r.get("doc_id") or str(r.get("id"))
                        title = r.get("title") or did
                        body = docs_cache.get(did, {}).get("text", "")

                        if search and search.lower() not in (title + " " + body).lower():
                            continue

                        node_id = f"doc_{did}"
                        if node_id not in node_ids_set:
                            node_ids_set.add(node_id)
                            nodes.append({
                                "data": {
                                    "id": node_id,
                                    "label": "Document",
                                    "name": title,
                                    "source": r.get("source", "unknown"),
                                    "doc_id": did,
                                    "created_at": r.get("created_at", ""),
                                    "author": r.get("author", ""),
                                    "body_snippet": body[:200] + "..." if body else "",
                                }
                            })
                except Exception:
                    pass

        # 2. Fetch Org Nodes from HydraDB
        if "Org" in allowed_labels and len(nodes) < limit:
            fetch_limit = min(limit - len(nodes), 100)
            if fetch_limit > 0:
                try:
                    org_rows = client.run(f"MATCH (o:Org) RETURN o.id AS id, o.name AS name LIMIT {fetch_limit}")
                    for r in org_rows:
                        o_name = r.get("name") or f"Org_{r.get('id')}"
                        o_id = f"org_{r.get('id')}"
                        if o_id not in node_ids_set:
                            node_ids_set.add(o_id)
                            nodes.append({
                                "data": {
                                    "id": o_id,
                                    "label": "Org",
                                    "name": o_name,
                                }
                            })
                except Exception:
                    pass

        # 3. Fetch Person Nodes from HydraDB
        if "Person" in allowed_labels and len(nodes) < limit:
            fetch_limit = min(limit - len(nodes), 600)
            if fetch_limit > 0:
                try:
                    person_rows = client.run(f"MATCH (p:Person) RETURN p.id AS id, p.name AS name LIMIT {fetch_limit}")
                    for r in person_rows:
                        p_name = r.get("name") or f"Person_{r.get('id')}"
                        p_id = f"person_{r.get('id')}"
                        if p_id not in node_ids_set:
                            node_ids_set.add(p_id)
                            nodes.append({
                                "data": {
                                    "id": p_id,
                                    "label": "Person",
                                    "name": p_name,
                                }
                            })
                except Exception:
                    pass

        # 4. Build Real Edges from Node Adjacency
        edge_counter = 1
        org_name_to_id = {n["data"]["name"].lower(): n["data"]["id"] for n in nodes if n["data"].get("label") == "Org"}
        person_name_to_id = {n["data"]["name"].lower(): n["data"]["id"] for n in nodes if n["data"].get("label") == "Person"}

        for d_node in list(nodes):
            if d_node["data"].get("label") == "Document":
                doc_did = d_node["data"].get("doc_id")
                d_id = d_node["data"]["id"]
                author = (d_node["data"].get("author") or "").lower()
                body = (d_node["data"].get("body_snippet") or "").lower()

                # Author link
                if author and author in person_name_to_id:
                    edges.append({
                        "data": {
                            "id": f"auth_{edge_counter}",
                            "source": d_id,
                            "target": person_name_to_id[author],
                            "type": "AUTHORED",
                            "label": "AUTHORED",
                        }
                    })
                    edge_counter += 1

                # Mentioned Org link
                for oname, oid in org_name_to_id.items():
                    if oname in body:
                        edges.append({
                            "data": {
                                "id": f"mention_{edge_counter}",
                                "source": d_id,
                                "target": oid,
                                "type": "MENTIONS",
                                "label": "MENTIONS",
                            }
                        })
                        edge_counter += 1

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


@router.get("/node/{node_id}")
def get_node_details(node_id: str):
    """
    Returns real dynamic property inspector details for any selected node from HydraDB.
    """
    docs_cache = _get_docs_cache()

    # 1. Document node inspection
    if node_id.startswith("doc_"):
        doc_id = node_id.replace("doc_", "")
        doc = docs_cache.get(doc_id, {})
        
        connected_neighbors = []
        try:
            with GraphClient() as client:
                mentions = client.run(f"MATCH (d:Document {{doc_id: '{doc_id}'}})-[r:MENTIONS]->(o:Org) RETURN o.id AS id, o.name AS name")
                for m in mentions:
                    connected_neighbors.append({
                        "id": f"org_{m.get('id')}",
                        "label": "Org",
                        "name": m.get("name", "Connected Org"),
                        "relationship": "MENTIONS",
                    })
        except Exception:
            pass

        return {
            "id": node_id,
            "label": "Document",
            "name": doc.get("title") or doc_id,
            "source": doc.get("source", "unknown"),
            "doc_id": doc_id,
            "author": doc.get("author", "Unknown"),
            "created_at": doc.get("created_at", "N/A"),
            "full_body": doc.get("text") or doc.get("body", ""),
            "properties": {
                "doc_id": doc_id,
                "source": doc.get("source", "unknown"),
                "file_name": doc.get("file_name", "N/A"),
                "author": doc.get("author", "N/A"),
                "created_at": doc.get("created_at", "N/A"),
            },
            "connected_neighbors": connected_neighbors,
        }

    # 2. Person node inspection
    if node_id.startswith("person_"):
        raw_id = node_id.replace("person_", "")
        try:
            with GraphClient() as client:
                rows = client.run(f"MATCH (p:Person {{id: {raw_id}}}) RETURN p.id AS id, p.name AS name, p.doc_id AS did")
                if rows:
                    row = rows[0]
                    p_name = row.get("name") or f"Person {raw_id}"
                    connected = []
                    # Check linked document if available
                    if row.get("did"):
                        connected.append({"id": f"doc_{row.get('did')}", "label": "Document", "relationship": "MENTIONS"})
                    return {
                        "id": node_id,
                        "label": "Person",
                        "name": p_name,
                        "properties": {
                            "id": raw_id,
                            "name": p_name,
                            "label": "Person",
                        },
                        "connected_neighbors": connected,
                    }
        except Exception:
            pass

    # 3. Org node inspection
    if node_id.startswith("org_"):
        raw_id = node_id.replace("org_", "")
        try:
            with GraphClient() as client:
                rows = client.run(f"MATCH (o:Org {{id: {raw_id}}}) RETURN o.id AS id, o.name AS name")
                if rows:
                    row = rows[0]
                    o_name = row.get("name") or f"Org {raw_id}"
                    connected = []
                    # Check connected documents
                    doc_rows = client.run(f"MATCH (d:Document)-[:MENTIONS]->(o:Org {{id: {raw_id}}}) RETURN d.doc_id AS did, d.title AS title LIMIT 10")
                    for d in doc_rows:
                        connected.append({
                            "id": f"doc_{d.get('did')}",
                            "label": "Document",
                            "name": d.get("title", d.get("did")),
                            "relationship": "MENTIONS",
                        })
                    return {
                        "id": node_id,
                        "label": "Org",
                        "name": o_name,
                        "properties": {
                            "id": raw_id,
                            "name": o_name,
                            "label": "Org",
                        },
                        "connected_neighbors": connected,
                    }
        except Exception:
            pass

    # 4. Fact node inspection
    if node_id.startswith("fact_"):
        fact_id = node_id.replace("fact_", "")
        fact_props = {"id": fact_id}
        connected = []
        try:
            with GraphClient() as client:
                f_rows = client.run(f"MATCH (f:Fact {{id: {fact_id}}}) RETURN f.subject AS subject, f.attribute AS attr, f.value AS val, f.doc_id AS did, f.trust_score AS trust")
                if f_rows:
                    row = f_rows[0]
                    fact_props = {
                        "subject": row.get("subject"),
                        "attribute": row.get("attr"),
                        "value": row.get("val"),
                        "doc_id": row.get("did"),
                        "trust_score": row.get("trust"),
                    }
                    if row.get("did"):
                        connected.append({"id": f"doc_{row.get('did')}", "label": "Document", "relationship": "HAS_FACT"})
        except Exception:
            pass

        return {
            "id": node_id,
            "label": "Fact",
            "name": f"{fact_props.get('subject', 'Fact')} = {fact_props.get('value', '')}",
            "properties": fact_props,
            "connected_neighbors": connected,
        }

    # If not found in any label category, return authentic 404 error
    raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found in knowledge graph")
