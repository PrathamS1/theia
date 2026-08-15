"""
eval/metrics.py — Compute accuracy and F1 metrics for eval harness results.
"""

from typing import Any


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute overall and per-category accuracy + mean F1 from eval results.

    Each result dict is expected to have:
        question_type: str
        is_correct: bool
        f1_score: float (0.0–1.0)
    """
    total = len(results)
    if total == 0:
        return {
            "total_questions": 0,
            "overall_accuracy": 0.0,
            "mean_f1": 0.0,
            "by_category": {},
        }

    correct = sum(1 for r in results if r.get("is_correct"))
    f1_scores = [float(r.get("f1_score", 0.0)) for r in results]
    mean_f1 = sum(f1_scores) / total

    by_category: dict[str, Any] = {}
    for r in results:
        cat = r.get("question_type", "unknown")
        if cat not in by_category:
            by_category[cat] = {"correct": 0, "total": 0, "f1_sum": 0.0}
        by_category[cat]["total"] += 1
        if r.get("is_correct"):
            by_category[cat]["correct"] += 1
        by_category[cat]["f1_sum"] += float(r.get("f1_score", 0.0))

    for cat, stats in by_category.items():
        t = stats["total"]
        stats["accuracy"] = round(100.0 * stats["correct"] / t, 2) if t else 0.0
        stats["avg_f1"] = round(stats["f1_sum"] / t, 4) if t else 0.0
        del stats["f1_sum"]

    return {
        "total_questions": total,
        "overall_accuracy": round(100.0 * correct / total, 2),
        "mean_f1": round(mean_f1, 4),
        "by_category": by_category,
    }
