#!/usr/bin/env python3
"""
scripts/run_ingest.py — Production ingestion & indexing pipeline for Company Brain.

Loads the ~812 staged gold documents, builds the local all-MiniLM vector store,
and ingests Document nodes, Entities, and Facts into HydraDB.

This local dev environment's HydraDB graph-node process restarts every
1-2 minutes (its garbage collector can't do conditional writes against the
local-filesystem storage backend it's configured with), so a single failed
write can no longer be allowed to either abort the whole run or pass
silently. Each document's writes are retried with reconnect on failure, and
documents that still have failed writes after retries are collected and
reported at the end instead of being swallowed into "Ingestion Finished
Successfully".
"""

import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain import config
from company_brain.graph.client import GraphClient
from company_brain.graph.loader import GraphLoader
from company_brain.indexing.vector_store import VectorStore
from company_brain.extraction.hybrid_extractor import extract_entities_and_facts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_ingest")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STAGED_FILE = PROJECT_ROOT / "data" / "staged_gold_docs.json"

# How many times to retry a document's writes if any of them failed, and how
# long to back off between reconnect attempts. HydraDB's observed down-window
# after a restart has been up to ~80s in this environment.
MAX_DOC_RETRIES = 4
RECONNECT_DELAY_SECONDS = 8


def connect_with_retry(tries: int = 10, delay: float = 8.0):
    """Returns a connected GraphClient, or None if every attempt failed.

    Deliberately never raises: an earlier version raised RuntimeError after
    exhausting its tries, and since that call happened *inside* the
    per-document retry loop below with no try/except around it, a single
    unusually long HydraDB down-window (this environment's has exceeded 90s)
    crashed the entire ingest after only ~300/812 documents. A reconnect
    failure now just means "this attempt didn't get a client" and is handled
    by the caller's own bounded retry accounting instead of aborting the run.
    """
    last_exc = None
    for attempt in range(tries):
        try:
            client = GraphClient()
            if client.ping():
                return client
            client.close()
        except Exception as e:
            last_exc = e
        if attempt < tries - 1:
            time.sleep(delay)
    logger.warning("Could not connect to HydraDB at %s after %d attempts: %s", config.BOLT_URI, tries, last_exc)
    return None


def main():
    logger.info("=== Starting Step 1: Ingestion & Vector Indexing Pipeline ===")

    # 1. Ensure staged docs exist
    if not STAGED_FILE.exists():
        logger.info("Staged docs not found. Running extract_gold_docs.py...")
        from scripts.extract_gold_docs import main as extract_main
        extract_main()

    with open(STAGED_FILE, "r", encoding="utf-8") as f:
        staged_docs = json.load(f)

    doc_list = list(staged_docs.values())
    total_docs = len(doc_list)
    logger.info("Loaded %d staged gold documents.", total_docs)

    # 2. Build local dense chunk vector index (Zero Truncation)
    logger.info("Chunking full corpus and building passage vector index with all-MiniLM-L6-v2...")
    from company_brain.indexing.chunker import DocumentChunker
    chunker = DocumentChunker(chunk_size=1000, chunk_overlap=200)
    all_chunks = chunker.chunk_all_documents(staged_docs)
    logger.info("Generated %d passages from %d documents.", len(all_chunks), len(staged_docs))

    vstore = VectorStore()
    vstore.build_chunk_index(all_chunks)
    logger.info("[OK] Chunk vector index successfully built and saved (%d embeddings).", len(all_chunks))

    # 3. Connect to HydraDB and load graph elements
    logger.info("Connecting to HydraDB via Bolt...")
    client = connect_with_retry(tries=15, delay=8.0)
    if client is None:
        logger.error("HydraDB is not reachable at %s after repeated attempts. Please check it's running "
                     "(scripts/start_hydradb.sh or the WSL/docker setup) and try again.", config.BOLT_URI)
        sys.exit(1)
    loader = GraphLoader(client)
    start_time = time.time()

    total_entities = 0
    total_facts = 0
    fully_failed_docs: list[str] = []
    partially_failed_docs: list[tuple[str, dict]] = []

    logger.info("Ingesting documents and extracting ontology into HydraDB...")
    for idx, doc in enumerate(doc_list):
        doc_id = doc["doc_id"]
        source = doc["source"]
        created_at = doc.get("created_at", "2026-01-01T00:00:00Z")
        title = doc.get("title", doc_id)
        text = doc.get("text", "")

        extraction = extract_entities_and_facts(
            doc_text=text,
            doc_id=doc_id,
            source=source,
            title=title,
            created_at=created_at,
        )
        expected_writes = len(extraction.entities) + len(extraction.facts)

        stats = {"entities_ok": 0, "entities_failed": 0, "facts_ok": 0, "facts_failed": 0}
        for attempt in range(MAX_DOC_RETRIES):
            if client is None:
                # A previous attempt's reconnect failed outright (returned
                # None rather than raising -- see connect_with_retry). Try
                # again with a short, bounded budget rather than skipping
                # straight to "this document failed": HydraDB's down-windows
                # are usually much shorter than the time already spent
                # processing prior documents in this loop.
                client = connect_with_retry(tries=3, delay=RECONNECT_DELAY_SECONDS)
                if client is not None:
                    loader = GraphLoader(client)

            if client is None:
                stats = {"entities_ok": 0, "entities_failed": len(extraction.entities), "facts_ok": 0, "facts_failed": len(extraction.facts)}
            else:
                try:
                    stats = loader.load_document(
                        doc_id=doc_id,
                        source=source,
                        created_at=created_at,
                        text_snippet=text[:500],
                        extraction=extraction,
                        title=title,
                    )
                except Exception as e:
                    logger.warning("[%s] load_document raised (attempt %d/%d): %s", doc_id, attempt + 1, MAX_DOC_RETRIES, e)
                    stats = {"entities_ok": 0, "entities_failed": len(extraction.entities), "facts_ok": 0, "facts_failed": len(extraction.facts)}
                    client = None  # force a fresh connection next attempt; this one is presumed dead

            if stats["entities_failed"] == 0 and stats["facts_failed"] == 0:
                break  # this document fully succeeded

            if attempt < MAX_DOC_RETRIES - 1:
                logger.warning(
                    "[%s] %d/%d writes failed, reconnecting and retrying (attempt %d/%d)...",
                    doc_id, stats["entities_failed"] + stats["facts_failed"], expected_writes,
                    attempt + 1, MAX_DOC_RETRIES,
                )
                if client is not None:
                    try:
                        client.close()
                    except Exception:
                        pass
                    client = None
                time.sleep(RECONNECT_DELAY_SECONDS)

        total_entities += stats["entities_ok"]
        total_facts += stats["facts_ok"]

        if stats["entities_ok"] == 0 and stats["facts_ok"] == 0 and expected_writes > 0:
            fully_failed_docs.append(doc_id)
        elif stats["entities_failed"] > 0 or stats["facts_failed"] > 0:
            partially_failed_docs.append((doc_id, dict(stats)))

        if (idx + 1) % 100 == 0 or (idx + 1) == total_docs:
            elapsed = time.time() - start_time
            logger.info("  [%d / %d docs] Loaded (%d entities, %d facts) in %.1fs -- %d fully failed, %d partial",
                        idx + 1, total_docs, total_entities, total_facts, elapsed,
                        len(fully_failed_docs), len(partially_failed_docs))

    if client is not None:
        client.close()

    logger.info("=== Ingestion Finished ===")
    logger.info("  Total Documents Attempted:  %d", total_docs)
    logger.info("  Total Entities Written:     %d", total_entities)
    logger.info("  Total Facts Written:        %d", total_facts)
    logger.info("  Fully Failed Documents:     %d", len(fully_failed_docs))
    logger.info("  Partially Failed Documents: %d", len(partially_failed_docs))
    logger.info("  Time Elapsed:                %.2fs", time.time() - start_time)

    if fully_failed_docs:
        logger.warning("Fully failed doc_ids (zero writes survived retries): %s",
                        fully_failed_docs[:20] if len(fully_failed_docs) > 20 else fully_failed_docs)
    if partially_failed_docs:
        logger.warning("Partially failed doc_ids (some writes survived retries): %s",
                        [d for d, _ in partially_failed_docs[:20]])

    if fully_failed_docs or partially_failed_docs:
        logger.warning(
            "Ingestion completed with %d fully-failed and %d partially-failed documents out of %d. "
            "This is expected if HydraDB restarted during the run; re-running this script is safe "
            "(writes are idempotent by id) and will fill in what's still missing.",
            len(fully_failed_docs), len(partially_failed_docs), total_docs,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
