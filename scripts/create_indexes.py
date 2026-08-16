"""
scripts/create_indexes.py — Create node constraints and indexes in HydraDB.

Usage:
    python3 scripts/create_indexes.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain.graph.client import GraphClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("create_indexes")

# OpenCypher index & constraint syntax variants
INDEX_STATEMENTS = [
    # OpenCypher / Neo4j 4.x syntax: CREATE CONSTRAINT ON (node:Label) ASSERT node.prop IS UNIQUE
    ("Document.id constraint", "CREATE CONSTRAINT ON (d:Document) ASSERT d.id IS UNIQUE"),
    ("Document.doc_id constraint", "CREATE CONSTRAINT ON (d:Document) ASSERT d.doc_id IS UNIQUE"),
    ("Person.id constraint", "CREATE CONSTRAINT ON (p:Person) ASSERT p.id IS UNIQUE"),
    ("Fact.id constraint", "CREATE CONSTRAINT ON (f:Fact) ASSERT f.id IS UNIQUE"),
    # OpenCypher / Neo4j 4.x index syntax: CREATE INDEX ON :Label(prop)
    ("Document.source index", "CREATE INDEX ON :Document(source)"),
    ("Person.name index", "CREATE INDEX ON :Person(name)"),
    ("Fact.subject index", "CREATE INDEX ON :Fact(subject)"),
    ("Fact.attribute index", "CREATE INDEX ON :Fact(attribute)"),
]


def main():
    logger.info("Connecting to HydraDB to create constraints and indexes...")
    with GraphClient() as client:
        if not client.ping():
            logger.error("HydraDB is not reachable.")
            sys.exit(1)

        for name, stmt in INDEX_STATEMENTS:
            try:
                client.run_write(stmt)
                logger.info("✓ Created: %s", name)
            except Exception as exc:
                logger.warning("Note on %s: %s", name, exc)

    logger.info("Index setup complete.")


if __name__ == "__main__":
    main()
