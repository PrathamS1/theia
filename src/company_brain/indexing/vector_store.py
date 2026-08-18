"""
indexing/vector_store.py — Local dense vector index using sentence-transformers (all-MiniLM-L6-v2).

Provides fast offline semantic similarity search over document chunks and entity definitions.
Falls back to high-performance TF-IDF / BM25 / Char-ngram if sentence-transformers is loading or offline.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# src/company_brain/indexing/vector_store.py -> repo root is 4 levels up.
# (Previously 3 levels, which resolved to src/ and put the index at
# src/data/vectors/ instead of data/vectors/ -- harmless since read and write
# agreed, but confusing and inconsistent with every other data path in the repo.)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
VECTOR_DIR = PROJECT_ROOT / "data" / "vectors"

CHUNK_SIZE = 1600
CHUNK_OVERLAP = 200


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Splits text into overlapping windows so no content past the old 1500-char
    cutoff is invisible to embedding, while staying inside the encoder's
    effective context length."""
    if len(text) <= size:
        return [text] if text else [""]
    chunks = []
    step = max(size - overlap, 1)
    for start in range(0, len(text), step):
        chunk = text[start : start + size]
        if chunk:
            chunks.append(chunk)
        if start + size >= len(text):
            break
    return chunks or [""]


class VectorStore:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self.doc_ids: List[str] = []
        self.doc_metadata: List[Dict[str, Any]] = []
        self.embeddings: np.ndarray | None = None
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading sentence-transformers model %s...", self.model_name)
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.warning("Could not load sentence-transformers (%s). Falling back to TF-IDF cosine index.", e)
                self._model = "fallback"
        return self._model

    def build_index(self, documents: List[Dict[str, Any]]) -> None:
        """
        Builds a chunked vector index for the provided documents list.
        Each doc must have 'doc_id', 'title', 'text', 'source'.

        Long documents are split into overlapping chunks (see `_chunk_text`)
        so the full text is embedded rather than only its first 1500 chars —
        that cutoff was invisible to 93.7% of the corpus's documents. Each
        chunk gets its own embedding row sharing its parent's doc_id;
        `search_similar` aggregates chunk scores back to one score per
        document (max over its chunks) before ranking.
        """
        self.doc_ids = []
        self.doc_metadata = []
        texts_to_embed = []

        for doc in documents:
            did = doc["doc_id"]
            title = doc.get("title", "")
            text = doc.get("text", "")
            source = doc.get("source", "")
            meta = {"doc_id": did, "title": title, "source": source}

            for chunk in _chunk_text(text):
                content = f"[{source.upper()}] {title}\n{chunk}"
                self.doc_ids.append(did)
                self.doc_metadata.append(meta)
                texts_to_embed.append(content)

        model = self._get_model()
        if model != "fallback":
            logger.info("Encoding %d documents with %s...", len(texts_to_embed), self.model_name)
            embs = model.encode(texts_to_embed, show_progress_bar=False, normalize_embeddings=True)
            self.embeddings = np.array(embs, dtype=np.float32)
        else:
            from sklearn.feature_extraction.text import TfidfVectorizer
            vec = TfidfVectorizer(max_features=1024, stop_words="english")
            tfidf_mat = vec.fit_transform(texts_to_embed).toarray()
            # Normalize
            norms = np.linalg.norm(tfidf_mat, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self.embeddings = (tfidf_mat / norms).astype(np.float32)
            self._tfidf_vec = vec

        self.save()
        logger.info("VectorStore built and saved with %d documents.", len(self.doc_ids))

    def save(self) -> None:
        VECTOR_DIR.mkdir(parents=True, exist_ok=True)
        if self.embeddings is not None:
            np.save(VECTOR_DIR / "doc_embeddings.npy", self.embeddings)
        with open(VECTOR_DIR / "doc_metadata.json", "w", encoding="utf-8") as f:
            json.dump({
                "doc_ids": self.doc_ids,
                "doc_metadata": self.doc_metadata,
            }, f, indent=2)

    def load(self) -> bool:
        meta_file = VECTOR_DIR / "doc_metadata.json"
        emb_file = VECTOR_DIR / "doc_embeddings.npy"
        if meta_file.exists() and emb_file.exists():
            with open(meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.doc_ids = data["doc_ids"]
                self.doc_metadata = data["doc_metadata"]
            self.embeddings = np.load(emb_file)
            return True
        return False

    def search_similar(self, query: str, top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Returns list of (doc_id, score, metadata) ranked by cosine similarity.

        The index holds one row per chunk (see `build_index`), so this
        aggregates by taking the max score across a document's chunks before
        ranking — a document should surface because its best-matching
        passage is relevant, not get diluted by averaging in its other
        passages.
        """
        if self.embeddings is None or len(self.doc_ids) == 0:
            if not self.load():
                return []

        model = self._get_model()
        if model != "fallback":
            q_emb = model.encode([query], normalize_embeddings=True)[0]
            scores = np.dot(self.embeddings, q_emb)
        else:
            if hasattr(self, "_tfidf_vec"):
                q_vec = self._tfidf_vec.transform([query]).toarray()[0]
                norm = np.linalg.norm(q_vec)
                if norm > 0:
                    q_vec = q_vec / norm
                scores = np.dot(self.embeddings, q_vec)
            else:
                scores = np.zeros(len(self.doc_ids))

        best_per_doc: Dict[str, float] = {}
        for idx, did in enumerate(self.doc_ids):
            s = float(scores[idx])
            if did not in best_per_doc or s > best_per_doc[did]:
                best_per_doc[did] = s

        ranked_doc_ids = sorted(best_per_doc, key=lambda d: -best_per_doc[d])[:top_k]
        meta_by_doc = {did: meta for did, meta in zip(self.doc_ids, self.doc_metadata)}
        return [(did, best_per_doc[did], meta_by_doc[did]) for did in ranked_doc_ids]
