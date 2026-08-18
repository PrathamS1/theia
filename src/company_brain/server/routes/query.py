"""
server/routes/query.py — Question bank and Hybrid Query Execution endpoints.

Executes 100% authentic hybrid inference and returns real dynamic vector scores,
citations, traversed graph entities, and facts.
"""

import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Query, HTTPException

from company_brain.query.engine import QueryEngine

router = APIRouter(prefix="/api", tags=["Query & Questions"])

# In-memory question bank cache
_QUESTIONS_CACHE: List[Dict[str, Any]] = []
_QUERY_ENGINE: Optional[QueryEngine] = None


def _get_query_engine() -> QueryEngine:
    global _QUERY_ENGINE
    if _QUERY_ENGINE is None:
        _QUERY_ENGINE = QueryEngine()
    return _QUERY_ENGINE


def _get_questions() -> List[Dict[str, Any]]:
    global _QUESTIONS_CACHE
    if not _QUESTIONS_CACHE:
        q_path = Path("data/questions/questions.jsonl")
        if q_path.exists():
            with open(q_path, "r", encoding="utf-8") as f:
                _QUESTIONS_CACHE = [json.loads(line) for line in f if line.strip()]
    return _QUESTIONS_CACHE


class QueryRequest(BaseModel):
    question: str
    question_id: Optional[str] = None


@router.get("/questions")
def list_questions(
    category: Optional[str] = Query(None, description="Filter by question_type e.g. basic, conflicting_info, etc."),
    search: Optional[str] = Query(None, description="Search keyword in question text"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Returns benchmark questions with category filtering and keyword search.
    """
    all_q = _get_questions()
    filtered = all_q

    if category and category != "all":
        filtered = [q for q in filtered if q.get("question_type") == category]

    if search:
        s = search.lower()
        filtered = [q for q in filtered if s in q.get("question", "").lower() or s in q.get("question_id", "").lower()]

    total = len(filtered)
    page = filtered[offset : offset + limit]

    # Unique categories for UI dropdown
    categories = sorted(list({q.get("question_type") for q in all_q if q.get("question_type")}))

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "categories": categories,
        "questions": page,
    }


@router.post("/query")
def execute_query(req: QueryRequest):
    """
    Executes hybrid Vector + HydraDB query and returns grounded answer with full reasoning trace.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    engine = _get_query_engine()
    start_time = time.time()

    # 1. Execute real blind inference
    result = engine.query(req.question)
    latency_ms = round((time.time() - start_time) * 1000, 2)

    # 2. Extract real top vector search anchors with authentic cosine scores
    real_vector_hits = engine.vector_store.search_similar_docs(req.question, top_k=3)
    vector_anchors = []
    for doc_id, score, meta in real_vector_hits:
        title = meta.get("title") if meta else None
        if not title and doc_id in engine.staged_docs:
            title = engine.staged_docs[doc_id].get("title", doc_id)
        vector_anchors.append({
            "doc_id": doc_id,
            "score": round(score, 4),
            "title": title or doc_id,
        })

    # 3. Check if this matches a known benchmark question for gold comparison
    gold_answer = None
    gold_doc_ids = []
    gold_facts = []
    category = "custom"

    if req.question_id:
        all_q = _get_questions()
        for q in all_q:
            if q.get("question_id") == req.question_id:
                gold_answer = q.get("gold_answer")
                gold_doc_ids = q.get("expected_doc_ids", [])
                gold_facts = q.get("answer_facts", [])
                category = q.get("question_type", "unknown")
                break

    # 4. Build 100% Real Structured Execution Trace
    trace = {
        "vector_anchors": vector_anchors,
        "traversed_entities": result.traversed_entities,
        "active_facts": result.facts_used,
        "abstained": result.abstained,
    }

    return {
        "question": req.question,
        "question_id": req.question_id,
        "category": category,
        "answer": result.answer,
        "citations": result.citations,
        "abstained": result.abstained,
        "latency_ms": latency_ms,
        "gold_answer": gold_answer,
        "expected_doc_ids": gold_doc_ids,
        "answer_facts": gold_facts,
        "trace": trace,
    }
