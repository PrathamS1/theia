"""
query/cypher_templates.py — Parameterised Cypher query builders for multi-hop graph traversal.

Obeyes HydraDB Cypher rules:
- Requires a label or property predicate on node MATCH (e.g. MATCH (f:Fact))
- RETURN bindings.<property>
- Avoids unsupported functions like toLower() or CONTAINS in WHERE clause.
  Filtering is handled safely in Python memory layer.
"""

from typing import List, Dict, Any


def build_fact_query() -> str:
    """
    Builds HydraDB-compliant Cypher query to retrieve facts from the graph.
    """
    return "MATCH (f:Fact) RETURN f.id AS id, f.subject AS subject, f.attribute AS attribute, f.value AS value, f.trust_score AS trust_score, f.doc_id AS doc_id"


def build_entity_query() -> str:
    """
    Builds HydraDB-compliant Cypher query to find Person nodes and mentioned documents.
    """
    return "MATCH (d:Document)-[r:MENTIONS]->(e:Person) RETURN d.doc_id AS doc_id, d.source AS source, e.name AS name, e.id AS id"
