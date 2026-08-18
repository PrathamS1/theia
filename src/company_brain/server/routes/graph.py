"""
server/routes/graph.py — Graph topology, subgraphs, and node inspection endpoints.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException

from company_brain.graph.client import GraphClient

router = APIRouter(prefix="/api/graph", tags=["Graph"])

# In-memory document lookup cache for fast text inspection
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
    limit: int = Query(250, ge=10, le=1000, description="Max nodes to return"),
    labels: Optional[str] = Query(None, description="Comma-separated labels to include: Document,Person,Org,Ticket,Fact"),
    search: Optional[str] = Query(None, description="Search query to filter nodes by title or name"),
):
    """
    Returns graph nodes and edges structured for Cytoscape.js interactive visualization.
    """
    docs_cache = _get_docs_cache()
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    node_ids_set = set()

    allowed_labels = set(labels.split(",")) if labels else {"Document", "Person", "Org", "Ticket", "Fact"}

    # 1. Build Nodes from Document Hubs
    doc_count = 0
    for doc_id, doc in docs_cache.items():
        if "Document" not in allowed_labels:
            break
        if search and search.lower() not in (doc.get("title", "") + " " + doc.get("body", "")).lower():
            continue

        doc_node_id = f"doc_{doc_id}"
        if doc_node_id not in node_ids_set:
            node_ids_set.add(doc_node_id)
            nodes.append({
                "data": {
                    "id": doc_node_id,
                    "label": "Document",
                    "name": doc.get("title") or doc.get("doc_id", "Doc"),
                    "source": doc.get("source", "unknown"),
                    "doc_id": doc_id,
                    "created_at": doc.get("created_at", ""),
                    "author": doc.get("author", ""),
                    "body_snippet": (doc.get("body") or "")[:200] + "...",
                }
            })
            doc_count += 1
            if doc_count >= min(limit, 100):
                break

    # 2. Extract Entities and Facts linked to these documents
    edge_idx = 1
    for doc_id, doc in docs_cache.items():
        doc_node_id = f"doc_{doc_id}"
        if doc_node_id not in node_ids_set:
            continue

        # Linked Person
        author = doc.get("author")
        if author and "Person" in allowed_labels:
            person_id = f"person_{author.lower().replace(' ', '_')}"
            if person_id not in node_ids_set and len(nodes) < limit:
                node_ids_set.add(person_id)
                nodes.append({
                    "data": {
                        "id": person_id,
                        "label": "Person",
                        "name": author,
                        "source": doc.get("source", ""),
                    }
                })
            if person_id in node_ids_set:
                edges.append({
                    "data": {
                        "id": f"e_{edge_idx}",
                        "source": doc_node_id,
                        "target": person_id,
                        "type": "AUTHORED",
                        "label": "AUTHORED",
                    }
                })
                edge_idx += 1

    # 3. Add Sample SAME_AS Identity Resolution Edges
    sample_same_as = [
        {"source": "person_s_ratnaparkhi", "target": "person_soham", "name1": "S. Ratnaparkhi", "name2": "Soham", "conf": 1.0},
        {"source": "person_lina", "target": "person_lina_gomez", "name1": "Lina", "name2": "Lina Gomez", "conf": 1.0},
        {"source": "person_siddharth", "target": "person_siddharth_deshmukh", "name1": "Siddharth", "name2": "Siddharth Deshmukh", "conf": 1.0},
        {"source": "person_priya", "target": "person_priya_sharma", "name1": "Priya", "name2": "Priya Sharma", "conf": 0.95},
        {"source": "person_alex", "target": "person_alex_chen", "name1": "Alex", "name2": "Alex Chen", "conf": 1.0},
    ]
    for pair in sample_same_as:
        if "Person" in allowed_labels:
            if pair["source"] not in node_ids_set and len(nodes) < limit:
                node_ids_set.add(pair["source"])
                nodes.append({"data": {"id": pair["source"], "label": "Person", "name": pair["name1"]}})
            if pair["target"] not in node_ids_set and len(nodes) < limit:
                node_ids_set.add(pair["target"])
                nodes.append({"data": {"id": pair["target"], "label": "Person", "name": pair["name2"]}})
            if pair["source"] in node_ids_set and pair["target"] in node_ids_set:
                edges.append({
                    "data": {
                        "id": f"sameas_{edge_idx}",
                        "source": pair["source"],
                        "target": pair["target"],
                        "type": "SAME_AS",
                        "label": "SAME_AS",
                        "confidence": pair["conf"],
                    }
                })
                edge_idx += 1

    # 4. Add Sample SUPERSEDES Conflict Override Edges
    sample_supersedes = [
        {
            "id_active": "fact_burst_30",
            "id_old": "fact_burst_15",
            "name_active": "Streamly AI burst reservation = 30%",
            "name_old": "Streamly AI burst reservation = 15%",
            "subject": "Streamly AI dp-132-usw",
            "reason": "Updated capacity addendum overrides baseline spec",
        },
        {
            "id_active": "fact_latency_18ms",
            "id_old": "fact_latency_50ms",
            "name_active": "Edge proxy p99 SLA = 18ms",
            "name_old": "Edge proxy p99 SLA = 50ms",
            "subject": "Edge Proxy",
            "reason": "Q3 network optimization supersedes Q1 SLA",
        },
        {
            "id_active": "fact_upload_10mib",
            "id_old": "fact_upload_5mib",
            "name_active": "Multipart max_file_size = 10MiB",
            "name_old": "Multipart max_file_size = 5MiB",
            "subject": "Multipart Validation",
            "reason": "PR 18421 increased upload ceiling",
        },
    ]
    for conf in sample_supersedes:
        if "Fact" in allowed_labels:
            if conf["id_active"] not in node_ids_set and len(nodes) < limit:
                node_ids_set.add(conf["id_active"])
                nodes.append({"data": {"id": conf["id_active"], "label": "Fact", "name": conf["name_active"], "is_active": True, "subject": conf["subject"]}})
            if conf["id_old"] not in node_ids_set and len(nodes) < limit:
                node_ids_set.add(conf["id_old"])
                nodes.append({"data": {"id": conf["id_old"], "label": "Fact", "name": conf["name_old"], "is_active": False, "subject": conf["subject"]}})
            if conf["id_active"] in node_ids_set and conf["id_old"] in node_ids_set:
                edges.append({
                    "data": {
                        "id": f"super_{edge_idx}",
                        "source": conf["id_active"],
                        "target": conf["id_old"],
                        "type": "SUPERSEDES",
                        "label": "SUPERSEDES",
                        "reason": conf["reason"],
                    }
                })
                edge_idx += 1

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


@router.get("/node/{node_id}")
def get_node_details(node_id: str):
    """
    Returns full property inspector details for a selected node.
    """
    docs_cache = _get_docs_cache()

    # If it's a document node
    if node_id.startswith("doc_"):
        doc_id = node_id.replace("doc_", "")
        doc = docs_cache.get(doc_id)
        if doc:
            return {
                "id": node_id,
                "label": "Document",
                "name": doc.get("title", "Document"),
                "source": doc.get("source", ""),
                "doc_id": doc_id,
                "author": doc.get("author", ""),
                "created_at": doc.get("created_at", ""),
                "full_body": doc.get("body", ""),
                "properties": {
                    "doc_id": doc_id,
                    "source": doc.get("source", ""),
                    "author": doc.get("author", ""),
                    "created_at": doc.get("created_at", ""),
                },
                "connected_neighbors": [
                    {"id": f"person_{doc.get('author', '').lower()}", "label": "Person", "relationship": "AUTHORED"}
                ] if doc.get("author") else [],
            }

    # If it's a fact node
    if node_id.startswith("fact_"):
        return {
            "id": node_id,
            "label": "Fact",
            "name": node_id.replace("fact_", "").replace("_", " ").title(),
            "properties": {
                "fact_id": node_id,
                "status": "Active Grounded Proposition",
            },
            "connected_neighbors": [
                {"id": "doc_sample", "label": "Document", "relationship": "HAS_FACT"}
            ],
        }

    # Default fallback
    return {
        "id": node_id,
        "label": "Entity",
        "name": node_id.replace("_", " ").title(),
        "properties": {"entity_id": node_id},
        "connected_neighbors": [],
    }
