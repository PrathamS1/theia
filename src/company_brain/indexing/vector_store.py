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

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VECTOR_DIR = PROJECT_ROOT / "data" / "vectors"


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
        Builds vector index for the provided documents list.
        Each doc must have 'doc_id', 'title', 'text', 'source'.
        """
        self.doc_ids = []
        self.doc_metadata = []
        texts_to_embed = []

        for doc in documents:
            did = doc["doc_id"]
            title = doc.get("title", "")
            text = doc.get("text", "")
            source = doc.get("source", "")
            
            # Combine title, source and text for rich embedding
            content = f"[{source.upper()}] {title}\n{text[:1500]}"
            self.doc_ids.append(did)
            self.doc_metadata.append({
                "doc_id": did,
                "title": title,
                "source": source,
            })
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

        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            results.append((self.doc_ids[idx], float(scores[idx]), self.doc_metadata[idx]))
        return results
