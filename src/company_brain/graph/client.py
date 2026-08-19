"""
graph/client.py — thin wrapper around the Neo4j Bolt driver connecting to HydraDB.

Usage:
    from company_brain.graph.client import GraphClient

    client = GraphClient()
    result = client.run("RETURN 1 AS n")
    client.close()

    # Or as a context manager:
    with GraphClient() as client:
        client.run("MATCH (n) RETURN count(n) AS total")
"""

from __future__ import annotations

import logging
from typing import Any

from neo4j import GraphDatabase, Driver, Session, Result
from neo4j.exceptions import ServiceUnavailable

# Bypass Neo4j driver's strict product check for HydraDB (SlateDBGraph/0.1.0)
import neo4j._sync.io._common
neo4j._sync.io._common.check_supported_server_product = lambda agent: None

for mod_name in ("_bolt3", "_bolt4", "_bolt5", "_bolt"):
    try:
        mod = __import__(f"neo4j._sync.io.{mod_name}", fromlist=["check_supported_server_product"])
        setattr(mod, "check_supported_server_product", lambda agent: None)
    except (ImportError, AttributeError):
        pass

from company_brain import config

logger = logging.getLogger(__name__)


class GraphClient:
    """
    Wraps a Neo4j Bolt driver targeting HydraDB.

    - Uses `causal` consistency for normal reads/writes.
    - Use run(..., strong=True) for queries that must see the very latest write
      (e.g. right after a bulk load, before an eval run).
    """

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        connection_timeout: float = 5.0,
    ) -> None:
        self._uri = uri or config.BOLT_URI
        self._user = user or config.HYDRA_USER
        self._password = password or config.HYDRA_PASSWORD
        self._driver: Driver = GraphDatabase.driver(
            self._uri,
            auth=(self._user, self._password),
            connection_timeout=connection_timeout,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> GraphClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ── Query helpers ─────────────────────────────────────────────────────────

    def run(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
        strong: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Run a Cypher query and return all records as plain dicts.

        Args:
            cypher:     Cypher query string.
            parameters: Optional parameter dict for parameterised queries.
            strong:     If True, use strong consistency (slower but guaranteed
                        to see the latest committed write).
        """
        access_mode = "WRITE" if strong else None
        with self._driver.session(
            fetch_size=1000,
            **({"default_access_mode": access_mode} if access_mode else {}),
        ) as session:
            result: Result = session.run(cypher, parameters or {})
            return [dict(record) for record in result]

    def run_write(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Convenience wrapper for write queries using auto-commit RUN execution."""
        with self._driver.session() as session:
            result: Result = session.run(cypher, parameters or {})
            return [dict(record) for record in result]

    def run_batch(
        self,
        cypher: str,
        rows: list[dict[str, Any]],
        batch_size: int | None = None,
    ) -> int:
        """
        Execute a batched UNWIND write.

        The Cypher must use `UNWIND $rows AS row` and reference `row.*`.
        Returns the total number of rows processed.

        Example:
            client.run_batch(
                "UNWIND $rows AS row MERGE (d:Document {doc_id: row.doc_id}) SET d += row",
                rows=[{"doc_id": "abc", "source": "slack", ...}, ...],
            )
        """
        batch_size = batch_size or config.WRITE_BATCH_SIZE
        total = 0
        for i in range(0, len(rows), batch_size):
            chunk = rows[i : i + batch_size]
            self.run_write(cypher, {"rows": chunk})
            total += len(chunk)
            logger.debug("Batch write: %d / %d rows", total, len(rows))
        return total

    # ── Health check ──────────────────────────────────────────────────────────

    def ping(self) -> bool:
        """Return True if HydraDB is reachable."""
        try:
            result = self.run("MATCH (n:Document) RETURN count(*)")
            return isinstance(result, list)
        except (ServiceUnavailable, Exception) as exc:
            logger.warning("HydraDB ping failed: %s", exc)
            return False
