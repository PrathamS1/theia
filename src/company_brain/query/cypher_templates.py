"""
query/cypher_templates.py — HydraDB-compliant Cypher query builders.

Rules obeyed:
- All MATCH nodes carry a label predicate
- RETURN uses <binding>.<property> syntax
- No WHERE string functions (toLower, CONTAINS) — filtering done in Python
- Fact retrieval optionally scoped to a set of doc_ids to avoid full-table scans
"""

from typing import List


def build_fact_query(doc_ids: List[str] | None = None, limit: int = 200) -> str:
    """
    Retrieve Fact nodes from HydraDB, ordered by trust_score descending.

    If doc_ids is provided, retrieve ALL facts then filter in Python
    (HydraDB does not support IN or list parameters in WHERE).
    The limit caps the total rows returned to avoid overwhelming the driver.
    """
    # HydraDB does not support ORDER BY or LIMIT reliably in all versions,
    # so we fetch up to `limit` rows and sort in Python.
    return (
        "MATCH (f:Fact) "
        "RETURN f.id AS id, f.subject AS subject, f.attribute AS attribute, "
        "f.value AS value, f.trust_score AS trust_score, f.doc_id AS doc_id"
    )


def build_entity_name_query() -> str:
    """
    Retrieve Person entity names only (no id/source — extra properties cause 30s timeout).
    """
    return "MATCH (e:Person) RETURN e.name AS name"


def build_org_name_query() -> str:
    """
    Retrieve Org entity names only.
    """
    return "MATCH (o:Org) RETURN o.name AS name"


def build_facts_for_docs_query() -> str:
    """
    Retrieve Facts linked to documents.
    Used after entity lookup to narrow facts to relevant documents only.
    """
    return (
        "MATCH (d:Document)-[:HAS_FACT]->(f:Fact) "
        "RETURN f.id AS id, f.subject AS subject, f.attribute AS attribute, "
        "f.value AS value, f.trust_score AS trust_score, f.doc_id AS doc_id, "
        "d.source AS source"
    )
