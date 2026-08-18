#!/usr/bin/env python3
"""
scripts/run_eval.py — Official EnterpriseRAG-Bench Evaluation Runner.

Runs 500 benchmark questions in strict blind inference mode:
1. Passes ONLY question_text into QueryEngine.
2. Evaluates Document Recall, Fact Correctness, Answer Completeness, and Extra Docs Penalty.
3. Computes Composite Benchmark Score and compares against Leaderboard (#1 Troml @ 76.79).
4. Saves full evaluation artifacts to data/eval_results/eval_latest.json.

Usage:
    python3 scripts/run_eval.py [--limit N]
"""

import sys
import json
import logging
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain.graph.client import GraphClient
from company_brain.query.engine import QueryEngine
from company_brain.eval.metrics import evaluate_prediction, aggregate_benchmark_results

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_eval")


def main():
    parser = argparse.ArgumentParser(description="Run EnterpriseRAG-Bench evaluation.")
    parser.add_argument("--questions", type=str, default="data/questions/questions.jsonl", help="Path to questions.jsonl file")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions evaluated (e.g. 50 or 500)")
    parser.add_argument("--output", type=str, default="data/eval_results/eval_latest.json", help="Output results file")
    parser.add_argument("--concurrency", type=int, default=1, help="Evaluation concurrency (default 1)")
    args = parser.parse_args()

    questions_file = Path(args.questions)
    if not questions_file.exists():
        logger.error("Questions file not found at %s", questions_file)
        sys.exit(1)

    # Load questions
    with open(questions_file, "r", encoding="utf-8") as f:
        all_questions = [json.loads(line) for line in f if line.strip()]

    if args.limit:
        all_questions = all_questions[:args.limit]

    logger.info("=== Starting Benchmark Evaluation on %d Questions ===", len(all_questions))
    logger.info("Connecting to HydraDB and initializing Hybrid Query Engine...")

    engine = QueryEngine()

    eval_records: List[Dict[str, Any]] = []
    start_time = time.time()

    with GraphClient() as client:
        for idx, q in enumerate(all_questions, 1):
            q_text = q["question"]
            qid = q.get("question_id", f"q_{idx}")
            qtype = q.get("question_type", "basic")

            # Strict blind query
            pred = engine.query(q_text, client=client)

            # Evaluate against ground truth
            eval_res = evaluate_prediction(
                prediction=pred.model_dump(),
                ground_truth=q
            )
            eval_records.append(eval_res)

            if idx % 50 == 0 or idx == len(all_questions):
                elapsed = time.time() - start_time
                avg_score = sum(r["composite_score"] for r in eval_records) / len(eval_records)
                logger.info("  [%d / %d] Elapsed: %.1fs | Running Composite Score: %.2f",
                            idx, len(all_questions), elapsed, avg_score)

    total_time = time.time() - start_time
    logger.info("Evaluation loop complete in %.2f seconds (%.2f q/s).", total_time, len(all_questions) / total_time)

    # Aggregate Benchmark Metrics
    summary = aggregate_benchmark_results(eval_records)
    summary["execution_time_seconds"] = round(total_time, 2)
    summary["questions_per_second"] = round(len(all_questions) / total_time, 2)

    # Save artifact
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "per_question": eval_records}, f, indent=2)

    # Display Report
    print("\n" + "=" * 80)
    print("  🏆 ENTERPRISERAG-BENCH EVALUATION REPORT — COMPANY BRAIN (HYDRADB)")
    print("=" * 80)
    print(f"\nTotal Questions Evaluated: {summary['total_questions']}")
    print(f"Total Execution Time:      {summary['execution_time_seconds']}s ({summary['questions_per_second']} queries/sec)")
    print("\n" + "-" * 80)
    print(f"  🎯 OVERALL COMPOSITE BENCHMARK SCORE:  {summary['overall_composite_score']} / 100.00")
    print(f"     • Fact Answer Correctness:          {summary['overall_correctness']}%")
    print(f"     • Answer Completeness:              {summary['overall_completeness']}%")
    print(f"     • Document Recall:                  {summary['overall_doc_recall']}%")
    print(f"     • Invalid Extra Docs:               {summary['overall_invalid_extra_docs']}%")
    print("-" * 80)

    # Category breakdown table
    print("\n📊 CATEGORY BREAKDOWN (10 DIMENSIONS):")
    print(f"  {'Category':<24} | {'Count':<5} | {'Score':<6} | {'Doc Recall':<10} | {'Correctness':<11} | {'Completeness':<12}")
    print("  " + "-" * 80)
    for cat, metrics in summary.get("by_category", {}).items():
        print(f"  {cat:<22} | {metrics['count']:<5} | {metrics['composite_score']:>6.2f} | {metrics['doc_recall']:>9.2f}% | {metrics['correctness']:>10.2f}% | {metrics['completeness']:>11.2f}%")
    print("=" * 80)


if __name__ == "__main__":
    main()
