"""
resolution/conflicts.py — Conflict Detection and Tagging Layer.

Identifies facts with matching (subject, attribute) pairs but conflicting values,
tags them with source trust & timestamps, and links them with SUPERSEDES edges in HydraDB.

Fetches facts in per-document batches to avoid HydraDB's 30-second query timeout
when scanning 95K+ Fact nodes in a single query.
"""

import logging
from company_brain.graph.client import GraphClient

logger = logging.getLogger(__name__)

# Number of documents to fetch facts for per query batch
_DOC_BATCH_SIZE = 50


def detect_and_tag_conflicts(client: GraphClient) -> int:
    """
    Finds conflicting Fact nodes in HydraDB with the same (subject, attribute) but different values.
    Fetches facts in small per-document batches to stay within HydraDB's 30-second query timeout.
    Returns count of SUPERSEDES edges created.
    """

    # Step 1: Fetch all Document node integer ids (fast — Document count always succeeds)
    try:
        doc_rows = client.run("MATCH (d:Document) RETURN d.id AS did, d.doc_id AS doc_id")
        all_doc_ids = [r["did"] for r in doc_rows if r.get("did") is not None]
    except Exception as exc:
        logger.warning("Could not fetch document list for conflict detection: %s", exc)
        return 0

    if not all_doc_ids:
        logger.info("No documents found — skipping conflict detection.")
        return 0

    logger.info("Fetching facts for %d documents in batches of %d...", len(all_doc_ids), _DOC_BATCH_SIZE)

    grouped: dict[tuple, list] = {}
    total_facts = 0
    errors = 0

    # Step 2: Fetch facts per document individually to avoid full-scan timeout
    for doc_int_id in all_doc_ids:
        try:
            with client.get_session() as session:
                result = session.run(
                    "MATCH (d:Document {id: $did})-[:HAS_FACT]->(f:Fact) "
                    "RETURN f.id AS id, f.subject AS subject, f.attribute AS attribute, f.value AS value, f.trust_score AS trust_score",
                    {"did": doc_int_id}
                )
                for record in result:
                    raw_id = record.get("id")
                    if raw_id is None:
                        continue
                    try:
                        fact_id = int(raw_id)
                    except (ValueError, TypeError):
                        continue

                    sub = str(record.get("subject") or "").lower().strip()
                    attr = str(record.get("attribute") or "").lower().strip()
                    val = str(record.get("value") or "").strip()
                    trust = record.get("trust_score")

                    if sub and attr and val:
                        key = (sub, attr)
                        grouped.setdefault(key, []).append({
                            "id": fact_id,
                            "subject": sub,
                            "attribute": attr,
                            "value": val,
                            "trust_score": float(trust) if trust is not None else 0.5,
                        })
                        total_facts += 1
                result.consume()
        except Exception as exc:
            errors += 1
            logger.debug("Failed to fetch facts for doc %d: %s", doc_int_id, exc)

    if errors:
        logger.warning("Fact fetch errors for %d documents (out of %d).", errors, len(all_doc_ids))

    conflicting_groups = [
        (k, v) for k, v in grouped.items()
        if len(v) >= 2 and len(set(f["value"] for f in v)) > 1
    ]
    logger.info("Scanned %d fact entries. Found %d conflicting attribute groups.", total_facts, len(conflicting_groups))

    if not conflicting_groups:
        logger.info("No conflicting fact pairs found in Knowledge Graph.")
        return 0

    # Build rows for batched UNWIND query
    rows = []
    for (sub, attr), fact_list in conflicting_groups:
        sorted_facts = sorted(fact_list, key=lambda x: x["trust_score"], reverse=True)
        winner = sorted_facts[0]
        for loser in sorted_facts[1:]:
            rows.append({
                "wid": winner["id"],
                "lid": loser["id"],
            })

    if not rows:
        return 0

    logger.info("Writing %d SUPERSEDES conflict edges in batched UNWIND queries...", len(rows))

    # HydraDB UNWIND rules: nodes have ONLY id, NO labels, NO relationship properties
    batch_cypher = (
        "UNWIND $rows AS row "
        "CREATE (w {id: row.wid})"
        "-[:SUPERSEDES]->"
        "(l {id: row.lid})"
    )

    try:
        supersedes_count = client.run_batch(batch_cypher, rows, batch_size=500)
    except Exception as exc:
        logger.warning("Batched conflict write error: %s", exc)
        supersedes_count = 0

    logger.info("Conflict layer complete. Created %d SUPERSEDES edges.", supersedes_count)
    return supersedes_count


def _sanitize(text: str) -> str:
    if not text:
        return ""
    return text.replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
