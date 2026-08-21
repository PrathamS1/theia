#!/usr/bin/env python3
"""
scripts/run_resolution.py — Entry point for Entity Resolution & Conflict Tagging.

Runs candidate pair blocking, SAME_AS edge creation, and SUPERSEDES conflict edge tagging in HydraDB.

Usage:
    python3 scripts/run_resolution.py [--heuristic]
"""

import sys
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain.graph.client import GraphClient
from company_brain.resolution.resolve import resolve_entities
from company_brain.resolution.conflicts import detect_and_tag_conflicts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_resolution")


def main():
    parser = argparse.ArgumentParser(description="Run Entity & Conflict Resolution")
    parser.add_argument("--workspace", "-w", type=str, default=None, help="Scope resolution to a specific live workspace user_id")
    parser.add_argument("--gold-only", action="store_true",
                        help="Restrict entity resolution to people mentioned by the 812 benchmark "
                             "documents. Required on the noisy corpus: resolution is O(n^2) over every "
                             "Person (~11.6k -> ~68M comparisons) and its co-occurrence query is an "
                             "unanchored scan that exceeds the 30s statement timeout.")
    args = parser.parse_args()

    logger.info("Starting Entity Resolution & Conflict Layer processing...")

    with GraphClient() as client:
        if not client.ping():
            logger.error("HydraDB is not reachable. Ensure graph-node is running.")
            sys.exit(1)

        # Step 1: Entity Resolution -> SAME_AS edges
        logger.info("Step 1: Entity Resolution...")
        gold_ids = None
        if args.gold_only:
            import json as _json
            from pathlib import Path as _Path
            _p = _Path(__file__).resolve().parent.parent / "data" / "staged_gold_docs.json"
            gold_ids = set(_json.load(open(_p, encoding="utf-8")).keys())
            logger.info("Gold-only scope: %d benchmark documents.", len(gold_ids))
        same_as_count = resolve_entities(client, workspace_id=args.workspace, doc_ids=gold_ids)

        # Step 2: Conflict Layer -> SUPERSEDES edges
        logger.info("Step 2: Conflict Detection & Tagging...")
        conflict_count = detect_and_tag_conflicts(client, workspace_id=args.workspace)

        logger.info("Resolution completed successfully!")
        logger.info("  SAME_AS edges created:   %d", same_as_count)
        logger.info("  SUPERSEDES edges created: %d", conflict_count)


if __name__ == "__main__":
    main()
