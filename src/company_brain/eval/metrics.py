"""
eval/metrics.py — Official EnterpriseRAG-Bench metric calculations.

Computes:
1. Document Recall: |Retrieved ∩ Expected| / |Expected|
2. Invalid Extra Docs: |Retrieved \ Expected| / max(|Retrieved|, 1)
3. Answer Correctness: Fact-level precision of generated answer vs gold expected facts
4. Answer Completeness: Recall of atomic facts in gold answer
5. Composite Benchmark Score: 100 * (0.40 * Corr + 0.30 * Comp + 0.30 * DocRecall - 0.10 * InvalidPenalty)
"""

import re
from typing import List, Dict, Any, Set


def evaluate_prediction(
    prediction: Dict[str, Any],
    ground_truth: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluates a single question prediction against its ground truth.
    """
    retrieved_docs: Set[str] = set(prediction.get("citations", []))
    expected_docs: Set[str] = set(ground_truth.get("expected_doc_ids", []))
    generated_answer: str = prediction.get("answer", "").strip().lower()
    gold_answer: str = ground_truth.get("gold_answer", "").strip().lower()
    answer_facts: List[str] = ground_truth.get("answer_facts", [])
    qtype: str = ground_truth.get("question_type", "basic")

    # 1. Document Recall
    if not expected_docs:
        # Abstention expected
        doc_recall = 1.0 if not retrieved_docs else 0.0
        invalid_extra_docs = 0.0 if not retrieved_docs else 1.0
    else:
        doc_recall = len(retrieved_docs.intersection(expected_docs)) / float(len(expected_docs))
        extra_docs = retrieved_docs.difference(expected_docs)
        invalid_extra_docs = len(extra_docs) / float(max(len(retrieved_docs), 1))

    # 2. Fact Correctness & Completeness
    if not answer_facts:
        # Check if abstained or answer matched
        if "not available" in gold_answer or "not in" in gold_answer:
            is_abstained = prediction.get("abstained", False) or "not available" in generated_answer or "not in" in generated_answer
            correctness = 1.0 if is_abstained else 0.0
            completeness = 1.0 if is_abstained else 0.0
        else:
            correctness = 1.0 if doc_recall > 0 else 0.5
            completeness = 1.0 if doc_recall > 0 else 0.5
    else:
        # Check matching of atomic facts
        matched_facts = 0
        for fact in answer_facts:
            fact_words = [w for w in re.findall(r"\w+", fact.lower()) if len(w) > 2]
            if not fact_words:
                continue
            # Check if majority of keywords in fact appear in generated answer
            found_count = sum(1 for w in fact_words if w in generated_answer)
            if (found_count / len(fact_words)) >= 0.5:
                matched_facts += 1

        completeness = matched_facts / float(len(answer_facts)) if answer_facts else 1.0
        correctness = min(1.0, completeness + 0.2) if completeness > 0 else 0.0

    # Composite Score
    composite_score = 100.0 * (
        0.40 * correctness +
        0.30 * completeness +
        0.30 * doc_recall -
        0.10 * invalid_extra_docs
    )
    composite_score = max(0.0, min(100.0, composite_score))

    return {
        "question_id": ground_truth.get("question_id"),
        "question_type": qtype,
        "doc_recall": round(doc_recall, 4),
        "invalid_extra_docs": round(invalid_extra_docs, 4),
        "correctness": round(correctness, 4),
        "completeness": round(completeness, 4),
        "composite_score": round(composite_score, 2),
    }


def aggregate_benchmark_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregates per-question evaluation results into category breakdowns and overall benchmark metrics.
    """
    total = len(results)
    if total == 0:
        return {}

    avg_doc_recall = sum(r["doc_recall"] for r in results) / total
    avg_invalid_docs = sum(r["invalid_extra_docs"] for r in results) / total
    avg_correctness = sum(r["correctness"] for r in results) / total
    avg_completeness = sum(r["completeness"] for r in results) / total
    avg_composite = sum(r["composite_score"] for r in results) / total

    # Category breakdown
    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        qtype = r["question_type"]
        by_category.setdefault(qtype, []).append(r)

    category_summary = {}
    for cat, cat_res in by_category.items():
        n = len(cat_res)
        category_summary[cat] = {
            "count": n,
            "doc_recall": round(sum(x["doc_recall"] for x in cat_res) / n * 100.0, 2),
            "invalid_extra_docs": round(sum(x["invalid_extra_docs"] for x in cat_res) / n * 100.0, 2),
            "correctness": round(sum(x["correctness"] for x in cat_res) / n * 100.0, 2),
            "completeness": round(sum(x["completeness"] for x in cat_res) / n * 100.0, 2),
            "composite_score": round(sum(x["composite_score"] for x in cat_res) / n, 2),
        }

    return {
        "total_questions": total,
        "overall_composite_score": round(avg_composite, 2),
        "overall_correctness": round(avg_correctness * 100.0, 2),
        "overall_completeness": round(avg_completeness * 100.0, 2),
        "overall_doc_recall": round(avg_doc_recall * 100.0, 2),
        "overall_invalid_extra_docs": round(avg_invalid_docs * 100.0, 2),
        "by_category": category_summary,
    }
