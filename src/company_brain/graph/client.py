"""
graph/client.py — thin wrapper around the Neo4j Bolt driver connecting to HydraDB.

Usage:
    from company_brain.graph.client import GraphClient

    with GraphClient() as client:
        result = client.run_read("MATCH (d:Document) RETURN count(*)")
"""

from __future__ import annotations

import logging
from typing import Any

from neo4j import GraphDatabase, Driver, Session, Result, READ_ACCESS, WRITE_ACCESS
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


def _snapshot_of(session: Session, cypher: str) -> dict[str, Any] | None:
    """
    Read the session's Bolt bookmark and pull the graph epoch out of it.

    HydraDB bookmarks look like
        sgk:1:<namespace>:<graph>:<cell>:<epoch>
    where the trailing segment is a monotonically increasing epoch. Capturing it
    turns "the graph said so" into a checkable claim.
    """
    try:
        bookmarks = list(session.last_bookmarks().raw_values)
    except Exception:
        return None
    if not bookmarks:
        return None

    bookmark = bookmarks[-1]
    epoch: int | None = None
    tail = bookmark.rsplit(":", 1)[-1]
    if tail.isdigit():
        epoch = int(tail)

    return {"bookmark": bookmark, "read_epoch": epoch, "cypher": cypher}


class GraphClient:
    """
    Wraps a Neo4j Bolt driver targeting HydraDB.
    Explicitly separates READ_ACCESS (snapshot/causal fast path) and WRITE_ACCESS.
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

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> GraphClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def get_session(self, write: bool = False) -> Session:
        """Returns a Neo4j Session with explicit access mode."""
        mode = WRITE_ACCESS if write else READ_ACCESS
        return self._driver.session(default_access_mode=mode)

    def run_read(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
        fetch_size: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Execute read query using HydraDB's fast snapshot read path (READ_ACCESS).
        """
        with self._driver.session(
            default_access_mode=READ_ACCESS,
            fetch_size=fetch_size,
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
        """
        Execute write query using WRITE_ACCESS.
        """
        if session is not None:
            result: Result = session.run(cypher, parameters or {})
            records = [dict(record) for record in result]
            result.consume()
            return records

        with self._driver.session(default_access_mode=WRITE_ACCESS) as s:
            result: Result = s.run(cypher, parameters or {})
            records = [dict(record) for record in result]
            result.consume()
            return records

    def run(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
        strong: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Default run method — defaults to fast READ_ACCESS unless strong is specified.
        """
        mode = WRITE_ACCESS if strong else READ_ACCESS
        with self._driver.session(
            default_access_mode=mode,
            fetch_size=1000,
        ) as session:
            result: Result = session.run(cypher, parameters or {})
            records = [dict(record) for record in result]
            result.consume()
            self._last_snapshot = _snapshot_of(session, cypher)
            return records

    @property
    def last_snapshot(self) -> dict[str, Any] | None:
        """
        Provenance for the most recent read: the HydraDB bookmark, the graph epoch
        it pins, and the Cypher that produced it.

        The bookmark identifies an immutable point in the graph's history, so an
        answer can be re-checked against exactly the state that produced it rather
        than against whatever the graph looks like later.
        """
        return getattr(self, "_last_snapshot", None)

    def run_batch(
        self,
        cypher: str,
        rows: list[dict[str, Any]],
        batch_size: int | None = None,
    ) -> int:
        """
        Execute a batched UNWIND write query.
        """
        batch_size = batch_size or getattr(config, "WRITE_BATCH_SIZE", 200)
        total = 0
        with self._driver.session(default_access_mode=WRITE_ACCESS) as s:
            for i in range(0, len(rows), batch_size):
                chunk = rows[i : i + batch_size]
                res = s.run(cypher, {"rows": chunk})
                res.consume()
                total += len(chunk)
                logger.debug("Batch write progress: %d / %d rows", total, len(rows))
        return total

    def sync(self) -> None:
        """Forces reader synchronization against authoritative SlateDB writer epoch."""
        try:
            self.run("MATCH (d:Document) RETURN count(*)", strong=True)
        except Exception as e:
            logger.debug("HydraDB sync epoch ping: %s", e)

    def ping(self) -> bool:
        try:
            result = self.run_read("MATCH (n:Document) RETURN count(*)")
            return isinstance(result, list)
        except (ServiceUnavailable, Exception) as exc:
            logger.warning("HydraDB ping failed: %s", exc)
            return False
