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
from company_brain.integrations.normalizers.github_normalizer import GitHubNormalizer
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

        return self._process_and_index_docs(all_normalized_docs, source_label="Slack")

    def sync_github(
        self,
        selected_repos: Optional[List[str]] = None,
        max_repos: int = 10,
        prs_per_repo: int = 20,
        issues_per_repo: int = 20,
    ) -> Dict[str, Any]:
        """
        Executes an incremental sync for GitHub:
        1. Checks connection
        2. Discovers repositories
        3. Filters to user-selected repositories (or top max_repos)
        4. Fetches PRs and Issues for each selected repo
        5. Normalizes via GitHubNormalizer
        6. Chunks, builds local vector embeddings, and writes to HydraDB with workspace isolation
        """
        logger.info("Starting GitHub sync for workspace=%s (selected_repos=%s)...", self.user_id, selected_repos)

        # 1. Verify connection
        status_info = self.composio.get_connection_status(user_id=self.user_id, toolkit="github")
        if status_info.get("status") != "ACTIVE" and status_info.get("status") != "CONNECTED":
            return {
                "status": "NOT_CONNECTED",
                "message": f"GitHub connection is not active (current: {status_info.get('status')}). Please connect GitHub first.",
                "user_id": self.user_id,
            }

        # 2. Fetch Repositories
        repos = self.composio.fetch_github_repositories(user_id=self.user_id)
        if not repos:
            return {
                "status": "SUCCESS",
                "message": "GitHub sync completed, but no accessible repositories were found.",
                "documents_synced": 0,
            }

        # Filter to selected repos if specified by user
        if selected_repos:
            selected_set = {r.strip().lower() for r in selected_repos if r.strip()}
            target_repos = [
                r for r in repos
                if (r.get("full_name", "").lower() in selected_set or r.get("name", "").lower() in selected_set)
            ]
            logger.info("Filtered to %d user-selected repositories out of %d available.", len(target_repos), len(repos))
            if not target_repos:
                # If exact match wasn't found, try matching by repo basename
                target_repos = [
                    r for r in repos
                    if any(sel in r.get("full_name", "").lower() for sel in selected_set)
                ]
        else:
            target_repos = repos[:max_repos]

        logger.info("Syncing %d selected repositories for workspace=%s...", len(target_repos), self.user_id)

        normalizer = GitHubNormalizer()
        all_normalized_docs: List[Dict[str, Any]] = []

        for repo in target_repos:
            repo_name = repo.get("name") or repo.get("full_name", "")
            owner = repo.get("owner", {}).get("login") if isinstance(repo.get("owner"), dict) else ""
            if not repo_name:
                continue
            if not owner and "/" in repo_name:
                owner, repo_name = repo_name.split("/", 1)
            elif not owner:
                owner = self.user_id

            # Normalize repository metadata
            repo_doc = normalizer.normalize_repository(repo)
            if repo_doc:
                repo_doc["workspace_id"] = self.user_id
                all_normalized_docs.append(repo_doc)

            # Fetch & normalize PRs
            prs = self.composio.fetch_github_pull_requests(
                owner=owner,
                repo=repo_name,
                user_id=self.user_id,
                limit=prs_per_repo,
            )
            for pr in prs:
                doc = normalizer.normalize_pull_request(pr, repo_name=repo_name)
                if doc:
                    doc["workspace_id"] = self.user_id
                    all_normalized_docs.append(doc)

            # Fetch & normalize Issues
            issues = self.composio.fetch_github_issues(
                owner=owner,
                repo=repo_name,
                user_id=self.user_id,
                limit=issues_per_repo,
            )
            for issue in issues:
                doc = normalizer.normalize_issue(issue, repo_name=repo_name)
                if doc:
                    doc["workspace_id"] = self.user_id
                    all_normalized_docs.append(doc)

        if not all_normalized_docs:
            return {
                "status": "SUCCESS",
                "message": "GitHub sync completed, but no items were extracted.",
                "documents_synced": 0,
            }

        logger.info("Normalized %d live GitHub documents for workspace=%s.", len(all_normalized_docs), self.user_id)
        return self._process_and_index_docs(all_normalized_docs, source_label="GitHub")

    def _process_and_index_docs(self, all_normalized_docs: List[Dict[str, Any]], source_label: str = "Live") -> Dict[str, Any]:
        """
        Shared ingestion pipeline: caching, chunking, vector indexing, graph insertion, and resolution.
        """
        # Load existing staged docs to merge Slack + GitHub cleanly
        existing_docs = {}
        if self.docs_cache_file.exists():
            try:
                with open(self.docs_cache_file, "r", encoding="utf-8") as f:
                    existing_docs = json.load(f)
            except Exception:
                pass

        for d in all_normalized_docs:
            existing_docs[d["doc_id"]] = d

        with open(self.docs_cache_file, "w", encoding="utf-8") as f:
            json.dump(existing_docs, f, indent=2)

        # Index all documents for this workspace
        all_docs_to_index = list(existing_docs.values())

        # Full-passage chunking
        chunker = DocumentChunker()
        all_chunks = []
        for doc in all_docs_to_index:
            chunks = chunker.chunk_document(
                doc_id=doc["doc_id"],
                text=doc.get("text", ""),
                meta=doc.get("metadata", {}),
            )
            all_chunks.extend(chunks)

        logger.info("Created %d passage chunks from %d total documents for workspace=%s.", len(all_chunks), len(all_docs_to_index), self.user_id)

        # Dense MiniLM vector embedding & index build
        vstore = VectorStore(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vstore.build_chunk_index(all_chunks)
        vstore.save(vector_dir=str(self.vectors_dir))
        logger.info("Built and saved live vector index for %d chunks in %s.", len(all_chunks), self.vectors_dir)

        # Extract entities and triple facts
        enriched_docs = []
        total_facts = 0
        for doc in all_normalized_docs:
            extracted_res = extract_entities_and_facts(
                doc_text=doc.get("text", ""),
                doc_id=doc["doc_id"],
                source=doc.get("source", source_label.lower()),
                title=doc.get("title", ""),
                created_at=doc.get("created_at", ""),
            )
            enriched_item = {
                "doc_id": doc["doc_id"],
                "source": doc.get("source", source_label.lower()),
                "created_at": doc.get("created_at", ""),
                "title": doc.get("title", ""),
                "text": doc.get("text", ""),
                "workspace_id": self.user_id,
                "extraction": extracted_res,
            }
            enriched_docs.append(enriched_item)
            total_facts += len(extracted_res.facts)

        # Load into HydraDB over Bolt
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
            logger.info("Loaded %d %s documents and %d facts into HydraDB for workspace=%s.", len(enriched_docs), source_label, total_facts, self.user_id)

            # Run Entity & Temporal Resolution scoped strictly to workspace_id
            try:
                same_as_count = resolve_entities(client, workspace_id=self.user_id)
                conflict_count = detect_and_tag_conflicts(client, workspace_id=self.user_id)
                logger.info("Workspace resolution complete: %d SAME_AS edges, %d SUPERSEDES edges.", same_as_count, conflict_count)
            except Exception as e:
                logger.warning("Entity resolution encountered an error: %s", e)

        # Clear cached topology for this workspace so UI immediately sees new graph
        try:
            from company_brain.graph.topology import cache as topology_cache
            topology_cache.clear_cache(workspace_id=self.user_id)
        except Exception:
            pass

        return {
            "status": "SUCCESS",
            "user_id": self.user_id,
            "source": source_label.lower(),
            "documents_synced": len(all_normalized_docs),
            "chunks_vectorized": len(all_chunks),
            "facts_extracted": total_facts,
            "resolution": {
                "same_as_edges": same_as_count,
                "supersedes_edges": conflict_count,
            },
        }
