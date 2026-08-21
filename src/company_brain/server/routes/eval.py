"""
server/routes/eval.py — Benchmark Evaluation runner and results endpoints.
"""

import json
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, BackgroundTasks

from company_brain.query.engine import QueryEngine
from company_brain.eval.metrics import evaluate_prediction, aggregate_benchmark_results

router = APIRouter(prefix="/api/eval", tags=["Evaluation"])

# Evaluation runner state
_EVAL_STATE: Dict[str, Any] = {
    "status": "idle",
    "current": 0,
    "total": 0,
    "category": "all",
    "running_score": 0.0,
    "start_time": None,
    "last_result": None,
}


class EvalRunRequest(BaseModel):
    category: Optional[str] = "all"
    limit: Optional[int] = None


def _background_eval_task(category: str, limit: Optional[int]):
    global _EVAL_STATE
    _EVAL_STATE["status"] = "running"
    _EVAL_STATE["category"] = category
    _EVAL_STATE["start_time"] = time.time()

    q_path = Path("data/questions/questions.jsonl")
    if not q_path.exists():
        _EVAL_STATE["status"] = "error"
        return

    with open(q_path, "r", encoding="utf-8") as f:
        questions = [json.loads(line) for line in f if line.strip()]

    if category and category != "all":
        questions = [q for q in questions if q.get("question_type") == category]

    if limit:
        questions = questions[:limit]

    _EVAL_STATE["total"] = len(questions)
    _EVAL_STATE["current"] = 0

    engine = QueryEngine()
    records: List[Dict[str, Any]] = []

    for idx, q in enumerate(questions, 1):
        pred = engine.query(q["question"])
        rec = evaluate_prediction(
            question_id=q.get("question_id", f"qst_{idx}"),
            question_type=q.get("question_type", "basic"),
            prediction=pred,
            expected_doc_ids=q.get("expected_doc_ids", []),
            gold_answer=q.get("gold_answer", ""),
            answer_facts=q.get("answer_facts", []),
        )
        records.append(rec)
        _EVAL_STATE["current"] = idx
        _EVAL_STATE["running_score"] = round(sum(r["composite_score"] for r in records) / idx, 2)

    summary = aggregate_benchmark_results(records, time.time() - _EVAL_STATE["start_time"])
    _EVAL_STATE["status"] = "completed"
    _EVAL_STATE["last_result"] = {"summary": summary, "per_question": records}

    # Save to disk
    out_path = Path("data/eval_results/eval_latest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(_EVAL_STATE["last_result"], f, indent=2)


@router.get("/latest")
def get_latest_eval():
    """
    Returns latest evaluation results, overall score, category breakdown, and total correct counts.
    """
    out_path = Path("data/eval_results/eval_latest.json")
    if not out_path.exists():
        raise HTTPException(status_code=404, detail="No evaluation results found. Run evaluation first.")

    with open(out_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data.get("summary", {})
    per_question = data.get("per_question", [])

    # Calculate Total Correct Count (correctness >= 0.5 or composite_score >= 50.0)
    correct_count = sum(1 for q in per_question if q.get("correctness", 0) >= 0.5 or q.get("composite_score", 0) >= 50.0)
    total_q = summary.get("total_questions", len(per_question))

    summary["correct_count"] = correct_count
    summary["total_count"] = total_q
    summary["correct_ratio"] = f"{correct_count} / {total_q}"

    return {
        "summary": summary,
        "total_records": len(per_question),
        "per_question_sample": per_question[:50],  # send top 50 sample for instant rendering
    }


@router.get("/status")
def get_eval_status():
    """
    Returns live progress status of the running evaluation task.
    """
    return {
        "status": _EVAL_STATE["status"],
        "current": _EVAL_STATE["current"],
        "total": _EVAL_STATE["total"],
        "category": _EVAL_STATE["category"],
        "running_score": _EVAL_STATE["running_score"],
        "elapsed_seconds": round(time.time() - _EVAL_STATE["start_time"], 1) if _EVAL_STATE["start_time"] and _EVAL_STATE["status"] == "running" else 0,
    }


@router.get("/questions")
def get_benchmark_questions(limit: Optional[int] = 50, category: Optional[str] = None):
    """
    Returns benchmark questions for UI explorer or picker.
    """
    q_path = Path("data/questions/questions.jsonl")
    if not q_path.exists():
        return {"questions": [], "total": 0}

    with open(q_path, "r", encoding="utf-8") as f:
        questions = [json.loads(line) for line in f if line.strip()]

    if category and category != "all":
        questions = [q for q in questions if q.get("question_type") == category]

    total = len(questions)
    if limit:
        questions = questions[:limit]

    return {
        "questions": questions,
        "total": total,
    }


@router.post("/run")
def start_eval(req: EvalRunRequest, background_tasks: BackgroundTasks):
    """
    Triggers background evaluation run across questions or a specific category.
    """
    if _EVAL_STATE["status"] == "running":
        return {"message": "Evaluation is already running", "status": "running"}

    background_tasks.add_task(_background_eval_task, req.category or "all", req.limit)
    return {
        "message": f"Evaluation started for category '{req.category or 'all'}'",
        "status": "started",
    }
