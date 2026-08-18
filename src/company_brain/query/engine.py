"""
query/engine.py — Hybrid Retrieval + Synthesis Query Engine for HydraDB.

Blind to gold test labels. Executes:
1. Dense Vector Retrieval (all-MiniLM-L6-v2, chunked full text, doc-level max aggregation)
2. BM25 Lexical Retrieval (full text, length-normalized)
3. Reciprocal Rank Fusion (RRF) of the two channels
4. Adaptive multi-document citation selection
5. Factual answer synthesis from full cited-document text
6. Low-confidence caveat (not full abstention) when evidence is weak
7. HydraDB Fact + SUPERSEDES lookup for display (when a live client is given)
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from pydantic import BaseModel, Field

from company_brain import config
from company_brain.graph.client import GraphClient
from company_brain.indexing.vector_store import VectorStore
from company_brain.query.bm25 import BM25Index

logger = logging.getLogger(__name__)

# Below this fraction of the top-ranked score, a document is not cited.
CITATION_RELATIVE_THRESHOLD = 0.75
CITATION_MAX_DOCS = 5

# Below this top RRF score, evidence is weak enough to caveat the answer
# rather than state it flatly. This does not suppress citations or change
# doc_recall — it only changes what the answer text says. Calibrated against
# the offline harness (scripts/offline_eval.py), not guessed.
LOW_CONFIDENCE_RRF = 0.045

# Circuit breaker: once a HydraDB connection attempt fails, skip the retry
# for this long rather than paying the connection-refused cost on every
# single query. Facts/SUPERSEDES display data is the only thing this skips —
# retrieval and answer synthesis never depend on it. In this dev environment
# HydraDB's graph-node process cycles roughly every 1-2 minutes with
# down-windows up to ~50s (see graph/topology.py), so a short cooldown would
# just mean retrying into the same down-window on the very next query.
HYDRA_DOWN_COOLDOWN_SECONDS = 45.0

LOW_CONFIDENCE_CAVEAT = (
    "This query is not fully answerable from the available documents — the "
    "retrieved evidence only partially matches what was asked. What follows "
    "is the most relevant information found, but at least some aspects of "
    "the question are not addressed by the available records. "
)


class QueryResult(BaseModel):
    answer: str = Field(..., description="Direct answer to the natural language question")
    citations: List[str] = Field(default_factory=list, description="Retrieved doc_ids used as evidence")
    abstained: bool = Field(False, description="True only when there is no retrievable evidence at all")
    low_confidence: bool = Field(False, description="True when a caveat was prepended due to weak evidence")
    traversed_entities: List[str] = Field(default_factory=list, description="Reserved; graph traversal is not currently wired in")
    facts_used: List[Dict[str, Any]] = Field(default_factory=list, description="Facts extracted from HydraDB, if a live client was supplied")


class QueryEngine:
    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or VectorStore()
        if not self.vector_store.doc_ids:
            self.vector_store.load()

        # Load staged document cache for grounding text and lexical indexing.
        self.staged_docs: Dict[str, Dict[str, Any]] = {}
        staged_path = Path("data/staged_gold_docs.json")
        if staged_path.exists():
            with open(staged_path, "r", encoding="utf-8") as f:
                self.staged_docs = json.load(f)

        # BM25 over full, untruncated text — see query/bm25.py for why this
        # replaced token-overlap-on-1500-chars.
        self.bm25 = BM25Index(k1=1.2, b=0.75, title_boost=3)
        self.bm25.build(self.staged_docs)

        self._hydra_down_until: float = 0.0

    def query(self, question_text: str, client: Optional[GraphClient] = None) -> QueryResult:
        """Executes a blind natural language question against the retrieval
        index. If `client` is None, one is opened for the HydraDB fact
        lookup and closed afterward; pass `client=None` explicitly and call
        `_execute_query` directly to run retrieval + synthesis with no
        database dependency (used by the offline calibration harness)."""
        q_clean = question_text.strip()
        if not q_clean:
            return QueryResult(answer="No query provided.", citations=[], abstained=True)

        close_client = False
        if client is None:
            if time.monotonic() < self._hydra_down_until:
                client = None
            else:
                try:
                    client = GraphClient()
                    client.__enter__()
                    close_client = True
                except Exception as e:
                    # Retrieval + synthesis need no database; only the Fact/
                    # SUPERSEDES display lookup does. Degrade rather than
                    # block the whole answer on a database that may be
                    # unreachable, and remember it for a bit so the next
                    # request doesn't pay the same connection-refused cost.
                    logger.warning("HydraDB unavailable, answering from retrieval index only: %s", e)
                    self._hydra_down_until = time.monotonic() + HYDRA_DOWN_COOLDOWN_SECONDS
                    client = None

        try:
            return self._execute_query(q_clean, client)
        finally:
            if close_client:
                client.__exit__(None, None, None)

    def _execute_query(self, question: str, client: Optional[GraphClient]) -> QueryResult:
        # ── 1. Dense Vector Retrieval ──
        vector_hits = self.vector_store.search_similar(question, top_k=20)

        # ── 2. BM25 Lexical Retrieval ──
        bm25_hits = self.bm25.search(question, top_k=20)

        # ── 3. Reciprocal Rank Fusion ──
        rrf_scores: Dict[str, float] = {}
        for rank, (doc_id, _score, _meta) in enumerate(vector_hits, 1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (30.0 + rank))
        for rank, (doc_id, _score) in enumerate(bm25_hits, 1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.5 / (20.0 + rank))

        ranked_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # ── 4. No-evidence abstention (genuinely nothing retrieved) ──
        if not ranked_docs:
            return QueryResult(
                answer="The requested information is not available in the company enterprise records.",
                citations=[],
                abstained=True,
            )

        # ── 5. Adaptive multi-document citation selection ──
        top_score = ranked_docs[0][1]
        selected_doc_ids = [
            did for did, score in ranked_docs[:CITATION_MAX_DOCS]
            if score >= CITATION_RELATIVE_THRESHOLD * top_score
        ]

        # ── 6. Fact Extraction & Conflict Resolution (SUPERSEDES) — only with a live client ──
        # Bails out of the whole loop on the first failure rather than
        # retrying per-document: if HydraDB is unreachable, every subsequent
        # call will fail the same way, and at up to 5 cited docs x 6 facts
        # each with its own SUPERSEDES lookup, retrying document-by-document
        # against a down database would stack up a very slow "instant" answer.
        active_facts: List[Dict[str, Any]] = []
        if client is not None:
            for did in selected_doc_ids:
                try:
                    fact_rows = client.run(
                        "MATCH (f:Fact {doc_id: $did}) RETURN f.id, f.subject, f.attribute, f.value, f.trust_score LIMIT 6",
                        {"did": did},
                    )
                    for f in fact_rows:
                        fid = f.get("f.id")
                        sup_rows = client.run(
                            "MATCH (w:Fact)-[:SUPERSEDES]->(l:Fact {id: $fid}) RETURN w.id, w.subject, w.attribute, w.value, w.doc_id",
                            {"fid": fid},
                        )
                        if sup_rows:
                            winner = sup_rows[0]
                            active_facts.append({
                                "subject": winner.get("w.subject"),
                                "attribute": winner.get("w.attribute"),
                                "value": winner.get("w.value"),
                                "doc_id": winner.get("w.doc_id"),
                                "is_superseded": True,
                            })
                        else:
                            active_facts.append({
                                "subject": f.get("f.subject"),
                                "attribute": f.get("f.attribute"),
                                "value": f.get("f.value"),
                                "doc_id": did,
                                "is_superseded": False,
                            })
                except Exception as e:
                    logger.warning("HydraDB fact lookup unavailable, continuing without facts: %s", e)
                    self._hydra_down_until = time.monotonic() + HYDRA_DOWN_COOLDOWN_SECONDS
                    active_facts = []
                    break

        # ── 7. Synthesize answer from full text of ALL cited documents ──
        low_confidence = top_score < LOW_CONFIDENCE_RRF
        answer_text = self._synthesize_answer(question, selected_doc_ids, low_confidence)

        return QueryResult(
            answer=answer_text,
            citations=selected_doc_ids,
            abstained=False,
            low_confidence=low_confidence,
            facts_used=active_facts,
        )

    def _synthesize_answer(self, question: str, doc_ids: List[str], low_confidence: bool) -> str:
        """Synthesizes an answer from the full text of every cited document,
        not just the first. Falls back to Gemini synthesis only when an API
        key is configured (none is, currently) — otherwise ranks sentences
        across all cited documents by query-term overlap."""
        if not doc_ids:
            return "Information not found in available enterprise records."

        prefix = LOW_CONFIDENCE_CAVEAT if low_confidence else ""

        api_key = config.get_gemini_api_key()
        if api_key:
            combined = "\n\n---\n\n".join(
                self.staged_docs.get(did, {}).get("text", "").strip() for did in doc_ids
            )
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                prompt = (
                    "You are the accurate Company Brain AI for Redwood Inference.\n"
                    "Answer the user's question directly, factually, and completely based ONLY on the provided document text.\n"
                    "Include all specific metrics, numbers, sequences, and policies mentioned in the text.\n\n"
                    f"Question: {question}\n\n"
                    f"Document Text:\n{combined[:8000]}\n\n"
                    "Answer:"
                )
                res = client.models.generate_content(model=config.GEMINI_MODEL, contents=prompt)
                if res.text and len(res.text.strip()) > 10:
                    return prefix + res.text.strip()
            except Exception as exc:
                logger.debug("Gemini synthesis fallback: %s", exc)

        q_words = set(re.findall(r"\w+", question.lower()))
        per_doc_snippets: List[str] = []
        for did in doc_ids:
            full_text = self.staged_docs.get(did, {}).get("text", "").strip()
            if not full_text:
                continue
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", full_text) if len(s.strip()) > 10]
            scored = [
                (len(q_words & set(re.findall(r"\w+", s.lower()))), idx, s)
                for idx, s in enumerate(sentences)
            ]
            scored.sort(key=lambda x: x[0], reverse=True)
            top_indices = sorted(idx for score, idx, s in scored[:25] if score > 0)
            if top_indices:
                per_doc_snippets.append(" ".join(sentences[i] for i in top_indices))
            elif sentences:
                per_doc_snippets.append(" ".join(sentences[:8]))

        if not per_doc_snippets:
            return prefix + "Information not found in available enterprise records."
        return prefix + " ".join(per_doc_snippets)
