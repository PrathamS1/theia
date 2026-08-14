#!/usr/bin/env python3
"""
scripts/run_ingest.py — Entry point for Phase 1 Data Ingestion & LLM Extraction.

Iterates over all documents in data/raw/, calls Gemini LLM extractor,
and loads Document nodes, extracted Entities, and Facts into HydraDB.

Usage:
    python3 scripts/run_ingest.py [--limit N]
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
    args = parser.parse_args()

    raw_dir = config.RAW_DATA_DIR
    if not raw_dir.exists():
        logger.error("Raw data directory %s does not exist. Run bash scripts/download_dataset.sh first.", raw_dir)
        sys.exit(1)

    logger.info("Starting ingestion from %s...", raw_dir)

    with GraphClient() as client:
        if not client.ping():
            logger.error("HydraDB is not reachable. Ensure graph-node is running.")
            sys.exit(1)

        loader = GraphLoader(client)
        count = 0

        for doc in iter_documents_from_dir(raw_dir):
            if args.limit > 0 and count >= args.limit:
                break

            doc_id = doc["doc_id"]
            source = doc["source"]
            created_at = doc["created_at"]
            text = doc["text"]

            logger.info("[%d] Extracting doc_id=%s source=%s", count + 1, doc_id, source)
            
            # LLM extraction via Gemini
            extraction = extract_from_document(doc_text=text, doc_id=doc_id, source=source)
            logger.info("  -> Found %d entities, %d facts", len(extraction.entities), len(extraction.facts))

            # Load into HydraDB
            loader.load_document(
                doc_id=doc_id,
                source=source,
                created_at=created_at,
                text_snippet=text[:500],
                extraction=extraction,
            )
            count += 1

        logger.info("Ingestion complete. Processed %d documents.", count)


if __name__ == "__main__":
    main()
