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
    parser.add_argument("--heuristic", action="store_true", help="Bypass LLM API and run instant rule-based resolution")
    args = parser.parse_args()

    logger.info("Starting Entity Resolution & Conflict Layer processing...")

    with GraphClient() as client:
        if not client.ping():
            logger.error("HydraDB is not reachable. Ensure graph-node is running.")
            sys.exit(1)

        # Step 1: Entity Resolution -> SAME_AS edges
        logger.info("Step 1: Entity Resolution...")
        same_as_count = resolve_entities(client, force_heuristic=args.heuristic)

        # Step 2: Conflict Layer -> SUPERSEDES edges
        logger.info("Step 2: Conflict Detection & Tagging...")
        conflict_count = detect_and_tag_conflicts(client)

        logger.info("Resolution completed successfully!")
        logger.info("  SAME_AS edges created:   %d", same_as_count)
        logger.info("  SUPERSEDES edges created: %d", conflict_count)


if __name__ == "__main__":
    main()
