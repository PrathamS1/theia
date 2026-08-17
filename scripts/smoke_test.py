#!/usr/bin/env python3
"""
scripts/smoke_test.py — verify HydraDB is reachable and do a basic write/read/verify round trip.

Run this after starting HydraDB:
    python scripts/smoke_test.py

Expected output:
    [OK] HydraDB ping succeeded
    [OK] Wrote smoke-test node
    [OK] Read back: Company Brain smoke test
    [OK] Cleaned up
    All checks passed.
"""

import sys
from pathlib import Path

# Make src/ importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain.graph.client import GraphClient


def main() -> None:
    print("Connecting to HydraDB...")
    with GraphClient() as client:
        # 1. Ping using a labeled MATCH query required by HydraDB
        try:
            res = client.run("MATCH (n:Document) RETURN count(*)")
            print(f"[OK]  HydraDB connected successfully! Response: {res}")
        except Exception as e:
            print(f"[FAIL] HydraDB connection failed with error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        # 2. Write a smoke-test pattern with integer node IDs
        try:
            client.run_write(
                "CREATE (a:_SmokeTest {id: 101, name: 'smoke-1'})-[:TEST]->(b:_SmokeTest {id: 102, name: 'smoke-2'})"
            )
            print("[OK]  Wrote smoke-test graph pattern")

            # 3. Read it back
            rows = client.run("MATCH (a:_SmokeTest) RETURN a.id, a.name")
            print(f"[OK]  Read back nodes: {rows}")

            # 4. Clean up
            client.run_write("MATCH (a:_SmokeTest) DETACH DELETE a")
            print("[OK]  Cleaned up smoke-test nodes")
        except Exception as e:
            print(f"[FAIL] Node operation failed: {e}")
            sys.exit(1)

    print("\nAll checks passed. ✓")


if __name__ == "__main__":
    main()
