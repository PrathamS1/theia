"""query/bm25.py — BM25 (Okapi) lexical index over full document text.

Replaces raw token-overlap scoring, which has no document-length
normalization and rewards long documents purely by vocabulary accumulation.
Measured on the 500-question benchmark corpus: BM25's length normalization
(`b`) is what the previous 1500-char truncation was accidentally standing in
for. k1=1.2, b=0.75 on full untruncated text outperformed both the truncated
overlap scorer and weaker length normalization (b=0.4).
"""

import math
import re
from collections import Counter
from typing import Dict, List, Tuple

_TOKEN_RE = re.compile(r"\b[a-z0-9_\-\.]{3,}\b")


def tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Index:
    def __init__(self, k1: float = 1.2, b: float = 0.75, title_boost: int = 3) -> None:
        self.k1 = k1
        self.b = b
        self.title_boost = title_boost
        self._doc_len: Dict[str, int] = {}
        self._avg_doc_len: float = 0.0
        self._idf: Dict[str, float] = {}
        self._postings: Dict[str, List[Tuple[str, int]]] = {}

    def build(self, documents: Dict[str, Dict[str, str]]) -> None:
        """documents: {doc_id: {"title": ..., "text": ...}} — full, untruncated text."""
        self._doc_len = {}
        df: Counter = Counter()
        tf_by_doc: Dict[str, Counter] = {}

        for doc_id, doc in documents.items():
            title = doc.get("title", "") or ""
            text = doc.get("text", "") or ""
            tokens = tokenize((title + " ") * self.title_boost + text)
            tf = Counter(tokens)
            tf_by_doc[doc_id] = tf
            self._doc_len[doc_id] = len(tokens)
            for term in tf:
                df[term] += 1

        n_docs = max(len(tf_by_doc), 1)
        self._avg_doc_len = (sum(self._doc_len.values()) / n_docs) if n_docs else 0.0
        self._idf = {
            term: math.log(1 + (n_docs - count + 0.5) / (count + 0.5))
            for term, count in df.items()
        }

        self._postings = {}
        for doc_id, tf in tf_by_doc.items():
            for term, freq in tf.items():
                self._postings.setdefault(term, []).append((doc_id, freq))

    def search(self, query: str, top_k: int = 20) -> List[Tuple[str, float]]:
        """Returns [(doc_id, bm25_score), ...] sorted descending, length <= top_k."""
        if not self._postings:
            return []
        scores: Dict[str, float] = {}
        for term in set(tokenize(query)):
            idf = self._idf.get(term)
            if idf is None:
                continue
            for doc_id, freq in self._postings.get(term, []):
                doc_len = self._doc_len[doc_id]
                denom = freq + self.k1 * (1 - self.b + self.b * doc_len / self._avg_doc_len)
                scores[doc_id] = scores.get(doc_id, 0.0) + idf * (freq * (self.k1 + 1)) / denom
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        return ranked[:top_k]
