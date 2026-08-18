"""
resolution/conflicts.py — Conflict Detection & Temporal Supersession Layer.

Identifies facts with matching (subject, attribute) pairs but conflicting values,
ranks them by temporal recency and source authority, and writes SUPERSEDES edges into HydraDB using one-hop CREATE.
"""

import logging
from typing import Dict, List, Any, Tuple
from company_brain.graph.client import GraphClient

logger = logging.getLogger(__name__)


def detect_and_tag_conflicts(client: GraphClient) -> int:
    """
    Finds conflicting Fact nodes in HydraDB with the same (subject, attribute) but different values.
    Creates (f_newer)-[:SUPERSEDES]->(f_older) edges based on timestamp and source trust.
    Returns: count of SUPERSEDES edges created.
    """
    cypher = (
        "MATCH (d:Document)-[:HAS_FACT]->(f:Fact) "
        "RETURN f.id AS id, f.subject AS subject, f.attribute AS attribute, "
        "f.value AS value, f.trust_score AS trust_score, f.doc_id AS doc_id, d.created_at AS created_at"
    )
    try:
        facts = client.run(cypher)
    except Exception as exc:
        logger.warning("Could not fetch facts for conflict detection: %s", exc)
        try:
            facts = client.run("MATCH (f:Fact) RETURN f.id AS id, f.subject AS subject, f.attribute AS attribute, f.value AS value, f.trust_score AS trust_score, f.doc_id AS doc_id")
        except Exception:
            facts = []

    if not facts:
        return 0

    # Group facts by normalized (subject, attribute)
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for f in facts:
        sub = str(f.get("subject", "")).lower().strip()
        attr = str(f.get("attribute", "")).lower().strip()
        if sub and attr:
            key = (sub, attr)
            grouped.setdefault(key, []).append(f)

    supersedes_count = 0
    for (sub, attr), fact_list in grouped.items():
        if len(fact_list) < 2:
            continue

        # Check for conflicting values
        unique_values = set(str(f.get("value", "")).strip() for f in fact_list)
        if len(unique_values) > 1:
            # Sort facts by: 1) created_at timestamp descending, 2) trust_score descending
            sorted_facts = sorted(
                fact_list,
                key=lambda x: (
                    str(x.get("created_at", "1970-01-01")),
                    float(x.get("trust_score", 0.5))
                ),
                reverse=True
            )

            winner = sorted_facts[0]
            winner_val = str(winner.get("value", "")).replace("'", "").replace('"', "")
            winner_time = str(winner.get("created_at", "latest"))

            for loser in sorted_facts[1:]:
                loser_val = str(loser.get("value", "")).replace("'", "").replace('"', "")
                if loser_val != winner_val:
                    reason = f"Newer assertion ({winner_val}) supersedes earlier value ({loser_val})"
                    clean_reason = reason.replace("'", "\\'").replace('"', '\\"').replace("\n", " ")

                    link_cypher = (
                        f"CREATE (w:Fact {{id: {winner['id']}}})"
                        f"-[:SUPERSEDES {{reason: '{clean_reason}', timestamp: '{winner_time}'}}]->"
                        f"(l:Fact {{id: {loser['id']}}})"
                    )
                    try:
                        client.run_write(link_cypher)
                        supersedes_count += 1
                    except Exception as exc:
                        logger.debug("Failed to write SUPERSEDES edge: %s", exc)

    logger.info("Conflict layer complete. Created %d SUPERSEDES edges in HydraDB.", supersedes_count)
    return supersedes_count
