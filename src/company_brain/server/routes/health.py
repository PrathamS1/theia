"""
server/routes/health.py — Health and system status endpoints.

Queries real-time status and live element counts from HydraDB and Vector Store.
"""

import logging
import threading
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter
from company_brain import config
from company_brain.graph.client import GraphClient
from company_brain.indexing.vector_store import VectorStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Health"])


_VSTORE = None

# Label counts are unanchored scans. HydraDB 0.1.0 has no label-cardinality
# index, so cost grows with the graph: at ~26k documents / ~209k facts the Fact
# scan exceeds the server's 30s statement timeout while the others still return.
#
# So: never block the request on them. Serve the last known values immediately
# and refresh in the background. A label that cannot be counted reports null
# rather than 0 -- "we could not measure this" and "this is empty" are different
# claims, and rendering the second when the first is true is how a healthy graph
# ends up looking broken on screen.
_COUNT_LABELS = ("Document", "Person", "Org", "Topic", "Fact")
_COUNT_TTL_SECONDS = 120.0

_counts: Dict[str, Optional[int]] = {label: None for label in _COUNT_LABELS}
_counts_at: float = 0.0
_refreshing = threading.Lock()


def _refresh_counts() -> None:
    """Recount every label independently so one timeout cannot void the rest."""
    global _counts_at
    if not _refreshing.acquire(blocking=False):
        return  # a refresh is already in flight
    try:
        with GraphClient() as client:
            for label in _COUNT_LABELS:
                try:
                    rows = client.run(f"MATCH (n:{label}) RETURN count(*) AS n")
                    if rows:
                        _counts[label] = rows[0].get("n")
                except Exception as exc:
                    # Keep the previous value; a timeout is not evidence of zero.
                    logger.debug("count(%s) failed: %s", label, str(exc)[:120])
        _counts_at = time.time()
    except Exception as exc:
        logger.debug("count refresh failed: %s", str(exc)[:120])
    finally:
        _refreshing.release()


def _get_vstore():
    global _VSTORE
    if _VSTORE is None:
        _VSTORE = VectorStore()
        # Same index the query engine serves, so the reported vector count and the
        # searched corpus can never disagree.
        _VSTORE.load(config.VECTOR_DIR)
    return _VSTORE


@router.get("/health")
def get_health():
    """
    Returns system health, HydraDB connection status, and graph element counts dynamically.
    """
    # Connectivity is its own signal: a slow label scan says nothing about
    # whether HydraDB is reachable, and conflating the two previously reported a
    # fully-working graph as disconnected.
    hydra_ok = False
    try:
        with GraphClient() as client:
            hydra_ok = client.ping()
    except Exception:
        hydra_ok = False

    if hydra_ok and (time.time() - _counts_at) > _COUNT_TTL_SECONDS:
        threading.Thread(target=_refresh_counts, daemon=True).start()

    vstore = _get_vstore()
    vstore_loaded = (vstore.chunk_embeddings is not None or vstore.doc_embeddings is not None)
    vector_count = len(vstore.chunks_meta) if (vstore_loaded and vstore.chunks_meta) else len(vstore.doc_ids)

    return {
        "status": "healthy" if hydra_ok and vstore_loaded else "degraded",
        "hydradb_connected": hydra_ok,
        "vector_store_loaded": vstore_loaded,
        "total_documents": _counts["Document"],
        "total_persons": _counts["Person"],
        "total_orgs": _counts["Org"],
        "total_topics": _counts["Topic"],
        "total_facts": _counts["Fact"],
        "total_vectors": vector_count,
        # Age of the label counts in seconds; null until the first refresh lands.
        "counts_age_seconds": round(time.time() - _counts_at, 1) if _counts_at else None,
    }
