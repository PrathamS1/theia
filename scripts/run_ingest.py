#!/usr/bin/env python3
"""
scripts/run_ingest.py — Entry point for Phase 1 Data Ingestion & LLM Extraction.

Iterates over documents in data/raw/, calls Gemini LLM extractor (or heuristic fallback),
and loads Document nodes, extracted Entities, and Facts into HydraDB.

Supports multithreaded execution (--workers N), idempotency, and live tqdm progress bar.

Usage:
    python3 scripts/run_ingest.py [--limit N] [--workers N] [--reset] [--force] [--heuristic]
"""

import argparse
import sys
import logging
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain import config
from company_brain.graph.client import GraphClient
from company_brain.graph.loader import GraphLoader
from company_brain.extraction.extractor import extract_from_document
from company_brain.ingest.sources.loader_base import iter_documents_from_dir

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_ingest")


def _process_doc(doc: dict, loader: GraphLoader, existing_doc_ids: set, force: bool, heuristic: bool):
    doc_id = doc["doc_id"]
    source = doc["source"]
    created_at = doc["created_at"]
    text = doc["text"]

    if doc_id in existing_doc_ids and not force:
        return doc_id, True, 0, 0, source

    extraction = extract_from_document(
        doc_text=text,
        doc_id=doc_id,
        source=source,
        force_heuristic=heuristic,
    )

    loader.load_document(
        doc_id=doc_id,
        source=source,
        created_at=created_at,
        text_snippet=text[:500],
        extraction=extraction,
    )

    return doc_id, False, len(extraction.entities), len(extraction.facts), source


def main():
    parser = argparse.ArgumentParser(description="Ingest Redwood documents into HydraDB")
    parser.add_argument("--limit", type=int, default=0, help="Max documents to ingest (0 = all)")
    parser.add_argument("--workers", type=int, default=8, help="Number of parallel worker threads (default: 8)")
    parser.add_argument("--reset", action="store_true", help="Clear existing graph nodes before ingesting")
    parser.add_argument("--force", action="store_true", help="Force re-ingest documents even if already in HydraDB")
    parser.add_argument("--heuristic", action="store_true", help="Bypass LLM API calls and use 100% rule-based heuristic extraction")
    args = parser.parse_args()

    raw_dir = config.RAW_DATA_DIR
    if not raw_dir.exists():
        logger.error("Raw data directory %s does not exist. Run bash scripts/download_dataset.sh first.", raw_dir)
        sys.exit(1)

    if args.heuristic:
        logger.info("Heuristic mode enabled: using 100%% rule-based extraction.")

    logger.info("Collecting documents from %s...", raw_dir)
    all_docs = list(iter_documents_from_dir(raw_dir))
    if args.limit > 0:
        all_docs = all_docs[:args.limit]

    total_docs = len(all_docs)
    logger.info("Found %d total documents to process (Parallel Workers: %d).", total_docs, args.workers)

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
        new_count = 0
        skipped_count = 0
        total_entities_extracted = 0
        total_facts_extracted = 0

        pbar = tqdm(total=total_docs, desc="Ingesting Documents", unit="doc")

        if args.workers > 1:
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = {
                    executor.submit(_process_doc, doc, loader, existing_doc_ids, args.force, args.heuristic): doc
                    for doc in all_docs
                }
                for future in as_completed(futures):
                    try:
                        doc_id, skipped, n_ent, n_fact, src = future.result()
                        if skipped:
                            skipped_count += 1
                        else:
                            new_count += 1
                            total_entities_extracted += n_ent
                            total_facts_extracted += n_fact
                            existing_doc_ids.add(doc_id)
                        pbar.update(1)
                        pbar.set_postfix(new_docs=new_count, skipped=skipped_count, facts=total_facts_extracted)
                    except Exception as exc:
                        logger.warning("Error processing document: %s", exc)
                        pbar.update(1)
        else:
            for doc in all_docs:
                doc_id, skipped, n_ent, n_fact, src = _process_doc(doc, loader, existing_doc_ids, args.force, args.heuristic)
                if skipped:
                    skipped_count += 1
                else:
                    new_count += 1
                    total_entities_extracted += n_ent
                    total_facts_extracted += n_fact
                    existing_doc_ids.add(doc_id)
                pbar.update(1)
                pbar.set_postfix(new_docs=new_count, skipped=skipped_count, facts=total_facts_extracted)

        pbar.close()

        logger.info("\n🎉 Ingestion complete!")
        logger.info("  New Documents Ingested: %d", new_count)
        logger.info("  Skipped (Already In DB): %d", skipped_count)
        logger.info("  Total Extracted Entities: %d", total_entities_extracted)
        logger.info("  Total Extracted Facts:    %d", total_facts_extracted)


if __name__ == "__main__":
    main()
