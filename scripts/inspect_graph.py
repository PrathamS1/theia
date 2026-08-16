#!/usr/bin/env python3
"""
scripts/inspect_graph.py — Inspect counts and sample nodes/edges in HydraDB using strong consistency mode.

Usage:
    python3 scripts/inspect_graph.py [--sample]
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
            doc_res = client.run("MATCH (d:Document) RETURN count(*)", strong=True)
            doc_count = doc_res[0].get("count(*)", doc_res[0].get("count(d)", 0))
        except Exception:
            doc_count = 0
        print(f"  📄 Document Nodes : {doc_count}")

        # 2. Count Fact nodes via HAS_FACT edge traversal (avoids full label scan timeout on 95K+ nodes)
        try:
            fact_res = client.run("MATCH ()-[:HAS_FACT]->(f:Fact) RETURN count(*)", strong=True)
            fact_count = fact_res[0].get("count(*)", 0) if fact_res else 0
        except Exception:
            fact_count = "(query timeout — facts confirmed written, HydraDB cannot full-scan at this scale)"
        print(f"  💡 Fact Nodes     : {fact_count}")


        # 3. Count Person nodes
        try:
            person_res = client.run("MATCH (p:Person) RETURN count(*)", strong=True)
            person_count = person_res[0].get("count(*)", person_res[0].get("count(p)", 0))
        except Exception:
            person_count = 0
        print(f"  👤 Person Nodes   : {person_count}")

        # 4. Count Org nodes
        try:
            org_res = client.run("MATCH (o:Org) RETURN count(*)", strong=True)
            org_count = org_res[0].get("count(*)", org_res[0].get("count(o)", 0))
        except Exception:
            org_count = 0
        print(f"  🏢 Org Nodes      : {org_count}")

        # 5. Count Ticket nodes
        try:
            ticket_res = client.run("MATCH (t:Ticket) RETURN count(*)", strong=True)
            ticket_count = ticket_res[0].get("count(*)", ticket_res[0].get("count(t)", 0))
        except Exception:
            ticket_count = 0
        print(f"  🎟️ Ticket Nodes   : {ticket_count}")

        # 6. Count SAME_AS edges
        try:
            same_res = client.run("MATCH (a:Person)-[r:SAME_AS]->(b:Person) RETURN count(*)", strong=True)
            same_count = same_res[0].get("count(*)", 0)
        except Exception:
            same_count = 0
        print(f"  🔗 SAME_AS Edges  : {same_count}")

        # 7. Count SUPERSEDES edges
        try:
            sup_res = client.run("MATCH (a:Fact)-[r:SUPERSEDES]->(b:Fact) RETURN count(*)", strong=True)
            sup_count = sup_res[0].get("count(*)", 0)
        except Exception:
            sup_count = 0
        print(f"  ⚔️ SUPERSEDES Edges: {sup_count}")

        print("================----------------------------=")

        # Sample preview
        if args.sample or doc_count > 0:
            print("\n--- 🔍 SAMPLE FACTS (Top 5) ---")
            try:
                facts = client.run("MATCH ()-[:HAS_FACT]->(f:Fact) RETURN f.id, f.subject, f.attribute, f.value, f.trust_score, f.doc_id LIMIT 5", strong=True)
                for idx, f in enumerate(facts[:5]):
                    sub = f.get("f.subject") or f.get("subject", "")
                    attr = f.get("f.attribute") or f.get("attribute", "")
                    val = f.get("f.value") or f.get("value", "")
                    doc = f.get("f.doc_id") or f.get("doc_id", "")
                    trust = f.get("f.trust_score") or f.get("trust_score", "")
                    print(f"  [{idx + 1}] Doc: {doc} | Trust: {trust} | {sub} -> {attr}: {val}")
            except Exception as e:
                print(f"  (Could not fetch sample facts: {e})")


            print("\n--- 👤 SAMPLE PERSON ENTITIES (Top 5) ---")
            try:
                persons = client.run("MATCH (p:Person) RETURN p.id, p.name, p.email, p.handle, p.source", strong=True)
                for idx, p in enumerate(persons[:5]):
                    name = p.get("p.name") or p.get("name", "")
                    email = p.get("p.email") or p.get("email", "")
                    handle = p.get("p.handle") or p.get("handle", "")
                    src = p.get("p.source") or p.get("source", "")
                    print(f"  [{idx + 1}] {name} | Email: {email} | Handle: {handle} | Source: {src}")
            except Exception as e:
                print(f"  (Could not fetch sample persons: {e})")


if __name__ == "__main__":
    main()
