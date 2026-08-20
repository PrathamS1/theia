"""
server/routes/health.py — Health and system status endpoints.

Queries real-time status and live element counts from HydraDB and Vector Store.
"""

from fastapi import APIRouter
from company_brain.graph.client import GraphClient
from company_brain.indexing.vector_store import VectorStore

router = APIRouter(prefix="/api", tags=["Health"])


_VSTORE = None


def _get_vstore():
    global _VSTORE
    if _VSTORE is None:
        _VSTORE = VectorStore()
        _VSTORE.load()
    return _VSTORE


@router.get("/health")
def get_health():
    """
    Returns system health, HydraDB connection status, and graph element counts dynamically.
    """
    hydra_ok = False
    doc_count = 0
    person_count = 0
    org_count = 0
    topic_count = 0
    fact_count = 0

    try:
        with GraphClient() as client:
            hydra_ok = client.ping()
            if hydra_ok:
                doc_res = client.run("MATCH (d:Document) RETURN count(*)")
                person_res = client.run("MATCH (p:Person) RETURN count(*)")
                org_res = client.run("MATCH (o:Org) RETURN count(*)")
                topic_res = client.run("MATCH (t:Topic) RETURN count(*)")
                fact_res = client.run("MATCH (f:Fact) RETURN count(*)")

                doc_count = doc_res[0].get("count(*)", 0) if doc_res else 0
                person_count = person_res[0].get("count(*)", 0) if person_res else 0
                org_count = org_res[0].get("count(*)", 0) if org_res else 0
                topic_count = topic_res[0].get("count(*)", 0) if topic_res else 0
                fact_count = fact_res[0].get("count(*)", 0) if fact_res else 0
    except Exception:
        hydra_ok = False

    vstore = _get_vstore()
    vstore_loaded = (vstore.chunk_embeddings is not None or vstore.doc_embeddings is not None)
    vector_count = len(vstore.chunks_meta) if (vstore_loaded and vstore.chunks_meta) else len(vstore.doc_ids)

    return {
        "status": "healthy" if hydra_ok and vstore_loaded else "degraded",
        "hydradb_connected": hydra_ok,
        "vector_store_loaded": vstore_loaded,
        "total_documents": doc_count,
        "total_persons": person_count,
        "total_orgs": org_count,
        "total_topics": topic_count,
        "total_facts": fact_count,
        "total_vectors": vector_count,
    }
