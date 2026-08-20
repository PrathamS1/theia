#!/usr/bin/env python3
"""
scripts/create_indexes.py — run once to setup constraints & indexes in HydraDB.
Updated for the graph-native schema (adds Topic).
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain.graph.client import GraphClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("create_indexes")

STATEMENTS = [
    "CREATE CONSTRAINT doc_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
    "CREATE CONSTRAINT person_id_unique IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT org_id_unique IF NOT EXISTS FOR (o:Org) REQUIRE o.id IS UNIQUE",
    "CREATE CONSTRAINT ticket_id_unique IF NOT EXISTS FOR (t:Ticket) REQUIRE t.id IS UNIQUE",
    "CREATE CONSTRAINT project_id_unique IF NOT EXISTS FOR (pr:Project) REQUIRE pr.id IS UNIQUE",
    "CREATE CONSTRAINT deal_id_unique IF NOT EXISTS FOR (de:Deal) REQUIRE de.id IS UNIQUE",
    "CREATE CONSTRAINT topic_id_unique IF NOT EXISTS FOR (tp:Topic) REQUIRE tp.id IS UNIQUE",
    "CREATE CONSTRAINT fact_id_unique IF NOT EXISTS FOR (f:Fact) REQUIRE f.id IS UNIQUE",
    "CREATE INDEX fact_attribute_idx IF NOT EXISTS FOR (f:Fact) ON (f.attribute)",
    "CREATE INDEX doc_source_idx IF NOT EXISTS FOR (d:Document) ON (d.source)",
    "CREATE INDEX person_name_idx IF NOT EXISTS FOR (p:Person) ON (p.name)",
    "CREATE INDEX topic_name_idx IF NOT EXISTS FOR (tp:Topic) ON (tp.name)",
]


def main():
    logger.info("Setting up constraints and indexes in HydraDB...")
    with GraphClient() as client:
        for stmt in STATEMENTS:
            try:
                client.run_write(stmt)
                logger.info("OK: %s", stmt)
            except Exception as e:
                logger.info("Constraint/index note: %s -> %s", stmt, e)


if __name__ == "__main__":
    main()
