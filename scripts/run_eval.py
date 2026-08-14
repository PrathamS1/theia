#!/usr/bin/env python3
"""
scripts/run_eval.py — Entry point for Phase 4 Evaluation Harness.

Loops over questions in data/questions/questions.jsonl, executes each question against
the query engine, evaluates accuracy vs gold answers, and reports metrics by category.

Usage:
    python3 scripts/run_eval.py [--limit N]
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


def main():
    parser = argparse.ArgumentParser(description="Evaluate Company Brain on questions.jsonl")
    parser.add_argument("--limit", type=int, default=0, help="Max questions to evaluate (0 = all)")
    args = parser.parse_args()

    questions_path = config.QUESTIONS_FILE
    if not questions_path.exists():
        logger.error("Questions file %s not found. Run bash scripts/download_dataset.sh first.", questions_path)
        sys.exit(1)

    logger.info("Loading questions from %s...", questions_path)
    questions = []
    with open(questions_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))

    if args.limit > 0:
        questions = questions[:args.limit]

    logger.info("Starting evaluation on %d questions...", len(questions))
    results = []

    with GraphClient() as client:
        for idx, q_data in enumerate(questions):
            q_id = q_data.get("question_id")
            q_text = q_data.get("question")
            q_type = q_data.get("question_type", "basic")
            gold_facts = q_data.get("answer_facts", [])

            ans = answer_question(q_text, client)

            # Check if answer contains gold fact key terms
            correct_facts = 0
            for fact in gold_facts:
                key_words = [w.lower() for w in fact.split() if len(w) > 4]
                if any(w in ans.answer.lower() for w in key_words):
                    correct_facts += 1

            is_correct = (correct_facts >= max(1, len(gold_facts) // 2)) if gold_facts else (not ans.abstained)

            results.append({
                "question_id": q_id,
                "question_type": q_type,
                "question": q_text,
                "answer": ans.answer,
                "citations": ans.citations,
                "is_correct": is_correct,
            })

            logger.info("[%d/%d] %s (%s): %s", idx + 1, len(questions), q_id, q_type, "✓ Correct" if is_correct else "✗ Incorrect")

    metrics = compute_metrics(results)
    logger.info("\n=== EVALUATION REPORT ===")
    logger.info("Total Questions: %d", metrics["total_questions"])
    logger.info("Overall Accuracy: %.2f%%", metrics["overall_accuracy"])
    logger.info("\nCategory Breakdown:")
    for cat, stats in metrics["by_category"].items():
        logger.info("  %-15s : %d / %d (%.2f%%)", cat, stats["correct"], stats["total"], stats["accuracy"])


if __name__ == "__main__":
    main()
