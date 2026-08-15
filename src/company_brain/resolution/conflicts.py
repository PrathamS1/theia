"""
resolution/conflicts.py — Conflict Detection and Tagging Layer.

Identifies facts with matching (subject, attribute) pairs but conflicting values,
tags them with source trust & timestamps, and links them with SUPERSEDES edges in HydraDB.
"""

import logging
from tqdm import tqdm
from company_brain.graph.client import GraphClient

logger = logging.getLogger(__name__)


def detect_and_tag_conflicts(client: GraphClient) -> int:
    """
    Finds conflicting Fact nodes in HydraDB with the same (subject, attribute) but different values.
    Uses auto-commit Cypher writes to ensure clean execution on HydraDB.
    Returns count of SUPERSEDES edges created.
    """
    cypher = (
        "MATCH (f:Fact) "
        "RETURN f.id AS id, f.subject AS subject, f.attribute AS attribute, f.value AS value, f.trust_score AS trust_score"
    )

    grouped: dict[tuple, list] = {}
    try:
        with client.get_session() as session:
            result = session.run(cypher)
            for record in result:
                raw_id = record.get("id") if record.get("id") is not None else record.get("f.id")
                if raw_id is None:
                    continue

                try:
                    fact_id = int(raw_id)
                except (ValueError, TypeError):
                    continue

                sub = str(record.get("subject") or record.get("f.subject") or "").lower().strip()
                attr = str(record.get("attribute") or record.get("f.attribute") or "").lower().strip()
                val = str(record.get("value") or record.get("f.value") or "").strip()
                trust = record.get("trust_score") if record.get("trust_score") is not None else record.get("f.trust_score")

                if sub and attr and val:
                    generic_attrs = {"status", "priority", "type", "date", "author", "id", "name", "project", "owner"}
                    if sub.startswith("dsid_") or sub.startswith("doc_"):
                        if attr in generic_attrs:
                            continue
                        key = ("__global_entity__", attr)
                    else:
                        key = (sub, attr)
                        
                    fact_dict = {
                        "id": fact_id,
                        "subject": sub,
                        "attribute": attr,
                        "value": val,
                        "trust_score": float(trust) if trust is not None else 0.5,
                    }
                    grouped.setdefault(key, []).append(fact_dict)
            result.consume()
    except Exception as exc:
        logger.warning("Could not fetch facts for conflict detection: %s", exc)
        return 0

    total_facts = sum(len(v) for v in grouped.values())
    conflicting_groups = [(k, v) for k, v in grouped.items() if len(v) >= 2 and len(set(f["value"] for f in v)) > 1]
    logger.info("Scanned %d fact entries. Found %d conflicting attribute groups.", total_facts, len(conflicting_groups))

    if not conflicting_groups:
        logger.info("No conflicting fact pairs found in Knowledge Graph.")
        return 0

    supersedes_count = 0
    for (sub, attr), fact_list in tqdm(conflicting_groups, desc="Tagging SUPERSEDES Conflicts", unit="group"):
        sorted_facts = sorted(fact_list, key=lambda x: x["trust_score"], reverse=True)
        winner = sorted_facts[0]

        for loser in sorted_facts[1:]:
            w_trust = winner["trust_score"]
            l_trust = loser["trust_score"]

            w_sub = _sanitize(winner["subject"])
            w_attr = _sanitize(winner["attribute"])
            w_val = _sanitize(winner["value"])

            l_sub = _sanitize(loser["subject"])
            l_attr = _sanitize(loser["attribute"])
            l_val = _sanitize(loser["value"])

            link_cypher = (
                f"CREATE (w:Fact {{id: {winner['id']}, subject: '{w_sub}', attribute: '{w_attr}', value: '{w_val}'}})"
                f"-[:SUPERSEDES {{reason: 'Higher trust score ({w_trust}) overrides ({l_trust})'}}]->"
                f"(l:Fact {{id: {loser['id']}, subject: '{l_sub}', attribute: '{l_attr}', value: '{l_val}'}})"
            )
            try:
                client.run_write(link_cypher)
                supersedes_count += 1
            except Exception as exc:
                logger.debug("Failed to write SUPERSEDES edge: %s", exc)

    logger.info("Conflict layer complete. Created %d SUPERSEDES edges.", supersedes_count)
    return supersedes_count


def _sanitize(text: str) -> str:
    if not text:
        return ""
    return text.replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
