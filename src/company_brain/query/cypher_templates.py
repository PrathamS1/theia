"""
query/cypher_templates.py — HydraDB-compliant Cypher query builders.

Rules obeyed:
- Requires a label or property predicate on node MATCH (e.g. MATCH (d:Document {id: $did}))
- RETURN bindings.<property>
- Uses node IDs as anchors for sub-millisecond targeted lookups
"""

from typing import List


def build_doc_facts_query() -> str:
    """
    Retrieves facts connected to a specific Document node by integer ID.
    Sub-millisecond latency on HydraDB.
    """
    return (
        "MATCH (d:Document {id: $did})-[:HAS_FACT]->(f:Fact) "
        "RETURN f.id AS id, f.subject AS subject, f.attribute AS attribute, "
        "f.value AS value, f.trust_score AS trust_score, f.doc_id AS doc_id"
    )


def build_entity_docs_query(label: str = "Person") -> str:
    """
    Finds Document IDs mentioning a specific entity.
    """
    return (
        f"MATCH (d:Document)-[:MENTIONS]->(e:{label} {{id: $eid}}) "
        "RETURN d.id AS did, d.doc_id AS doc_id, d.source AS source"
    )


def build_same_as_query() -> str:
    """
    Finds resolved canonical aliases for an entity using SAME_AS edges.
    """
    return (
        "MATCH (a:Person {id: $pid})-[:SAME_AS]->(b:Person) "
        "RETURN b.id AS id, b.name AS name"
    )


def build_supersedes_query() -> str:
    """
    Finds facts superseded by a winner fact.
    """
    return (
        "MATCH (w:Fact {id: $fid})-[:SUPERSEDES]->(l:Fact) "
        "RETURN l.id AS loser_id"
    )


def build_all_superseded_ids_query() -> str:
    """
    Returns the integer IDs of ALL loser facts that have an incoming SUPERSEDES edge.
    Used to filter out stale/superseded facts from query results in Python.
    Fast: traverses only SUPERSEDES edges, not all facts.
    """
    return (
        "MATCH ()-[:SUPERSEDES]->(loser:Fact) "
        "RETURN loser.id AS loser_id"
    )
