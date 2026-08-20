#!/usr/bin/env python3
"""
scripts/interactive_query.py — Interactive CLI Query & Graph Inspector for Company Brain.

Allows you to ask any natural-language question or select a preset,
and inspect the vector anchor lookup, HydraDB graph facts, conflict resolution, and answer.

Usage:
    python3 scripts/interactive_query.py
"""

import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain.query.engine import QueryEngine

logging.basicConfig(level=logging.WARNING)

PRESET_QUESTIONS = [
    ("qst_0001 (Basic / Limit)", "What are the default size limits for file uploads and total request size for the new multipart upload support on the OpenAI-compatible API endpoints?"),
    ("qst_0002 (Metric)", "What is the name of the new metric added so SRE can track when server-side streaming sessions get finalized due to hitting the time limit?"),
    ("qst_0005 (Multi-Hop SLA)", "What failover sequence and recovery targets did MedThink specify for handling an EU region outage, including any limits on how long traffic can shift to the US?"),
    ("qst_0016 (Policy)", "What is the company policy for how long contractor access should last by default before it expires, according to the access and permissions playbook?"),
    ("qst_0036 (Temporal Conflict)", "On Streamly AI's dedicated pool dp-132-usw, what % of interactive burst credits should be reserved exclusively for priority=high routes?"),
    ("qst_0481 (Abstention / Not in Data)", "For the hot-route capacity protection rollout in us-east, which specific enterprise accounts were on the initial allowlist, and what were the exact per-route-group budget values (RPS, estimated TPS, and concurrency) configured for each of those accounts?"),
    ("qst_0483 (Abstention / Missing Blockchain)", "For the admin activity chronicle's daily Merkle-root anchoring, which public blockchain network do we anchor to and what smart contract address is used, and how should an auditor verify the anchor end-to-end?"),
]


def main():
    print("=" * 70)
    print("  🧠 COMPANY BRAIN — INTERACTIVE HYDRADB & VECTOR QUERY EXPLORER")
    print("=" * 70)

    try:
        engine = QueryEngine()
    except Exception as e:
        print(f"[ERROR] Failed to initialize QueryEngine: {e}")
        return

    while True:
        print("\nPreset Questions:")
        for idx, (label, q_text) in enumerate(PRESET_QUESTIONS, 1):
            print(f"  [{idx}] {label}")
        print("  [C] Type Custom Question")
        print("  [Q] Quit")

        choice = input("\nSelect an option: ").strip()
        if choice.lower() == "q":
            break

        if choice.lower() == "c":
            query = input("\nEnter your question: ").strip()
        elif choice.isdigit() and 1 <= int(choice) <= len(PRESET_QUESTIONS):
            query = PRESET_QUESTIONS[int(choice) - 1][1]
        else:
            print("Invalid selection.")
            continue

        if not query:
            continue

        print("\n" + "-" * 70)
        print(f"❓ Question: {query}")
        print("-" * 70)

        # ── Execute Hybrid QueryEngine ──
        res = engine.query(query)

        # ── 1. Vector Anchor Search ──
        hits = engine.vector_store.search_similar_chunks(query, top_k=3)
        print("\n🔍 1. Vector Anchor Retrieval (all-MiniLM-L6-v2):")
        for rank, (doc_id, score, text, meta) in enumerate(hits, 1):
            source = meta.get("source", "unknown").upper() if meta else "DOC"
            title = meta.get("title", doc_id) if meta else doc_id
            print(f"   #{rank} [{score:.4f}] [{source}] {doc_id} — {title}")

        # ── 2. HydraDB Graph Inspection ──
        print("\n🕸️  2. HydraDB Graph Traversal & Ontology:")
        if res.traversed_entities:
            print(f"   Entities Traversed: {', '.join(res.traversed_entities)}")
        if res.facts_used:
            print(f"   Active Graph Facts Used ({len(res.facts_used)}):")
            for f in res.facts_used[:5]:
                print(f"     • {f.get('subject')}: {f.get('attribute')} = '{f.get('value')}'")
        else:
            print("   Active Graph Facts Used: (none / ungrounded)")

        # ── 3. Decision & Answer Synthesis ──
        print("\n💡 3. Query Engine Output:")
        if res.abstained:
            print("   ⚠️  Fact-Level Abstention Triggered: Target information is NOT in company knowledge base.")
            print(f"   Citations: {res.citations} (empty as required)")
            print(f"   Answer: \"{res.answer}\"")
        else:
            print(f"   Citations: {res.citations}")
            print(f"   Answer:\n   \"\"\"\n   {res.answer}\n   \"\"\"")

        print("=" * 70)

    engine.close()
    print("Goodbye!")


if __name__ == "__main__":
    main()
