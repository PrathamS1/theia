"""
resolution/resolve.py — Entity Resolution Engine for HydraDB.

Evaluates candidate pairs, leverages graph co-occurrence evidence,
and writes SAME_AS {confidence, evidence} edges into HydraDB using one-hop CREATE.
"""

import logging
from typing import List, Tuple, Dict, Any, Optional, Set

from company_brain import config
from company_brain.graph.client import GraphClient
from company_brain.resolution.blocking import generate_candidate_pairs

logger = logging.getLogger(__name__)


def resolve_entities(
    client: GraphClient,
    workspace_id: Optional[str] = None,
    doc_ids: Optional[Set[str]] = None,
) -> int:
    """
    Runs blocking, evaluates candidate entity pairs, and writes SAME_AS edges into HydraDB
    strictly scoped to the specified workspace_id.
    Returns: count of SAME_AS edges created.
    """
    candidate_pairs = generate_candidate_pairs(client, workspace_id=workspace_id, doc_ids=doc_ids)
    same_as_count = 0

    for p1, p2, score, shared_docs in candidate_pairs:
        confidence = round(score / 100.0, 3)
        evidence_parts = []
        if shared_docs:
            evidence_parts.append(f"Shared docs: {', '.join(shared_docs[:2])}")
        name1 = str(p1.get("name", "")).replace("'", "").replace('"', "")
        name2 = str(p2.get("name", "")).replace("'", "").replace('"', "")
        evidence_parts.append(f"Fuzzy match: {score:.1f}% ({name1} / {name2})")
        evidence = "; ".join(evidence_parts)

        # Write SAME_AS edge
        success = _write_same_as(client, p1["id"], p2["id"], confidence, evidence, workspace_id=workspace_id)
        if success:
            same_as_count += 1

    logger.info("Entity resolution complete for workspace=%s. Created %d SAME_AS edges in HydraDB.", workspace_id, same_as_count)
    return same_as_count


def _write_same_as(
    client: GraphClient,
    id1: int,
    id2: int,
    confidence: float,
    evidence: str,
    workspace_id: Optional[str] = None,
) -> bool:
    """
    Writes a SAME_AS edge between two resolved entity nodes in HydraDB using one-hop CREATE.
    """
    clean_evidence = evidence.replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
    ws_prop = f", workspace_id: '{workspace_id}'" if workspace_id else ""
    cypher = (
        f"CREATE (a:Person {{id: {id1}}})"
        f"-[:SAME_AS {{confidence: {confidence}, evidence: '{clean_evidence}'{ws_prop}}}]->"
        f"(b:Person {{id: {id2}}})"
    )
    try:
        client.run_write(cypher)
        return True
    except Exception as exc:
        logger.debug("Failed to write SAME_AS edge between %d and %d: %s", id1, id2, exc)
        return False
