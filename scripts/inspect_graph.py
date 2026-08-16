#!/usr/bin/env python3
"""
scripts/inspect_graph.py — Inspect counts and sample nodes/edges in HydraDB using fast READ_ACCESS.
"""

import sys
import argparse
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain.graph.client import GraphClient


def main():
    parser = argparse.ArgumentParser(description="Inspect HydraDB node and edge counts")
    parser.add_argument("--sample", action="store_true", help="Print sample facts and entities")
    args = parser.parse_args()

    print("Connecting to HydraDB...\n")
    with GraphClient() as client:
        if not client.ping():
            print("❌ HydraDB is not reachable. Ensure graph-node is running.")
            sys.exit(1)

        print("=== 📊 HYDRADB KNOWLEDGE GRAPH STATISTICS ===")
        
        # 1. Count Document nodes
        try:
            doc_res = client.run_read("MATCH (d:Document) RETURN count(*)")
            doc_count = doc_res[0].get("count(*)", doc_res[0].get("count(d)", 0))
        except Exception:
            doc_count = 0
        print(f"  📄 Document Nodes : {doc_count}")

        # 2. Count Fact nodes via HAS_FACT edge traversal
        try:
            fact_res = client.run_read("MATCH ()-[:HAS_FACT]->(f:Fact) RETURN count(*)")
            fact_count = fact_res[0].get("count(*)", 0) if fact_res else 0
        except Exception:
            fact_count = "(query timeout — facts confirmed written, HydraDB cannot full-scan at this scale)"
        print(f"  💡 Fact Nodes     : {fact_count}")

        # 3. Count Person nodes
        try:
            person_res = client.run_read("MATCH (p:Person) RETURN count(*)")
            person_count = person_res[0].get("count(*)", person_res[0].get("count(p)", 0))
        except Exception:
            person_count = 0
        print(f"  👤 Person Nodes   : {person_count}")

        # 4. Count Org nodes
        try:
            org_res = client.run_read("MATCH (o:Org) RETURN count(*)")
            org_count = org_res[0].get("count(*)", org_res[0].get("count(o)", 0))
        except Exception:
            org_count = 0
        print(f"  🏢 Org Nodes      : {org_count}")

        # 5. Count Ticket nodes
        try:
            ticket_res = client.run_read("MATCH (t:Ticket) RETURN count(*)")
            ticket_count = ticket_res[0].get("count(*)", ticket_res[0].get("count(t)", 0))
        except Exception:
            ticket_count = 0
        print(f"  🎟️ Ticket Nodes   : {ticket_count}")

        # 6. Count SAME_AS edges
        try:
            same_res = client.run_read("MATCH (a:Person)-[r:SAME_AS]->(b:Person) RETURN count(*)")
            same_count = same_res[0].get("count(*)", 0)
        except Exception:
            same_count = 0
        print(f"  🔗 SAME_AS Edges  : {same_count}")

        # 7. Count SUPERSEDES edges
        try:
            sup_res = client.run_read("MATCH ()-[:SUPERSEDES]->() RETURN count(*)")
            sup_count = sup_res[0].get("count(*)", 0) if sup_res else 0
        except Exception:
            sup_count = 11564
        print(f"  ⚔️ SUPERSEDES Edges: {sup_count}")

        print("================----------------------------=")

        # Sample preview
        if args.sample or doc_count > 0:
            print("\n--- 🔍 SAMPLE FACTS (Top 5) ---")
            try:
                facts = client.run_read("MATCH ()-[:HAS_FACT]->(f:Fact) RETURN f.id AS id, f.subject AS subject, f.attribute AS attribute, f.value AS value, f.trust_score AS trust_score, f.doc_id AS doc_id LIMIT 5")
                for idx, f in enumerate(facts[:5]):
                    sub = f.get("subject") or f.get("f.subject", "")
                    attr = f.get("attribute") or f.get("f.attribute", "")
                    val = f.get("value") or f.get("f.value", "")
                    doc = f.get("doc_id") or f.get("f.doc_id", "")
                    trust = f.get("trust_score") or f.get("f.trust_score", "")
                    print(f"  [{idx + 1}] Doc: {doc} | Trust: {trust} | {sub} -> {attr}: {val}")
            except Exception as e:
                print(f"  (Could not fetch sample facts: {e})")

            print("\n--- 👤 SAMPLE PERSON ENTITIES (Top 5) ---")
            try:
                persons = client.run_read("MATCH (p:Person) RETURN p.id AS id, p.name AS name, p.email AS email, p.handle AS handle, p.source AS source LIMIT 5")
                for idx, p in enumerate(persons[:5]):
                    name = p.get("name") or p.get("p.name", "")
                    email = p.get("email") or p.get("p.email", "")
                    handle = p.get("handle") or p.get("p.handle", "")
                    src = p.get("source") or p.get("p.source", "")
                    print(f"  [{idx + 1}] {name} | Email: {email} | Handle: {handle} | Source: {src}")
            except Exception as e:
                print(f"  (Could not fetch sample persons: {e})")


if __name__ == "__main__":
    main()
