"""
query/cypher_templates.py — Parameterised Cypher query builders for multi-hop graph traversal.

Obeyes HydraDB Cypher rules:
- Requires a label or property predicate on node MATCH (e.g. MATCH (f:Fact))
- RETURN bindings.<property>
"""

from typing import List, Dict, Any


def build_fact_query(search_terms: List[str]) -> str:
    """
    Builds Cypher query to retrieve facts matching query keywords.
    """
    conditions = []
    for term in search_terms:
        clean_term = term.replace("'", "\\'").lower()
        conditions.append(
            f"toLower(f.subject) CONTAINS '{clean_term}' OR "
            f"toLower(f.attribute) CONTAINS '{clean_term}' OR "
            f"toLower(f.value) CONTAINS '{clean_term}'"
        )

    where_clause = " OR ".join(conditions) if conditions else "true"
    return f"MATCH (f:Fact) WHERE {where_clause} RETURN f.id, f.subject, f.attribute, f.value, f.trust_score, f.doc_id"


def build_entity_query(entity_name: str) -> str:
    """
    Builds Cypher query to find matching entity node and its mentioned documents.
    """
    clean_name = entity_name.replace("'", "\\'").lower()
    return f"MATCH (d:Document)-[r:MENTIONS]->(e:Person) WHERE toLower(e.name) CONTAINS '{clean_name}' RETURN d.doc_id, d.source, e.name, e.id"
