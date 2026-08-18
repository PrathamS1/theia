#!/usr/bin/env python3
"""
scripts/run_ingest.py — Production ingestion & indexing pipeline for Company Brain.

Loads the ~812 staged gold documents, builds the local all-MiniLM vector store,
and ingests Document nodes, Entities, and Facts into HydraDB.
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
    try:
        with GraphClient() as client:
            if not client.ping():
                logger.error("HydraDB is not reachable at %s. Please start HydraDB first using scripts/start_hydradb.sh", config.BOLT_URI)
                sys.exit(1)

            loader = GraphLoader(client)
            start_time = time.time()

            total_entities = 0
            total_facts = 0

            logger.info("Ingesting documents and extracting ontology into HydraDB...")
            for idx, doc in enumerate(doc_list):
                doc_id = doc["doc_id"]
                source = doc["source"]
                created_at = doc.get("created_at", "2026-01-01T00:00:00Z")
                title = doc.get("title", doc_id)
                text = doc.get("text", "")

                # Hybrid extraction (Heuristics + Semantic triples)
                extraction = extract_entities_and_facts(
                    doc_text=text,
                    doc_id=doc_id,
                    source=source,
                    title=title,
                    created_at=created_at,
                )

                total_entities += len(extraction.entities)
                total_facts += len(extraction.facts)

                # Ingest into HydraDB
                loader.load_document(
                    doc_id=doc_id,
                    source=source,
                    created_at=created_at,
                    text_snippet=text[:500],
                    extraction=extraction,
                    title=title,
                )

                if (idx + 1) % 100 == 0 or (idx + 1) == total_docs:
                    elapsed = time.time() - start_time
                    logger.info("  [%d / %d docs] Loaded (%d entities, %d facts) in %.1fs",
                                idx + 1, total_docs, total_entities, total_facts, elapsed)

            logger.info("=== Ingestion Finished Successfully ===")
            logger.info("  Total Documents Ingested: %d", total_docs)
            logger.info("  Total Entities Extracted: %d", total_entities)
            logger.info("  Total Facts Extracted:    %d", total_facts)
            logger.info("  Time Elapsed:             %.2fs", time.time() - start_time)

    except Exception as e:
        logger.error("HydraDB ingestion encountered an error: %s", e)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
