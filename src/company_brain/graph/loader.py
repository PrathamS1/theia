"""
graph/loader.py — bulk loader for Document, Entity, and Fact nodes into HydraDB.

Obeys HydraDB Cypher rules:
- Integer node `id` property (generated deterministically from string identifiers)
- One-hop CREATE pattern: (Document)-[:MENTIONS]->(Entity) and (Document)-[:HAS_FACT]->(Fact)
- Auto-commit RUN queries
"""

import logging
import zlib
from typing import Dict, Any, List

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
        title: str = "",
    ) -> None:
        """
        Loads a document and its extracted entities and facts into HydraDB.
        """
        doc_int_id = string_to_int_id(f"doc_{doc_id}")
        source_trust = trust_for(source)

        # 0. Always ensure the Document node itself exists
        doc_cypher = (
            f"CREATE (d:Document {{id: {doc_int_id}, doc_id: '{doc_id}', source: '{source}', "
            f"title: '{_sanitize(title)}', created_at: '{created_at}'}})"
        )
        try:
            self.client.run_write(doc_cypher)
        except Exception as e:
            logger.debug("Document base node write: %s", e)

        # 1. Load entities via one-hop (Document)-[:MENTIONS]->(Entity) pattern
        for idx, entity in enumerate(extraction.entities):
            entity_key = f"{entity.entity_type}_{entity.name}"
            entity_int_id = string_to_int_id(entity_key)
            label = entity.entity_type if entity.entity_type in ["Person", "Org", "Project", "Ticket", "Deal"] else "Entity"

            cypher = (
                f"CREATE (d:Document {{id: {doc_int_id}, doc_id: '{doc_id}', source: '{source}', created_at: '{created_at}'}})"
                f"-[:MENTIONS {{source: '{source}', timestamp: '{created_at}', doc_id: '{doc_id}'}}]->"
                f"(e:{label} {{id: {entity_int_id}, name: '{_sanitize(entity.name)}', source: '{source}'}})"
            )
            try:
                self.client.run_write(cypher)
            except Exception as e:
                logger.debug("Failed to write entity %s: %s", entity.name, e)

        # 2. Load facts via one-hop (Document)-[:HAS_FACT]->(Fact) pattern
        for idx, fact in enumerate(extraction.facts):
            fact_key = f"fact_{doc_id}_{idx}"
            fact_int_id = string_to_int_id(fact_key)

            cypher = (
                f"CREATE (d:Document {{id: {doc_int_id}, doc_id: '{doc_id}', source: '{source}', created_at: '{created_at}'}})"
                f"-[:HAS_FACT {{source: '{source}', timestamp: '{created_at}', doc_id: '{doc_id}'}}]->"
                f"(f:Fact {{id: {fact_int_id}, subject: '{_sanitize(fact.subject)}', attribute: '{_sanitize(fact.attribute)}', value: '{_sanitize(fact.value)}', trust_score: {source_trust}, doc_id: '{doc_id}'}})"
            )
            try:
                self.client.run_write(cypher)
            except Exception as e:
                logger.debug("Failed to write fact %s: %s", fact.subject, e)


def _sanitize(text: str) -> str:
    """Escape quotes for safe inline Cypher strings."""
    if not text:
        return ""
    return text.replace("'", "\\'").replace('"', '\\"').replace("\n", " ").replace("\r", "")
