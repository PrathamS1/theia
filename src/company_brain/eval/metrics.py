"""
eval/metrics.py — Metric calculations for EnterpriseRAG-Bench evaluation.
"""

from typing import List, Dict, Any


def compute_metrics(eval_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes accuracy metrics broken down by question_type.
    """
    by_category: Dict[str, Dict[str, int]] = {}

    for res in eval_results:
        qtype = res.get("question_type", "basic")
        if qtype not in by_category:
            by_category[qtype] = {"total": 0, "correct": 0}

        by_category[qtype]["total"] += 1
        if res.get("is_correct"):
            by_category[qtype]["correct"] += 1

    total_q = len(eval_results)
    total_correct = sum(1 for r in eval_results if r.get("is_correct"))
    overall_accuracy = (total_correct / total_q * 100.0) if total_q > 0 else 0.0

    category_summary = {}
    for cat, counts in by_category.items():
        tot = counts["total"]
        corr = counts["correct"]
        acc = (corr / tot * 100.0) if tot > 0 else 0.0
        category_summary[cat] = {"total": tot, "correct": corr, "accuracy": round(acc, 2)}

    return {
        "total_questions": total_q,
        "total_correct": total_correct,
        "overall_accuracy": round(overall_accuracy, 2),
        "by_category": category_summary,
    }
