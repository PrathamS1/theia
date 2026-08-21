"""
resolution/conflicts.py — Conflict Detection & Temporal Supersession Layer.

Identifies facts with matching (subject, attribute) pairs but conflicting values,
ranks them by temporal recency and source authority, and writes SUPERSEDES edges into HydraDB using one-hop CREATE.
"""

import logging
import re
from typing import Dict, List, Any, Tuple, Optional
from company_brain.graph.client import GraphClient

logger = logging.getLogger(__name__)

# Units that describe the same kind of quantity, so two values are comparable.
# Anything unrecognised is "unknown" and is never treated as a conflict -- we would
# rather miss a contradiction than invent one.
_UNIT_GROUPS = (
    ("duration", re.compile(r"\b\d+(?:\.\d+)?\s*(?:ms|milliseconds?|s|secs?|seconds?|m|mins?|minutes?|h|hrs?|hours?|d|days?|w|weeks?|months?|years?)\b", re.I)),
    ("bytes",    re.compile(r"\b\d+(?:\.\d+)?\s*(?:b|kb|mb|gb|tb|kib|mib|gib|tib)\b", re.I)),
    ("percent",  re.compile(r"\b\d+(?:\.\d+)?\s*%")),
    ("money",    re.compile(r"(?:[$€£]\s*\d+(?:\.\d+)?|\b\d+(?:\.\d+)?\s*(?:usd|eur|gbp)\b)", re.I)),
    ("count",    re.compile(r"^\s*\d+(?:\.\d+)?\s*$")),
)


def _unit_of(value: Any) -> str:
    """Classify a fact value by the kind of quantity it expresses."""
    v = str(value or "").strip()
    if not v:
        return "unknown"
    for name, pattern in _UNIT_GROUPS:
        if pattern.search(v):
            return name
    return "unknown"


def detect_and_tag_conflicts(client: GraphClient, workspace_id: Optional[str] = None) -> int:
    """
    Finds conflicting Fact nodes in HydraDB strictly scoped to the specified workspace_id.
    Creates (f_newer)-[:SUPERSEDES]->(f_older) edges based on timestamp and source trust.
    Returns: count of SUPERSEDES edges created.
    """
    try:
        if workspace_id:
            facts = client.run(f"MATCH (f:Fact {{workspace_id: '{workspace_id}'}}) RETURN f.id AS id, f.subject AS subject, f.attribute AS attribute, f.value AS value, f.trust_score AS trust_score, f.doc_id AS doc_id, f.created_at AS created_at")
        else:
            facts = client.run("MATCH (f:Fact) RETURN f.id AS id, f.subject AS subject, f.attribute AS attribute, f.value AS value, f.trust_score AS trust_score, f.doc_id AS doc_id, f.created_at AS created_at")
    except Exception as exc:
        logger.warning("Could not fetch facts for conflict detection: %s", exc)
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
    ws_prop = f", workspace_id: '{workspace_id}'" if workspace_id else ""
    for (sub, attr), fact_list in grouped.items():
        if len(fact_list) < 2:
            continue

        # Two values only conflict if they are the same *kind* of quantity.
        # Grouping on the generic `limit_or_target` attribute previously declared
        # "12 months", "30 days" and "5%" to be contradictions of one another,
        # which produced SUPERSEDES edges between unrelated measurements.
        by_unit: Dict[str, List[Dict[str, Any]]] = {}
        for f in fact_list:
            by_unit.setdefault(_unit_of(f.get("value")), []).append(f)

        for unit, unit_facts in by_unit.items():
            if len(unit_facts) < 2 or unit == "unknown":
                continue
            unique_values = set(str(f.get("value", "")).strip() for f in unit_facts)
            if len(unique_values) <= 1:
                continue

            # Sort by recency, then source authority. `.get(k, default)` does not
            # fire when the key exists with a None value -- which is exactly the
            # case here -- so the fallback is applied explicitly.
            sorted_facts = sorted(
                unit_facts,
                key=lambda x: (
                    str(x.get("created_at") or "1970-01-01T00:00:00Z"),
                    float(x.get("trust_score") or 0.5),
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
                        f"-[:SUPERSEDES {{reason: '{clean_reason}', timestamp: '{winner_time}'{ws_prop}}}]->"
                        f"(l:Fact {{id: {loser['id']}}})"
                    )
                    try:
                        client.run_write(link_cypher)
                        supersedes_count += 1
                    except Exception as exc:
                        logger.debug("Failed to write SUPERSEDES edge: %s", exc)

    logger.info("Conflict layer complete for workspace=%s. Created %d SUPERSEDES edges in HydraDB.", workspace_id, supersedes_count)
    return supersedes_count
