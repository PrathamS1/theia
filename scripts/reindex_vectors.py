#!/usr/bin/env python3
"""
scripts/reindex_vectors.py — Full-Corpus Chunking & Re-Embedding Runner.

Processes all 812 gold documents:
1. Splits full text into sliding-window passages (~1000 chars with 200 char overlap).
2. Encodes 100% of all chunks into 384-dimensional dense vectors with all-MiniLM-L6-v2.
3. Persists embeddings to data/vectors/chunk_embeddings.npy and chunk_meta.json.
"""

import sys
import json
import logging
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain.indexing.chunker import DocumentChunker
from company_brain.indexing.vector_store import VectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reindex_vectors")


def main():
    staged_path = Path("data/staged_gold_docs.json")
    if not staged_path.exists():
        logger.error("staged_gold_docs.json not found at %s", staged_path)
        sys.exit(1)

    with open(staged_path, "r", encoding="utf-8") as f:
        docs = json.load(f)

    logger.info("Loaded %d gold documents from %s", len(docs), staged_path)

    # 1. Chunk all documents
    chunker = DocumentChunker(chunk_size=1000, chunk_overlap=200)
    start_t = time.time()
    all_chunks = chunker.chunk_all_documents(docs)
    logger.info(
        "Split %d documents into %d chunks in %.2f seconds (Avg %.1f chunks/doc).",
        len(docs),
        len(all_chunks),
        time.time() - start_t,
        len(all_chunks) / len(docs),
    )

    # 2. Build dense embeddings
    vstore = VectorStore()
    vstore.build_chunk_index(all_chunks, batch_size=128)

    # 3. Save to disk
    vstore.save()
    logger.info("✅ Full-Corpus Chunk Indexing Complete!")


if __name__ == "__main__":
    main()
