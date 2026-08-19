"""
sync_worker.py — Background coordinator for live SaaS ingestion, vector indexing, and HydraDB graph updates.
"""

from typing import Dict, Any, List, Optional
import os
import json
import logging
from pathlib import Path

from company_brain.config import LIVE_DATA_DIR
from company_brain.integrations.composio_client import ComposioManager
from company_brain.integrations.normalizers.slack_normalizer import SlackNormalizer
from company_brain.indexing.chunker import DocumentChunker
from company_brain.indexing.vector_store import VectorStore
from company_brain.extraction.hybrid_extractor import extract_entities_and_facts
from company_brain.graph.client import GraphClient
from company_brain.graph.loader import GraphLoader
from company_brain.resolution.resolve import resolve_entities
from company_brain.resolution.conflicts import detect_and_tag_conflicts

logger = logging.getLogger("company_brain.integrations.sync")


class LiveSyncWorker:
    """
    Coordinates fetching live enterprise SaaS data, transforming, chunking,
    vectorizing, and updating HydraDB and local vector stores.
    """

    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self.composio = ComposioManager()
        self.user_live_dir = LIVE_DATA_DIR / user_id
        self.user_live_dir.mkdir(parents=True, exist_ok=True)
        self.vectors_dir = self.user_live_dir / "vectors"
        self.vectors_dir.mkdir(parents=True, exist_ok=True)
        self.docs_cache_file = self.user_live_dir / "live_staged_docs.json"

    def sync_slack(self, max_channels: int = 5, messages_per_channel: int = 30) -> Dict[str, Any]:
        """
        Pulls live Slack messages, chunks, vectorizes, and writes into HydraDB.
        """
        logger.info("Starting Slack sync for user_id=%s...", self.user_id)

        # 1. Verify connection status
        conn = self.composio.get_connection_status(user_id=self.user_id, toolkit="slack")
        if conn.get("status") != "ACTIVE":
            logger.warning("Slack is not in ACTIVE state (current: %s)", conn.get("status"))
            return {
                "status": "ERROR",
                "message": f"Slack connection is not ACTIVE. Current status: {conn.get('status')}. Please connect Slack first.",
                "connection": conn,
            }

        # 2. Fetch accessible channels
        raw_channels = self.composio.fetch_slack_channels(user_id=self.user_id)
        if not raw_channels:
            return {
                "status": "ERROR",
                "message": "No accessible Slack channels were returned by the API. Please ensure your Slack connection has channel read permissions (channels:read, groups:read).",
                "documents_synced": 0,
            }

        all_normalized_docs: List[Dict[str, Any]] = []

        # 3. Pull messages per channel
        for ch in raw_channels[:max_channels]:
            ch_id = ch.get("id", "")
            ch_name = ch.get("name", ch_id)
            if not ch_id:
                continue

            logger.info("Fetching messages from #%s (%s)...", ch_name, ch_id)

            raw_msgs = self.composio.fetch_slack_messages(
                channel_id=ch_id,
                user_id=self.user_id,
                limit=messages_per_channel,
            )

            docs = SlackNormalizer.normalize_channel_history(
                raw_msgs,
                channel_name=ch_name,
                channel_id=ch_id,
            )
            # Tag with workspace_id for strict multi-tenant isolation
            for d in docs:
                d["workspace_id"] = self.user_id
            all_normalized_docs.extend(docs)

        if not all_normalized_docs:
            return {
                "status": "SUCCESS",
                "message": "Slack sync completed, but no messages were found in the connected channels.",
                "documents_synced": 0,
            }

        logger.info("Normalized %d live Slack documents for workspace=%s.", len(all_normalized_docs), self.user_id)

        # 4. Save live documents cache
        staged_dict = {d["doc_id"]: d for d in all_normalized_docs}
        with open(self.docs_cache_file, "w", encoding="utf-8") as f:
            json.dump(staged_dict, f, indent=2)

        # 5. Full-passage chunking
        chunker = DocumentChunker()
        all_chunks = []
        for doc in all_normalized_docs:
            chunks = chunker.chunk_document(
                doc_id=doc["doc_id"],
                text=doc.get("text", ""),
                meta=doc.get("metadata", {}),
            )
            all_chunks.extend(chunks)

        logger.info("Created %d passage chunks from %d live documents.", len(all_chunks), len(all_normalized_docs))

        # 6. Dense MiniLM vector embedding & index build (saved in data/live/{user_id}/vectors/)
        vstore = VectorStore(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vstore.build_chunk_index(all_chunks)
        vstore.save(vector_dir=str(self.vectors_dir))
        logger.info("Built and saved live vector index for %d chunks in %s.", len(all_chunks), self.vectors_dir)

        # 7. Extract entities and triple facts
        enriched_docs = []
        total_facts = 0
        for doc in all_normalized_docs:
            extracted_res = extract_entities_and_facts(
                doc_text=doc.get("text", ""),
                doc_id=doc["doc_id"],
                source=doc.get("source", "slack"),
                title=doc.get("title", ""),
                created_at=doc.get("created_at", ""),
            )
            enriched_item = {
                "doc_id": doc["doc_id"],
                "source": doc.get("source", "slack"),
                "created_at": doc.get("created_at", ""),
                "title": doc.get("title", ""),
                "text": doc.get("text", ""),
                "workspace_id": self.user_id,
                "extraction": extracted_res,
            }
            enriched_docs.append(enriched_item)
            total_facts += len(extracted_res.facts)

        # 8. Load into HydraDB over Bolt
        same_as_count = 0
        conflict_count = 0
        with GraphClient() as client:
            loader = GraphLoader(client, workspace_id=self.user_id)
            for enriched in enriched_docs:
                loader.load_document(
                    doc_id=enriched["doc_id"],
                    source=enriched["source"],
                    created_at=enriched.get("created_at", ""),
                    text_snippet=enriched.get("text", "")[:300],
                    extraction=enriched["extraction"],
                    title=enriched.get("title", ""),
                    workspace_id=self.user_id,
                )
            logger.info("Loaded %d documents and %d facts into HydraDB for workspace=%s.", len(enriched_docs), total_facts, self.user_id)

            # 9. Run Entity & Temporal Resolution scoped strictly to workspace_id
            try:
                same_as_count = resolve_entities(client, workspace_id=self.user_id)
                conflict_count = detect_and_tag_conflicts(client, workspace_id=self.user_id)
                logger.info("Workspace resolution complete: %d SAME_AS edges, %d SUPERSEDES edges.", same_as_count, conflict_count)
            except Exception as e:
                logger.warning("Entity resolution encountered an error: %s", e)

        return {
            "status": "SUCCESS",
            "user_id": self.user_id,
            "documents_synced": len(all_normalized_docs),
            "chunks_vectorized": len(all_chunks),
            "facts_extracted": total_facts,
            "resolution": {
                "same_as_edges": same_as_count,
                "supersedes_edges": conflict_count,
            },
        }
