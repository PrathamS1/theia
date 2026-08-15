"""
graph/loader.py — bulk loader for Document, Entity, and Fact nodes into HydraDB.

Obeyes HydraDB Cypher rules:
- Integer node `id` property (generated deterministically from string identifiers)
- Clean node creation patterns avoiding duplicate node allocation overhead
- High-throughput execution using persistent Neo4j Bolt sessions
"""

import logging
import zlib
from typing import Dict, Any, List, Optional
from neo4j import Session

from company_brain.graph.client import GraphClient
from company_brain.graph.schema import trust_for
from company_brain.extraction.prompts import DocumentExtractionResult

logger = logging.getLogger(__name__)


def string_to_int_id(identifier: str) -> int:
    """
    Generate a positive 32-bit integer ID from string identifier,
    as required by HydraDB node `id` property.
    """
    return zlib.crc32(identifier.encode("utf-8")) & 0x7FFFFFFF


class GraphLoader:
    def __init__(self, client: GraphClient) -> None:
        self.client = client

    def load_document(
        self,
        doc_id: str,
        source: str,
        created_at: str,
        text_snippet: str,
        extraction: DocumentExtractionResult,
        session: Optional[Session] = None,
    ) -> None:
        """
        Loads a document and its extracted entities and facts into HydraDB.
        Reuses an open persistent Bolt session to maximize write speed.
        """
        doc_int_id = string_to_int_id(f"doc_{doc_id}")
        source_trust = trust_for(source)

        # 1. Create Document Node ONCE per document
        doc_cypher = (
            f"CREATE (d:Document {{id: {doc_int_id}, doc_id: '{doc_id}', source: '{source}', created_at: '{created_at}'}})"
        )
        try:
            self.client.run_write(doc_cypher, session=session)
        except Exception as e:
            logger.debug("Failed doc write %s: %s", doc_id, e)

        # 2. Create Entity Nodes
        for entity in extraction.entities:
            entity_key = f"{entity.entity_type}_{entity.name}"
            entity_int_id = string_to_int_id(entity_key)
            label = entity.entity_type if entity.entity_type in ["Person", "Org", "Project", "Ticket", "Deal"] else "Entity"

            ent_cypher = (
                f"CREATE (e:{label} {{id: {entity_int_id}, name: '{_sanitize(entity.name)}', source: '{source}'}})"
            )
            try:
                self.client.run_write(ent_cypher, session=session)
            except Exception as e:
                logger.debug("Failed entity write %s: %s", entity.name, e)

        # 3. Create Fact Nodes
        for idx, fact in enumerate(extraction.facts):
            fact_key = f"fact_{doc_id}_{idx}"
            fact_int_id = string_to_int_id(fact_key)

            fact_cypher = (
                f"CREATE (f:Fact {{id: {fact_int_id}, subject: '{_sanitize(fact.subject)}', attribute: '{_sanitize(fact.attribute)}', value: '{_sanitize(fact.value)}', trust_score: {source_trust}, doc_id: '{doc_id}'}})"
            )
            try:
                self.client.run_write(fact_cypher, session=session)
            except Exception as e:
                logger.debug("Failed fact write %s: %s", fact.subject, e)


def _sanitize(text: str) -> str:
    """Escape quotes for safe inline Cypher strings."""
    if not text:
        return ""
    return text.replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
