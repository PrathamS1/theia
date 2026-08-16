"""
graph/loader.py — bulk loader for Document, Entity, and Fact nodes into HydraDB.

Complies strictly with HydraDB Cypher rules:
- Positive 32-bit integer node `id` property
- Single one-hop CREATE pattern: (Document)-[:MENTIONS]->(Entity) and (Document)-[:HAS_FACT]->(Fact)
- Parameterized queries (no string interpolation) to prevent Cypher parse errors from special characters
- High-throughput execution with persistent Neo4j Bolt session reuse
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
        Uses parameterized Cypher queries to avoid parse errors from special characters in values.
        """
        doc_int_id = string_to_int_id(f"doc_{doc_id}")
        source_trust = trust_for(source)
        has_written = False

        # 1. Create Entity Nodes: (Document)-[:MENTIONS]->(Entity)
        for entity in extraction.entities:
            entity_key = f"{entity.entity_type}_{entity.name}"
            entity_int_id = string_to_int_id(entity_key)
            label = entity.entity_type if entity.entity_type in ["Person", "Org", "Project", "Ticket", "Deal"] else "Entity"

            cypher = (
                f"CREATE (d:Document {{id: $did, doc_id: $doc_id, source: $source, created_at: $ts}})"
                f"-[:MENTIONS]->"
                f"(e:{label} {{id: $eid, name: $name, source: $source}})"
            )
            params = {
                "did": doc_int_id,
                "doc_id": doc_id,
                "source": source,
                "ts": created_at,
                "eid": entity_int_id,
                "name": entity.name or "",
            }
            try:
                self.client.run_write(cypher, params, session=session)
                has_written = True
            except Exception as e:
                logger.debug("Failed entity write %s: %s", entity.name, e)

        # 2. Create Fact Nodes: (Document)-[:HAS_FACT]->(Fact)
        for idx, fact in enumerate(extraction.facts):
            fact_key = f"fact_{doc_id}_{idx}"
            fact_int_id = string_to_int_id(fact_key)

            cypher = (
                "CREATE (d:Document {id: $did, doc_id: $doc_id, source: $source, created_at: $ts})"
                "-[:HAS_FACT]->"
                "(f:Fact {id: $fid, subject: $subject, attribute: $attribute, value: $value, trust_score: $trust, doc_id: $doc_id})"
            )
            params = {
                "did": doc_int_id,
                "doc_id": doc_id,
                "source": source,
                "ts": created_at,
                "fid": fact_int_id,
                "subject": fact.subject or "",
                "attribute": fact.attribute or "",
                "value": fact.value or "",
                "trust": source_trust,
            }
            try:
                self.client.run_write(cypher, params, session=session)
                has_written = True
            except Exception as e:
                logger.debug("Failed fact write %s: %s", fact.subject, e)

        # 3. Fallback for docs with no entities/facts
        if not has_written:
            cypher = (
                "CREATE (d:Document {id: $did, doc_id: $doc_id, source: $source, created_at: $ts})"
                "-[:MENTIONS]->"
                "(e:Document {id: $did, doc_id: $doc_id, source: $source, created_at: $ts})"
            )
            params = {
                "did": doc_int_id,
                "doc_id": doc_id,
                "source": source,
                "ts": created_at,
            }
            try:
                self.client.run_write(cypher, params, session=session)
            except Exception as e:
                logger.debug("Failed standalone doc write %s: %s", doc_id, e)
