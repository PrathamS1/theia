"""
resolution/blocking.py — candidate entity pair generation using rapidfuzz.

Groups extracted Person / Org / Project entities into high-recall candidate clusters
before running graph path checks and LLM adjudication.
"""

import logging
from typing import List, Tuple, Dict, Any
from rapidfuzz import fuzz

from company_brain import config
from company_brain.graph.client import GraphClient

logger = logging.getLogger(__name__)


def generate_candidate_pairs(client: GraphClient) -> List[Tuple[Dict[str, Any], Dict[str, Any], float]]:
    """
    Fetch all Person and Org entities from HydraDB and group similar pairs.
    Returns list of tuples: (entity_A_dict, entity_B_dict, similarity_score).
    """
    # 1. Fetch Person entities
    try:
        persons = client.run_read("MATCH (p:Person) RETURN p.id AS id, p.name AS name, p.email AS email, p.handle AS handle, p.source AS source")
    except Exception:
        persons = []

    candidate_pairs = []
    threshold = config.BLOCKING_THRESHOLD

    # Fuzzy match Person names and exact match email/handle
    for i in range(len(persons)):
        for j in range(i + 1, len(persons)):
            p1, p2 = persons[i], persons[j]
            score = 0.0

            # Exact match on email or handle
            if p1.get("email") and p2.get("email") and p1["email"] == p2["email"]:
                score = 100.0
            elif p1.get("handle") and p2.get("handle") and p1["handle"] == p2["handle"]:
                score = 95.0
            else:
                name1, name2 = p1.get("name", ""), p2.get("name", "")
                if name1 and name2:
                    score = fuzz.token_sort_ratio(name1, name2)

            if score >= threshold:
                candidate_pairs.append((p1, p2, score))

    logger.info("Generated %d candidate entity pairs for resolution", len(candidate_pairs))
    return candidate_pairs
