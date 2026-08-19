"""
graph/loader.py — bulk loader for Document, Entity, and Fact nodes into HydraDB.

Obeys HydraDB Cypher rules (verified empirically against a live instance):
- Integer node `id` property (generated deterministically from string identifiers)
- Only one-hop edge CREATE patterns are executable: (Document)-[:MENTIONS]->(Entity)
  and (Document)-[:HAS_FACT]->(Fact). A standalone `CREATE (d:Document {...})`
  with no edge is rejected outright ("only one-hop edge patterns are executable
  in Query engine CREATE") -- this was already true in the pre-existing code,
  just silently swallowed by its bare `except Exception`, so the Document node
  has only ever actually been created as a side effect of its first
  MENTIONS/HAS_FACT write, never by a dedicated statement.
- `MERGE` is rejected if followed by another clause ("MERGE with following
  clauses is not executable in Query engine"), so idempotent upsert-by-id is
  not available here -- CREATE is genuinely the only option.
- Auto-commit RUN queries
- All writes use $param binding (see graph/topology.py header for why: HydraDB
  supports it and it avoids hand-rolled string escaping entirely)

HydraDB resolves nodes by `id` and CREATE against an existing id replaces its
whole property bag (last write wins), which is why every prior write of the
Document node silently erased its title once a title-less write followed.
Fixed by carrying `title` (and every other Document property) on *every*
CREATE of the Document node, not just the first -- so it no longer matters
which write is last, they all agree.
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
    def __init__(self, client: GraphClient, workspace_id: Optional[str] = None) -> None:
        self.client = client
        self.workspace_id = workspace_id

    def load_document(
        self,
        doc_id: str,
        source: str,
        created_at: str,
        text_snippet: str,
        extraction: DocumentExtractionResult,
        title: str = "",
    ) -> Dict[str, int]:
        """
        Loads a document and its extracted entities and facts into HydraDB.
        Returns write counts ({entities_ok, entities_failed, facts_ok,
        facts_failed}) rather than swallowing failures silently.
        """
        stats = {"entities_ok": 0, "entities_failed": 0, "facts_ok": 0, "facts_failed": 0}
        doc_int_id = string_to_int_id(f"doc_{doc_id}")
        source_trust = trust_for(source)
        doc_props = {
            "doc_int_id": doc_int_id,
            "doc_id": doc_id,
            "source": source,
            "title": title,
            "created_at": created_at,
        }
        if self.workspace_id:
            doc_props["workspace_id"] = self.workspace_id

        ws_prop = ", workspace_id: $workspace_id" if self.workspace_id else ""

        # 1. Load entities via one-hop (Document)-[:MENTIONS]->(Entity) pattern.
        for entity in extraction.entities:
            entity_key = f"{entity.entity_type}_{entity.name}"
            entity_int_id = string_to_int_id(entity_key)
            label = entity.entity_type if entity.entity_type in ["Person", "Org", "Project", "Ticket", "Deal"] else "Entity"

            cypher = (
                f"CREATE (d:Document {{id: $doc_int_id, doc_id: $doc_id, source: $source, "
                f"title: $title, created_at: $created_at{ws_prop}}})"
                f"-[r:MENTIONS {{source: $source, timestamp: $created_at, doc_id: $doc_id{ws_prop}}}]->"
                f"(e:{label} {{id: $entity_int_id, name: $name, source: $source{ws_prop}}})"
            )
            try:
                self.client.run_write(cypher, {
                    **doc_props,
                    "entity_int_id": entity_int_id,
                    "name": entity.name,
                })
                stats["entities_ok"] += 1
            except Exception as e:
                stats["entities_failed"] += 1
                logger.debug("Failed to write entity %s: %s", entity.name, e)

        # 2. Load facts via one-hop (Document)-[:HAS_FACT]->(Fact) pattern.
        for idx, fact in enumerate(extraction.facts):
            fact_key = f"fact_{doc_id}_{idx}"
            fact_int_id = string_to_int_id(fact_key)

            cypher = (
                f"CREATE (d:Document {{id: $doc_int_id, doc_id: $doc_id, source: $source, "
                f"title: $title, created_at: $created_at{ws_prop}}})"
                f"-[r:HAS_FACT {{source: $source, timestamp: $created_at, doc_id: $doc_id{ws_prop}}}]->"
                f"(f:Fact {{id: $fact_int_id, subject: $subject, attribute: $attribute, "
                f"value: $value, trust_score: $trust_score, doc_id: $doc_id{ws_prop}}})"
            )
            try:
                self.client.run_write(cypher, {
                    **doc_props,
                    "fact_int_id": fact_int_id,
                    "subject": fact.subject,
                    "attribute": fact.attribute,
                    "value": fact.value,
                    "trust_score": source_trust,
                })
                stats["facts_ok"] += 1
            except Exception as e:
                stats["facts_failed"] += 1
                logger.debug("Failed to write fact %s: %s", fact.subject, e)

        return stats
