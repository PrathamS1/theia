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
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain.graph.client import GraphClient

logging.basicConfig(level=logging.WARNING)


def main():
    parser = argparse.ArgumentParser(description="Inspect HydraDB Graph Topology.")
    parser.add_argument("--workspace", "-w", type=str, default=None, help="Filter topology to a specific live workspace/user ID")
    args = parser.parse_args()

    ws = args.workspace

    print("=" * 80)
    if ws:
        print(f"  🌐 HYDRADB KNOWLEDGE GRAPH — LIVE WORKSPACE TOPOLOGY: '{ws}'")
    else:
        print("  🌐 HYDRADB KNOWLEDGE GRAPH — FULL CORPUS TOPOLOGY & RESOLUTION INSPECTOR")
    print("=" * 80)

    with GraphClient() as client:
        # ── 1. Node Counts ──
        print("\n📊 1. NODE COUNTS BY LABEL:")
        node_labels = ["Document", "Person", "Org", "Project", "Ticket", "Fact"]
        for label in node_labels:
            try:
                if ws:
                    res = client.run(f"MATCH (n:{label} {{workspace_id: $ws}}) RETURN count(*)", {"ws": ws})
                else:
                    res = client.run(f"MATCH (n:{label}) RETURN count(*)")
                cnt = res[0].get("count(*)", 0) if res else 0
                print(f"   • :{label:<12} {cnt:>6} nodes")
            except Exception as e:
                print(f"   • :{label:<12} [error: {e}]")

        # ── 2. Edge Counts ──
        print("\n🔗 2. EDGE COUNTS BY TYPE:")
        if ws:
            edge_queries = [
                ("MENTIONS", "MATCH ()-[r:MENTIONS {workspace_id: $ws}]->() RETURN count(*)", {"ws": ws}),
                ("HAS_FACT", "MATCH ()-[r:HAS_FACT {workspace_id: $ws}]->() RETURN count(*)", {"ws": ws}),
                ("SAME_AS", "MATCH ()-[r:SAME_AS {workspace_id: $ws}]->() RETURN count(*)", {"ws": ws}),
                ("SUPERSEDES", "MATCH ()-[r:SUPERSEDES {workspace_id: $ws}]->() RETURN count(*)", {"ws": ws}),
            ]
        else:
            edge_queries = [
                ("MENTIONS", "MATCH ()-[r:MENTIONS]->() RETURN count(*)", {}),
                ("HAS_FACT", "MATCH ()-[r:HAS_FACT]->() RETURN count(*)", {}),
                ("SAME_AS", "MATCH ()-[r:SAME_AS]->() RETURN count(*)", {}),
                ("SUPERSEDES", "MATCH ()-[r:SUPERSEDES]->() RETURN count(*)", {}),
            ]

        for item in edge_queries:
            etype = item[0]
            q = item[1]
            params = item[2]
            try:
                res = client.run(q, params) if params else client.run(q)
                cnt = res[0].get("count(*)", 0) if res else 0
                print(f"   • [:{etype:<13}] {cnt:>6} edges")
            except Exception as e:
                print(f"   • [:{etype:<13}] [error: {e}]")

        # ── 3. Inspect SAME_AS Entity Resolution Edges ──
        print("\n👥 3. SAMPLE 'SAME_AS' ENTITY RESOLUTION EDGES (Aliases & Clusters):")
        try:
            if ws:
                same_as_rows = client.run(
                    "MATCH (a:Person {workspace_id: $ws})-[r:SAME_AS]->(b:Person) RETURN a.name AS a_name, b.name AS b_name, r.confidence AS conf, r.evidence AS evidence LIMIT 6",
                    {"ws": ws}
                )
            else:
                same_as_rows = client.run("MATCH (a:Person)-[r:SAME_AS]->(b:Person) RETURN a.name AS a_name, b.name AS b_name, r.confidence AS conf, r.evidence AS evidence LIMIT 6")

            if not same_as_rows:
                print("   (No SAME_AS edges found)")
            else:
                for idx, row in enumerate(same_as_rows, 1):
                    a_name = row.get("a_name") or row.get("a.name", "Unknown")
                    b_name = row.get("b_name") or row.get("b.name", "Unknown")
                    conf = row.get("conf") or row.get("r.confidence", 1.0)
                    evidence = row.get("evidence") or row.get("r.evidence", "")
                    print(f"   [{idx:>2}] '{a_name}' ⟷ '{b_name}'")
                    print(f"        Confidence: {conf} | Evidence: {evidence}")
        except Exception as e:
            print(f"   [Error inspecting SAME_AS: {e}]")

        # ── 4. Inspect SUPERSEDES Conflict Resolution Edges ──
        print("\n⚡ 4. SAMPLE 'SUPERSEDES' TEMPORAL CONFLICT EDGES (Contradiction Overrides):")
        try:
            if ws:
                supersedes_rows = client.run("MATCH ()-[r:SUPERSEDES {workspace_id: $ws}]->() RETURN r.winner_id AS w_id, r.loser_id AS l_id, r.reason AS reason, r.timestamp AS ts LIMIT 6", {"ws": ws})
            else:
                supersedes_rows = client.run("MATCH ()-[r:SUPERSEDES]->() RETURN r.winner_id AS w_id, r.loser_id AS l_id, r.reason AS reason, r.timestamp AS ts LIMIT 6")

            if not supersedes_rows:
                print("   (No SUPERSEDES edges found)")
            else:
                for idx, row in enumerate(supersedes_rows, 1):
                    w_id = row.get("w_id") or row.get("r.winner_id", "N/A")
                    l_id = row.get("l_id") or row.get("r.loser_id", "N/A")
                    reason = row.get("reason") or row.get("r.reason", "Temporal override")
                    ts = row.get("ts") or row.get("r.timestamp", "latest")
                    print(f"   [{idx:>2}] ℹ️  Reason:    {reason}")
                    print(f"        🕒 Timestamp: {ts} (Winner Fact ID: {w_id} ➔ Loser Fact ID: {l_id})")
        except Exception as e:
            print(f"   [Error inspecting SUPERSEDES: {e}]")

        # ── 5. Key Connected Hubs ──
        print("\n🏢 5. KEY ENTERPRISE ORGS & PROJECTS IN GRAPH:")
        try:
            if ws:
                orgs = client.run("MATCH (o:Org {workspace_id: $ws}) RETURN o.id AS id, o.name AS name LIMIT 12", {"ws": ws})
                tickets = client.run("MATCH (t:Ticket {workspace_id: $ws}) RETURN t.id AS id, t.name AS name LIMIT 10", {"ws": ws})
            else:
                orgs = client.run("MATCH (o:Org) RETURN o.id AS id, o.name AS name LIMIT 12")
                tickets = client.run("MATCH (t:Ticket) RETURN t.id AS id, t.name AS name LIMIT 10")
            
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
