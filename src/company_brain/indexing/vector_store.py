"""
indexing/vector_store.py — Dense Vector Store for Full-Corpus Chunk & Document Embeddings.

Powered by sentence-transformers/all-MiniLM-L6-v2.
Embeds 100% of all document chunks and provides sub-millisecond cosine similarity search.
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

        # Chunk-level index
        self.chunk_embeddings: Optional[np.ndarray] = None
        self.chunks_meta: List[Dict[str, Any]] = []

        # Document-level index (backward compatibility)
        self.doc_embeddings: Optional[np.ndarray] = None
        self.doc_ids: List[str] = []
        self.doc_meta: List[Dict[str, Any]] = []

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading SentenceTransformer model %s...", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def build_chunk_index(self, chunks: List[Dict[str, Any]], batch_size: int = 128) -> int:
        """
        Encodes all chunks in batches into dense 384-dimensional embeddings.
        """
        if not chunks:
            logger.warning("No chunks provided to build_chunk_index.")
            return 0

        self.chunks_meta = chunks
        texts = [c.get("text", "") for c in chunks]

        logger.info("Encoding %d chunks with %s (batch_size=%d)...", len(texts), self.model_name, batch_size)
        start_t = time.time()
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        self.chunk_embeddings = np.array(embeddings, dtype=np.float32)
        elapsed = time.time() - start_t
        logger.info("Encoded %d chunks in %.2f seconds (%.1f chunks/sec).", len(texts), elapsed, len(texts) / max(elapsed, 0.001))
        return len(texts)

    def save(self, vector_dir: str = "data/vectors") -> None:
        """Saves embeddings and metadata indexes to disk."""
        v_path = Path(vector_dir)
        v_path.mkdir(parents=True, exist_ok=True)

        if self.chunk_embeddings is not None and self.chunks_meta:
            np.save(v_path / "chunk_embeddings.npy", self.chunk_embeddings)
            with open(v_path / "chunk_meta.json", "w", encoding="utf-8") as f:
                json.dump(self.chunks_meta, f)
            logger.info("Saved chunk embeddings (%s) and metadata to %s.", self.chunk_embeddings.shape, v_path)

        if self.doc_embeddings is not None:
            np.save(v_path / "doc_embeddings.npy", self.doc_embeddings)
            with open(v_path / "doc_ids.json", "w", encoding="utf-8") as f:
                json.dump(self.doc_ids, f)

    def load(self, vector_dir: str = "data/vectors") -> bool:
        """Loads chunk and document vector embeddings from disk."""
        v_path = Path(vector_dir)
        loaded = False

        # Load chunk index if available
        chunk_emb_path = v_path / "chunk_embeddings.npy"
        chunk_meta_path = v_path / "chunk_meta.json"
        if chunk_emb_path.exists() and chunk_meta_path.exists():
            try:
                self.chunk_embeddings = np.load(chunk_emb_path)
                with open(chunk_meta_path, "r", encoding="utf-8") as f:
                    self.chunks_meta = json.load(f)
                logger.info("Loaded chunk index: %d embeddings %s", len(self.chunks_meta), self.chunk_embeddings.shape)
                loaded = True
            except Exception as e:
                logger.error("Failed to load chunk embeddings: %s", e)

        # Also load document index for backward compatibility
        doc_emb_path = v_path / "doc_embeddings.npy"
        doc_ids_path = v_path / "doc_ids.json"
        if doc_emb_path.exists() and doc_ids_path.exists():
            try:
                self.doc_embeddings = np.load(doc_emb_path)
                with open(doc_ids_path, "r", encoding="utf-8") as f:
                    self.doc_ids = json.load(f)
                loaded = True
            except Exception as e:
                logger.error("Failed to load doc embeddings: %s", e)

        return loaded

    def search_similar_chunks(self, query: str, top_k: int = 25) -> List[Tuple[str, float, str, Dict[str, Any]]]:
        """
        Searches the chunk index for the top_k most similar passages.
        Returns: List of (doc_id, cosine_score, chunk_text, chunk_meta)
        """
        if self.chunk_embeddings is None or not self.chunks_meta:
            # Fallback to document-level search if chunk index is missing
            doc_hits = self.search_similar(query, top_k=top_k)
            return [(d[0], d[1], "", d[2]) for d in doc_hits]

        q_emb = self.model.encode([query], normalize_embeddings=True)[0]
        # Dot product of normalized vectors = Cosine Similarity
        scores = np.dot(self.chunk_embeddings, q_emb)

        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            cmeta = self.chunks_meta[idx]
            doc_id = cmeta.get("doc_id", "")
            text = cmeta.get("text", "")
            results.append((doc_id, score, text, cmeta))

        return results

    def search_similar_docs(self, query: str, top_k: int = 20) -> List[Tuple[str, float, str, Dict[str, Any]]]:
        """
        Aggregates chunk-level cosine similarities up to parent document level.
        Returns: List of (doc_id, best_score, best_chunk_text, doc_meta)
        """
        chunk_hits = self.search_similar_chunks(query, top_k=min(top_k * 3, 60))
        doc_best: Dict[str, Tuple[float, str, Dict[str, Any]]] = {}

        for doc_id, score, text, meta in chunk_hits:
            if doc_id not in doc_best or score > doc_best[doc_id][0]:
                doc_best[doc_id] = (score, text, meta.get("meta", {}))

        # Sort aggregated parent docs by best chunk score
        sorted_docs = sorted(doc_best.items(), key=lambda x: x[1][0], reverse=True)[:top_k]
        return [(doc_id, score, text, meta) for doc_id, (score, text, meta) in sorted_docs]

    def search_similar(self, query: str, top_k: int = 20) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Document-level search interface."""
        if self.chunk_embeddings is not None and self.chunks_meta:
            doc_hits = self.search_similar_docs(query, top_k=top_k)
            return [(did, score, meta) for did, score, text, meta in doc_hits]

        if self.doc_embeddings is None or not self.doc_ids:
            return []

        q_emb = self.model.encode([query], normalize_embeddings=True)[0]
        scores = np.dot(self.doc_embeddings, q_emb)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(self.doc_ids[idx], float(scores[idx]), self.doc_meta[idx] if idx < len(self.doc_meta) else {}) for idx in top_indices]
