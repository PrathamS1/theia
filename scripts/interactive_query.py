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

from company_brain.graph.client import GraphClient
from company_brain.indexing.vector_store import VectorStore

logging.basicConfig(level=logging.WARNING)

PRESET_QUESTIONS = [
    ("qst_0001 (Basic / Limit)", "What are the default size limits for file uploads and total request size for the new multipart upload support on the OpenAI-compatible API endpoints?"),
    ("qst_0002 (Metric)", "What is the name of the new metric added so SRE can track when server-side streaming sessions get finalized due to hitting the time limit?"),
    ("qst_0005 (Multi-Hop SLA)", "What failover sequence and recovery targets did MedThink specify for handling an EU region outage, including any limits on how long traffic can shift to the US?"),
    ("qst_0016 (Policy)", "What is the company policy for how long contractor access should last by default before it expires, according to the access and permissions playbook?"),
    ("qst_0036 (Temporal Conflict)", "On Streamly AI's dedicated pool dp-132-usw, what % of interactive burst credits should be reserved exclusively for priority=high routes?"),
    ("qst_0026 (Abstention)", "For the hot-route capacity protection rollout in us-east, which specific enterprise accounts were on the initial allowlist?"),
]


def main():
    print("=" * 70)
    print("  🧠 COMPANY BRAIN — INTERACTIVE HYDRADB & VECTOR QUERY EXPLORER")
    print("=" * 70)

    # 1. Load Vector Store
    vstore = VectorStore()
    if not vstore.load():
        print("[ERROR] Vector index not found. Run python3 scripts/run_ingest.py first.")
        return

    # 2. Connect to HydraDB
    try:
        client = GraphClient()
        if not client.ping():
            print("[ERROR] HydraDB is not reachable. Ensure bash scripts/start_hydradb.sh is running.")
            return
    except Exception as e:
        print(f"[ERROR] Could not connect to HydraDB: {e}")
        return

    # Load staged doc text cache for deep inspection
    staged_docs_path = Path("data/staged_gold_docs.json")
    staged_docs = {}
    if staged_docs_path.exists():
        with open(staged_docs_path, "r", encoding="utf-8") as f:
            staged_docs = json.load(f)

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

        # ── 1. Vector Anchor Search ──
        hits = vstore.search_similar(query, top_k=3)
        print("\n🔍 1. Vector Anchor Retrieval (all-MiniLM-L6-v2):")
        top_doc_id = None
        top_score = 0.0
        for rank, (doc_id, score, meta) in enumerate(hits, 1):
            source = meta.get("source", "unknown").upper()
            title = meta.get("title", doc_id)
            print(f"   #{rank} [{score:.4f}] [{source}] {doc_id} — {title}")
            if rank == 1:
                top_doc_id = doc_id
                top_score = score

        # ── 2. HydraDB Graph Inspection ──
        print("\n🕸️  2. HydraDB Graph Traversal & Ontology:")
        if top_doc_id:
            # Query Document node & related facts from HydraDB
            facts = client.run(f"MATCH (f:Fact {{doc_id: '{top_doc_id}'}}) RETURN f.subject, f.attribute, f.value, f.trust_score LIMIT 5")
            entities = client.run(f"MATCH (d:Document {{doc_id: '{top_doc_id}'}})-[:MENTIONS]->(e) RETURN e.name, e.source LIMIT 5")
            
            if entities:
                ent_names = [e.get("e.name") for e in entities if e.get("e.name")]
                print(f"   Entities Connected: {', '.join(ent_names)}")
            
            if facts:
                print(f"   Extracted Facts ({len(facts)}):")
                for f in facts:
                    print(f"     • {f.get('f.subject')}: {f.get('f.attribute')} = '{f.get('f.value')}' (trust: {f.get('f.trust_score')})")

        # ── 3. Decision & Answer Synthesis ──
        print("\n💡 3. Query Engine Output:")
        if top_score < 0.25:
            print("   ⚠️  Graph Abstention Triggered: Zero connected path in available data.")
            print("   Answer: \"The answer is not available in the company enterprise records.\"")
        else:
            doc_data = staged_docs.get(top_doc_id, {})
            text = doc_data.get("text", "")
            title = doc_data.get("title", "")
            source = doc_data.get("source", "")
            created_at = doc_data.get("created_at", "")

            # Show text snippet
            first_lines = "\n".join([line for line in text.splitlines() if line.strip()][:5])
            print(f"   Citations: [{source.upper()}] {top_doc_id} (Date: {created_at})")
            print(f"   Relevant Knowledge Snippet:\n   \"\"\"\n   {first_lines}\n   \"\"\"")

        print("=" * 70)

    client.close()
    print("Goodbye!")


if __name__ == "__main__":
    main()
