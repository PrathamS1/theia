#!/usr/bin/env python3
"""
scripts/run_ingest.py — Entry point for Phase 1 Data Ingestion & LLM Extraction.

Iterates over documents in data/raw/, calls Gemini LLM extractor,
and loads Document nodes, extracted Entities, and Facts into HydraDB.

Supports idempotency, automatic circuit breaker on 429 quota exhaustion,
and optional --heuristic flag for instant local extraction.

Usage:
    python3 scripts/run_ingest.py [--limit N] [--reset] [--force] [--heuristic]
"""

import argparse
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain import config
from company_brain.graph.client import GraphClient
from company_brain.graph.loader import GraphLoader
from company_brain.extraction.extractor import extract_from_document
from company_brain.ingest.sources.loader_base import iter_documents_from_dir

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_ingest")


def main():
    parser = argparse.ArgumentParser(description="Ingest Redwood documents into HydraDB")
    parser.add_argument("--limit", type=int, default=0, help="Max documents to ingest (0 = all)")
    parser.add_argument("--reset", action="store_true", help="Clear existing graph nodes before ingesting")
    parser.add_argument("--force", action="store_true", help="Force re-ingest documents even if already in HydraDB")
    parser.add_argument("--heuristic", action="store_true", help="Bypass LLM API calls and use 100% rule-based heuristic extraction")
    args = parser.parse_args()

    raw_dir = config.RAW_DATA_DIR
    if not raw_dir.exists():
        logger.error("Raw data directory %s does not exist. Run bash scripts/download_dataset.sh first.", raw_dir)
        sys.exit(1)

    if args.heuristic:
        logger.info("Heuristic flag enabled. Bypassing LLM API calls and using rule-based extraction for all documents.")

    logger.info("Starting ingestion from %s...", raw_dir)

    with GraphClient() as client:
        if not client.ping():
            logger.error("HydraDB is not reachable. Ensure graph-node is running.")
            sys.exit(1)

        # Handle reset flag
        if args.reset:
            logger.info("Reset flag provided. Clearing existing nodes from HydraDB...")
            try:
                client.run_write("MATCH (d:Document) DETACH DELETE d")
                client.run_write("MATCH (f:Fact) DETACH DELETE f")
                client.run_write("MATCH (e:Person) DETACH DELETE e")
                client.run_write("MATCH (o:Org) DETACH DELETE o")
                logger.info("Existing graph data cleared.")
            except Exception as e:
                logger.warning("Reset operation warning: %s", e)

        # Check existing ingested documents for idempotency
        existing_doc_ids = set()
        if not args.force and not args.reset:
            try:
                rows = client.run("MATCH (d:Document) RETURN d.doc_id AS doc_id")
                existing_doc_ids = set(str(r["doc_id"]) for r in rows if r.get("doc_id"))
                if existing_doc_ids:
                    logger.info("Found %d documents already ingested in HydraDB.", len(existing_doc_ids))
            except Exception as e:
                logger.debug("Could not fetch existing document IDs: %s", e)

        loader = GraphLoader(client)
        count = 0

        for doc in iter_documents_from_dir(raw_dir):
            if args.limit > 0 and count >= args.limit:
                break

            doc_id = doc["doc_id"]
            source = doc["source"]
            created_at = doc["created_at"]
            text = doc["text"]

            # Skip if already ingested (Idempotency)
            if doc_id in existing_doc_ids and not args.force:
                logger.info("[skip] doc_id=%s already ingested in HydraDB.", doc_id)
                continue

            logger.info("[%d] Extracting doc_id=%s source=%s", count + 1, doc_id, source)
            
            # LLM or Heuristic extraction
            extraction = extract_from_document(
                doc_text=text,
                doc_id=doc_id,
                source=source,
                force_heuristic=args.heuristic,
            )
            logger.info("  -> Found %d entities, %d facts", len(extraction.entities), len(extraction.facts))

            # Load into HydraDB
            loader.load_document(
                doc_id=doc_id,
                source=source,
                created_at=created_at,
                text_snippet=text[:500],
                extraction=extraction,
            )
            existing_doc_ids.add(doc_id)
            count += 1

        logger.info("Ingestion complete. Processed %d new documents.", count)


if __name__ == "__main__":
    main()
