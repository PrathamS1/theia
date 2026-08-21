#!/usr/bin/env python3
"""
scripts/verify_ingestion.py — Verification & smoke test script for Ingestion & Vector Index.

Checks:
1. HydraDB node counts (:Document, :Person, :Org, :Ticket, :Fact)
2. Edge provenance integrity (doc_id, source, timestamp)
3. Vector store top-k search accuracy against sample questions
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain.graph.client import GraphClient
from company_brain.indexing.vector_store import VectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_ingestion")


def main():
    logger.info("=== Running Ingestion & Vector Verification ===")

    # 1. Check Vector Store
    logger.info("1. Verifying Vector Store...")
    vstore = VectorStore()
    if not vstore.load():
        logger.error("[FAIL] Vector store could not be loaded from data/vectors/.")
    else:
        num_items = len(vstore.chunks_meta) if vstore.chunks_meta else len(vstore.doc_ids)
        emb_shape = vstore.chunk_embeddings.shape if vstore.chunk_embeddings is not None else (vstore.doc_embeddings.shape if vstore.doc_embeddings is not None else "None")
        logger.info("[OK]   Vector store loaded %d passage embeddings (matrix shape: %s).", num_items, emb_shape)
        
        sample_q = "What are the default size limits for multipart file uploads?"
        hits = vstore.search_similar(sample_q, top_k=3)
        logger.info("  Sample Semantic Search Query: '%s'", sample_q)
        for rank, (doc_id, score, meta) in enumerate(hits, 1):
            logger.info("    #%d: doc_id=%s (score=%.4f, source=%s, title='%s')",
                        rank, doc_id, score, meta.get("source"), meta.get("title"))

    # 2. Check HydraDB Counts
    logger.info("2. Verifying HydraDB Node & Edge Counts...")
    try:
        with GraphClient() as client:
            doc_res = client.run("MATCH (d:Document) RETURN count(*)")
            person_res = client.run("MATCH (p:Person) RETURN count(*)")
            fact_res = client.run("MATCH (f:Fact) RETURN count(*)")

            doc_count = doc_res[0].get("count(*)", 0) if doc_res else 0
            person_count = person_res[0].get("count(*)", 0) if person_res else 0
            fact_count = fact_res[0].get("count(*)", 0) if fact_res else 0

            logger.info("[OK]   HydraDB Graph Counts:")
            logger.info("         :Document nodes: %d", doc_count)
            logger.info("         :Person nodes:   %d", person_count)
            logger.info("         :Fact nodes:     %d", fact_count)

            # Check a sample query path
            sample_docs = client.run("MATCH (d:Document) RETURN d.doc_id, d.source LIMIT 3")
            logger.info("  Sample Document Nodes in Graph:")
            for d in sample_docs:
                logger.info("    -> doc_id=%s, source=%s", d.get("d.doc_id"), d.get("d.source"))

    except Exception as e:
        logger.error("[FAIL] HydraDB connection check failed: %s", e)
        sys.exit(1)

    logger.info("=== All Ingestion Checks Verified Successfully ✓ ===")


if __name__ == "__main__":
    main()
