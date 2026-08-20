"""
resolution/blocking.py — High-recall candidate entity pair generation using rapidfuzz & graph co-occurrence.

Groups Person and Org entities into candidate clusters based on:
1. Exact email prefix / Slack handle matches
2. Name fuzzy similarity (token_sort_ratio / partial_ratio)
3. Shared document co-occurrences in HydraDB
"""

import logging
from typing import List, Tuple, Dict, Any, Set, Optional
from rapidfuzz import fuzz

from company_brain import config
from company_brain.graph.client import GraphClient

logger = logging.getLogger(__name__)


def generate_candidate_pairs(
    client: GraphClient,
    workspace_id: Optional[str] = None,
) -> List[Tuple[Dict[str, Any], Dict[str, Any], float, List[str]]]:
    """
    Fetch Person entities from HydraDB and find matching candidate pairs scoped to workspace_id.
    Returns: List of (entity_A, entity_B, similarity_score, shared_evidence_docs).
    """
    try:
        if workspace_id:
            persons = client.run(f"MATCH (p:Person {{workspace_id: '{workspace_id}'}}) RETURN p.id AS id, p.name AS name, p.source AS source")
        else:
            persons = client.run("MATCH (p:Person) RETURN p.id AS id, p.name AS name, p.source AS source")
    except Exception as e:
        logger.warning("Failed to fetch Person nodes: %s", e)
        persons = []

    if not persons:
        return []

    # Map name -> list of person records
    candidate_pairs = []
    threshold = config.BLOCKING_THRESHOLD  # 85

    # Fetch document co-occurrence links: which persons are mentioned in the same documents
    co_occurrences: Dict[int, Set[str]] = {}
    try:
        if workspace_id:
            doc_mentions = client.run(
                f"MATCH (d:Document {{workspace_id: '{workspace_id}'}})-[:MENTIONS]->(p:Person {{workspace_id: '{workspace_id}'}}) RETURN p.id AS person_id, d.doc_id AS doc_id"
            )
        else:
            doc_mentions = client.run(
                "MATCH (d:Document)-[:MENTIONS]->(p:Person) RETURN p.id AS person_id, d.doc_id AS doc_id"
            )
        for row in doc_mentions:
            pid = row.get("person_id")
            did = row.get("doc_id")
            if pid and did:
                co_occurrences.setdefault(pid, set()).add(did)
    except Exception as e:
        logger.debug("Document co-occurrence lookup skipped: %s", e)

    # Compare pairs
    n = len(persons)
    cross_source_threshold = 70  # Lower threshold for cross-platform handle matching
    for i in range(n):
        p1 = persons[i]
        name1 = str(p1.get("name", "")).strip()
        id1 = p1.get("id")
        source1 = str(p1.get("source", "")).lower()

        for j in range(i + 1, n):
            p2 = persons[j]
            name2 = str(p2.get("name", "")).strip()
            id2 = p2.get("id")
            source2 = str(p2.get("source", "")).lower()

            if not name1 or not name2 or name1.lower() == name2.lower():
                if name1 and name2 and name1.lower() == name2.lower():
                    # Same name mention from different sources
                    shared_docs = list(co_occurrences.get(id1, set()).intersection(co_occurrences.get(id2, set())))
                    candidate_pairs.append((p1, p2, 100.0, shared_docs))
                continue

            # Determine if this is a cross-source pair (e.g., slack vs github)
            is_cross_source = source1 != source2 and source1 and source2

            if is_cross_source:
                # Use handle-aware cross-source similarity with lower threshold
                score = _cross_source_similarity(name1, name2)
                effective_threshold = cross_source_threshold
            else:
                # Same-source: use standard name comparison
                score = _compute_name_similarity(name1, name2)
                effective_threshold = threshold

            # Check shared graph context
            shared_docs = list(co_occurrences.get(id1, set()).intersection(co_occurrences.get(id2, set())))
            if shared_docs and score >= 60.0:
                score = min(100.0, score + 20.0)  # Boost confidence if they co-occur in the same documents

            if score >= effective_threshold:
                candidate_pairs.append((p1, p2, score, shared_docs))

    logger.info("Generated %d candidate entity pairs for resolution.", len(candidate_pairs))
    return candidate_pairs


def _compute_name_similarity(name1: str, name2: str) -> float:
    """Calculates multi-angle fuzzy similarity between two entity names/handles."""
    n1 = name1.lower().replace("@", "").replace(".", " ")
    n2 = name2.lower().replace("@", "").replace(".", " ")

    # Direct token sort ratio
    sort_score = fuzz.token_sort_ratio(n1, n2)
    # Token set ratio (handles subset names like "Selene" vs "Selene Huang")
    set_score = fuzz.token_set_ratio(n1, n2)
    # Partial ratio (handles handle prefixes like "clara" in "Clara Nguyen")
    partial_score = fuzz.partial_ratio(n1, n2)

    return max(sort_score, (set_score * 0.7 + partial_score * 0.3))


def _normalize_handle(name: str) -> str:
    """
    Strips platform-specific noise from handles/logins for cross-source matching.
    '@pratham' -> 'pratham', 'PrathamS1' -> 'prathams', 'soham.r' -> 'soham r'
    """
    import re
    n = name.lower().strip()
    n = n.lstrip("@")
    n = re.sub(r"[._-]", " ", n)
    # Strip trailing digits (GitHub login suffixes like 'PrathamS1' -> 'prathams')
    n = re.sub(r"\d+$", "", n)
    return n.strip()


def _cross_source_similarity(name1: str, name2: str) -> float:
    """
    Computes similarity between handles from different platforms.
    Uses normalized handles for a fairer comparison.
    """
    h1 = _normalize_handle(name1)
    h2 = _normalize_handle(name2)

    sort_score = fuzz.token_sort_ratio(h1, h2)
    set_score = fuzz.token_set_ratio(h1, h2)
    partial_score = fuzz.partial_ratio(h1, h2)

    # Exact prefix match (e.g., 'pratham' starts with 'pratham' in 'prathams')
    if h1.startswith(h2) or h2.startswith(h1):
        return max(90.0, sort_score)

    return max(sort_score, (set_score * 0.6 + partial_score * 0.4))

