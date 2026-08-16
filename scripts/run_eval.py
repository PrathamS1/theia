"""
scripts/run_eval.py — Phase 4 Evaluation Harness.

Loops over questions in data/questions/questions.jsonl, executes each question
against the query engine, evaluates accuracy vs gold answers using token F1,
and reports metrics by category.

Usage:
    python3 scripts/run_eval.py [--limit N] [--save] [--heuristic]
"""

import json
import sys
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain import config
from company_brain.graph.client import GraphClient
from company_brain.query.engine import answer_question
from company_brain.eval.metrics import compute_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_eval")


def _token_f1(prediction: str, gold_facts: list[str]) -> float:
    """
    Compute token-level F1 between prediction text and gold answer facts.
    Each gold fact is tokenised; we check if prediction contains those tokens.
    Returns a score 0.0–1.0.
    """
    if not gold_facts:
        return 1.0  # No gold facts = abstention question; handled separately

    pred_tokens = set(prediction.lower().split())

    total_recall = 0.0
    for fact in gold_facts:
        fact_tokens = {
            t for t in fact.lower().split()
            if len(t) > 2
        }
        if not fact_tokens:
            continue
        overlap = len(pred_tokens & fact_tokens)
        recall = overlap / len(fact_tokens)
        total_recall += recall

    return total_recall / len(gold_facts)


def main():
    parser = argparse.ArgumentParser(description="Evaluate Company Brain on questions.jsonl")
    parser.add_argument("--limit", type=int, default=0, help="Max questions to evaluate (0 = all)")
    parser.add_argument("--save", action="store_true", help="Save results to data/eval_results.jsonl")
    parser.add_argument("--threshold", type=float, default=0.3,
                        help="Token F1 threshold to count an answer as correct (default: 0.3)")
    parser.add_argument("--heuristic", action="store_true", help="Run 100% deterministic non-AI synthesis (instant, zero API calls)")
    args = parser.parse_args()

    questions_path = config.QUESTIONS_FILE
    if not questions_path.exists():
        logger.error("Questions file %s not found. Run bash scripts/download_dataset.sh first.", questions_path)
        sys.exit(1)

    if args.heuristic:
        logger.info("⚡ Heuristic non-AI mode enabled: using deterministic graph synthesis without Gemini API calls.")

    logger.info("Loading questions from %s...", questions_path)
    questions = []
    with open(questions_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))

    if args.limit > 0:
        questions = questions[:args.limit]

    logger.info("Starting evaluation on %d questions (F1 threshold=%.2f)...", len(questions), args.threshold)
    results = []

    with GraphClient() as client:
        if not client.ping():
            logger.error("HydraDB not reachable. Start the graph-node first.")
            sys.exit(1)

        for idx, q_data in enumerate(questions):
            q_id = q_data.get("question_id", f"q{idx}")
            q_text = q_data.get("question", "")
            q_type = q_data.get("question_type", "basic")
            gold_facts = q_data.get("answer_facts", [])
            expects_abstain = q_data.get("expected_abstain", False)

            try:
                ans = answer_question(q_text, client, force_heuristic=args.heuristic)
            except Exception as exc:
                logger.warning("[%d/%d] Error on %s: %s", idx + 1, len(questions), q_id, exc)
                results.append({
                    "question_id": q_id,
                    "question_type": q_type,
                    "question": q_text,
                    "answer": "",
                    "citations": [],
                    "abstained": False,
                    "matched_entities": [],
                    "f1_score": 0.0,
                    "is_correct": False,
                    "gold_facts": gold_facts,
                })
                continue

            # Scoring — split by question type for accuracy
            if q_type == "abstention" or expects_abstain:
                # Correct iff system correctly abstained from answering
                is_correct = ans.abstained
                f1 = 1.0 if is_correct else 0.0

            elif q_type == "conflict_resolution":
                # Keyword overlap but require the winning fact's value to appear
                if not gold_facts:
                    is_correct = not ans.abstained
                    f1 = 1.0 if is_correct else 0.0
                else:
                    key_words = [w.lower() for w in " ".join(gold_facts).split() if len(w) > 4]
                    is_correct = any(w in ans.answer.lower() for w in key_words) and not ans.abstained
                    f1 = _token_f1(ans.answer, gold_facts)

            elif not gold_facts:
                # No gold facts given — mark as correct if not abstained
                is_correct = not ans.abstained
                f1 = 1.0 if is_correct else 0.0

            else:
                # Default (basic / multi_hop): token F1 threshold
                f1 = _token_f1(ans.answer, gold_facts)
                is_correct = f1 >= args.threshold


            results.append({
                "question_id": q_id,
                "question_type": q_type,
                "question": q_text,
                "answer": ans.answer,
                "citations": ans.citations,
                "abstained": ans.abstained,
                "matched_entities": getattr(ans, "matched_entities", []),
                "f1_score": round(f1, 4),
                "is_correct": is_correct,
                "gold_facts": gold_facts,
            })

            status = "✓" if is_correct else "✗"
            abstain_tag = " [ABSTAIN]" if ans.abstained else ""
            matched = getattr(ans, "matched_entities", [])
            entity_tag = f" entities={matched[:2]}" if matched else ""
            logger.info(
                "[%d/%d] %s %s (%s) F1=%.2f%s%s",
                idx + 1, len(questions), status, q_id, q_type, f1, abstain_tag, entity_tag,
            )

    # Compute and display metrics
    metrics = compute_metrics(results)
    logger.info("\n=== EVALUATION REPORT ===")
    logger.info("Total Questions:  %d", metrics["total_questions"])
    logger.info("Overall Accuracy: %.2f%%", metrics["overall_accuracy"])
    logger.info("Mean F1 Score:    %.4f", metrics.get("mean_f1", 0.0))
    logger.info("\nCategory Breakdown:")
    for cat, stats in metrics["by_category"].items():
        logger.info(
            "  %-20s : %d / %d (%.2f%%) avg_f1=%.3f",
            cat,
            stats["correct"],
            stats["total"],
            stats["accuracy"],
            stats.get("avg_f1", 0.0),
        )

    if args.save:
        out_path = Path("data/eval_results.jsonl")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        logger.info("Results saved to %s", out_path)


if __name__ == "__main__":
    main()
