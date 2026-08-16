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
    """

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self._uri = uri or config.BOLT_URI
        self._user = user or config.HYDRA_USER
        self._password = password or config.HYDRA_PASSWORD
        self._driver: Driver = GraphDatabase.driver(
            self._uri,
            auth=(self._user, self._password),
        )
        logger.info("GraphClient connected to %s", self._uri)

    def close(self) -> None:
        self._driver.close()
        logger.info("GraphClient closed.")

    def __enter__(self) -> GraphClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def get_session(self) -> Session:
        """Returns a persistent Neo4j Session for high-throughput batch writes."""
        return self._driver.session()

    def run(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
        strong: bool = False,
    ) -> list[dict[str, Any]]:
        access_mode = "WRITE" if strong else None
        with self._driver.session(
            fetch_size=1000,
            **({"default_access_mode": access_mode} if access_mode else {}),
        ) as session:
            result: Result = session.run(cypher, parameters or {})
            records = [dict(record) for record in result]
            result.consume()
            return records

    def run_write(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
        session: Session | None = None,
    ) -> list[dict[str, Any]]:
        """Convenience wrapper for write queries. Consumes result streams to prevent socket hangs."""
        if session is not None:
            result: Result = session.run(cypher, parameters or {})
            records = [dict(record) for record in result]
            result.consume()
            return records

        with self._driver.session() as s:
            result: Result = s.run(cypher, parameters or {})
            records = [dict(record) for record in result]
            result.consume()
            return records

    def run_batch(
        self,
        cypher: str,
        rows: list[dict[str, Any]],
        batch_size: int | None = None,
    ) -> int:
        """
        Execute a batched UNWIND write query.
        The Cypher must use `UNWIND $rows AS row` and reference `row.*`.
        Returns total number of rows written.
        """
        batch_size = batch_size or getattr(config, "WRITE_BATCH_SIZE", 200)
        total = 0
        with self._driver.session() as s:
            for i in range(0, len(rows), batch_size):
                chunk = rows[i : i + batch_size]
                res = s.run(cypher, {"rows": chunk})
                res.consume()
                total += len(chunk)
                logger.debug("Batch write progress: %d / %d rows", total, len(rows))
        return total

    def ping(self) -> bool:
        try:
            result = self.run("MATCH (n:Document) RETURN count(*)")
            return isinstance(result, list)
        except (ServiceUnavailable, Exception) as exc:
            logger.warning("HydraDB ping failed: %s", exc)
            return False
