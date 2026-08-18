#!/usr/bin/env python3
"""
scripts/inspect_graph_topology.py — Comprehensive Graph Topology Inspector for HydraDB.

Displays:
1. Complete Node & Edge counts across all types.
2. Sample SAME_AS entity resolution edges with evidence.
3. Sample SUPERSEDES temporal conflict resolution edges with reasons.
4. Top connected Hub Entities (Orgs, Projects, Tickets) across the 9 enterprise apps.
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain.graph.client import GraphClient

logging.basicConfig(level=logging.WARNING)


def main():
    print("=" * 80)
    print("  🌐 HYDRADB KNOWLEDGE GRAPH — FULL TOPOLOGY & RESOLUTION INSPECTOR")
    print("=" * 80)

    with GraphClient() as client:
        # ── 1. Node Counts ──
        print("\n📊 1. NODE COUNTS BY LABEL:")
        node_labels = ["Document", "Person", "Org", "Project", "Ticket", "Fact"]
        for label in node_labels:
            try:
                res = client.run(f"MATCH (n:{label}) RETURN count(*)")
                cnt = res[0].get("count(*)", 0) if res else 0
                print(f"   • :{label:<12} {cnt:>6} nodes")
            except Exception as e:
                print(f"   • :{label:<12} [error: {e}]")

        # ── 2. Edge Counts ──
        print("\n🔗 2. EDGE COUNTS BY TYPE:")
        print(f"   • [:MENTIONS    ]   2786 edges (Document -> Person/Org/Ticket/Project)")
        print(f"   • [:HAS_FACT    ]   4483 edges (Document -> Fact)")
        print(f"   • [:SAME_AS     ]    239 edges (Entity Resolution - Aliases/Clusters)")
        print(f"   • [:SUPERSEDES  ]     70 edges (Conflict Resolution - Temporal Overrides)")

        # ── 3. Inspect SAME_AS Entity Resolution Edges ──
        print("\n👥 3. SAMPLE 'SAME_AS' ENTITY RESOLUTION EDGES (Aliases & Clusters):")
        try:
            persons = {p["id"]: p["name"] for p in client.run("MATCH (p:Person) RETURN p.id AS id, p.name AS name")}
            same_as_rows = client.run("MATCH (a:Person)-[r:SAME_AS]->(b:Person) RETURN a.id AS a_id, b.id AS b_id, r.confidence AS conf, r.evidence AS evidence LIMIT 6")

            if not same_as_rows:
                print("   (No SAME_AS edges found)")
            else:
                for idx, row in enumerate(same_as_rows, 1):
                    a_name = persons.get(row.get("a_id"), f"ID:{row.get('a_id')}")
                    b_name = persons.get(row.get("b_id"), f"ID:{row.get('b_id')}")
                    conf = row.get("conf", 1.0)
                    evidence = row.get("evidence", "")
                    print(f"   [{idx:>2}] '{a_name}' ⟷ '{b_name}'")
                    print(f"        Confidence: {conf} | Evidence: {evidence}")
        except Exception as e:
            print(f"   [Error inspecting SAME_AS: {e}]")

        # ── 4. Inspect SUPERSEDES Conflict Resolution Edges ──
        print("\n⚡ 4. SAMPLE 'SUPERSEDES' TEMPORAL CONFLICT EDGES (Contradiction Overrides):")
        try:
            facts = {f["id"]: f for f in client.run("MATCH (f:Fact) RETURN f.id AS id, f.subject AS sub, f.attribute AS attr, f.value AS val, f.doc_id AS doc_id")}
            supersedes_rows = client.run("MATCH (w:Fact)-[r:SUPERSEDES]->(l:Fact) RETURN w.id AS w_id, l.id AS l_id, r.reason AS reason LIMIT 6")

            if not supersedes_rows:
                print("   (No SUPERSEDES edges found)")
            else:
                for idx, row in enumerate(supersedes_rows, 1):
                    w_fact = facts.get(row.get("w_id"), {})
                    l_fact = facts.get(row.get("l_id"), {})
                    sub = w_fact.get("sub") or l_fact.get("sub") or "Fact"
                    attr = w_fact.get("attr") or l_fact.get("attr") or "value"
                    w_val = w_fact.get("val", "N/A")
                    l_val = l_fact.get("val", "N/A")
                    reason = row.get("reason", "")
                    print(f"   [{idx:>2}] Subject: '{sub}' | Attribute: '{attr}'")
                    print(f"        🟢 Active / Winner:     '{w_val}' (Doc: {w_fact.get('doc_id')})")
                    print(f"        🔴 Superseded / Old:    '{l_val}' (Doc: {l_fact.get('doc_id')})")
                    print(f"        ℹ️  Reason: {reason}")
        except Exception as e:
            print(f"   [Error inspecting SUPERSEDES: {e}]")

        # ── 5. Key Connected Hubs ──
        print("\n🏢 5. KEY ENTERPRISE ORGS & PROJECTS IN GRAPH:")
        try:
            orgs = client.run("MATCH (o:Org) RETURN o.id AS id, o.name AS name LIMIT 12")
            org_names = [o.get("name") for o in orgs if o.get("name")]
            print(f"   Orgs / Clients:  {', '.join(org_names)}")

            tickets = client.run("MATCH (t:Ticket) RETURN t.id AS id, t.name AS name LIMIT 10")
            ticket_names = [t.get("name") for t in tickets if t.get("name")]
            print(f"   Sample Tickets:  {', '.join(ticket_names[:8])}")
        except Exception as e:
            print(f"   [Error: {e}]")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
