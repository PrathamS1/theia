"""
resolution/conflicts.py — Conflict Detection and Tagging Layer.

Identifies facts with matching (subject, attribute) pairs but conflicting values,
tags them with source trust & timestamps, and links them with SUPERSEDES edges in HydraDB.
"""

import logging
from company_brain.graph.client import GraphClient

logger = logging.getLogger(__name__)


def detect_and_tag_conflicts(client: GraphClient) -> int:
    """
    Finds conflicting Fact nodes in HydraDB with the same (subject, attribute) but different values.
    Creates (f_newer)-[:SUPERSEDES]->(f_older) edges based on timestamp and source trust.
    Returns count of SUPERSEDES edges created.
    """
    cypher = (
        "MATCH (f:Fact) "
        "RETURN f.id AS id, f.subject AS subject, f.attribute AS attribute, f.value AS value, f.trust_score AS trust_score, f.doc_id AS doc_id"
    )
    try:
        facts = client.run(cypher)
    except Exception as exc:
        logger.warning("Could not fetch facts for conflict detection: %s", exc)
        return 0

    # Group facts by (subject, attribute)
    grouped: dict[tuple, list] = {}
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

        # Check if values conflict
        values = set(f.get("value", "").strip() for f in fact_list)
        if len(values) > 1:
            # Sort by trust_score descending
            sorted_facts = sorted(fact_list, key=lambda x: float(x.get("trust_score", 0.5)), reverse=True)
            winner = sorted_facts[0]

            for loser in sorted_facts[1:]:
                link_cypher = (
                    f"MATCH (w:Fact {{id: {winner['id']}}}), (l:Fact {{id: {loser['id']}}}) "
                    f"CREATE (w)-[:SUPERSEDES {{reason: 'Higher trust score ({winner.get(\"trust_score\")}) overrides ({loser.get(\"trust_score\")})'}}]->(l)"
                )
                try:
                    client.run_write(link_cypher)
                    supersedes_count += 1
                except Exception as exc:
                    logger.debug("Failed to write SUPERSEDES edge: %s", exc)

    logger.info("Conflict layer complete. Created %d SUPERSEDES edges.", supersedes_count)
    return supersedes_count
