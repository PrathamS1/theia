"""
graph/topology.py — read-only queries + caching for the graph visualisation API.

HydraDB 0.1.0 speaks a restricted openCypher subset (verified empirically):
  - no label-less MATCH, no variable-length paths, no undirected edges
  - RETURN only supports `binding.property` or `count(*)` -- never a bound node/rel
  - WHERE only supports property equality / STARTS WITH (no CONTAINS, no IN)
  - $param scalar binding works and is used throughout below (the rest of the
    codebase still f-string-interpolates Cypher, which this module avoids)

Performance is bimodal: a property-anchored 1-hop query (e.g. {doc_id: $did})
costs ~10-20ms; an unanchored relationship scan costs ~1.2-1.8s regardless of
LIMIT. So every per-node lookup here is anchored, and the few unavoidable
unanchored scans (paging documents, pulling all SAME_AS/SUPERSEDES) are cached.
"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from company_brain.graph.client import GraphClient

logger = logging.getLogger(__name__)

# label -> id property prefix used in Cytoscape node ids (doc_<doc_id>, person_<id>, ...)
_ENTITY_LABELS = ("Person", "Org", "Ticket", "Project")

# Cytoscape node-id prefix per label. Document uses "doc_" (not "document_")
# to match the frontend's existing citation-highlight convention, which
# constructs `doc_${docId}` directly from /api/query citations.
_ID_PREFIX = {
    "Document": "doc",
    "Person": "person",
    "Org": "org",
    "Ticket": "ticket",
    "Project": "project",
    "Fact": "fact",
}


def _node_id(label: str, key: Any) -> str:
    return f"{_ID_PREFIX.get(label, label.lower())}_{key}"


def _doc_node(row: Dict[str, Any]) -> Dict[str, Any]:
    doc_id = row["d.doc_id"]
    name = row.get("d.title") or doc_id
    return {
        "data": {
            "id": _node_id("Document", doc_id),
            "label": "Document",
            "name": name,
            "source": row.get("d.source", ""),
            "doc_id": doc_id,
            "created_at": row.get("d.created_at", ""),
        }
    }


def _entity_node(label: str, name_col: str, id_col: str, row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "data": {
            "id": _node_id(label, row[id_col]),
            "label": label,
            "name": row.get(name_col, ""),
        }
    }


def _fact_node(row: Dict[str, Any], is_active: Optional[bool] = None) -> Dict[str, Any]:
    subject = row.get("f.subject", "")
    attribute = row.get("f.attribute", "")
    value = row.get("f.value", "")
    data: Dict[str, Any] = {
        "id": _node_id("Fact", row["f.id"]),
        "label": "Fact",
        "name": f"{subject} · {attribute} = {value}",
        "subject": subject,
    }
    # Omitted (not False) when supersession status is unknown at this call
    # site, so the frontend's default (active) styling applies -- only facts
    # confirmed as superseded get the dashed/dimmed "stale" treatment.
    if is_active is not None:
        data["is_active"] = is_active
    return {"data": data}


def _edge(edge_id: str, source: str, target: str, etype: str, **extra: Any) -> Dict[str, Any]:
    d = {"id": edge_id, "source": source, "target": target, "type": etype, "label": etype}
    d.update(extra)
    return {"data": d}


def _open_client_with_retry(client_factory, tries: int = 8, delay: float = 5.0):
    """This dev environment's HydraDB graph-node process restarts roughly
    every 1-2 minutes (a manifest/GC issue on its local-filesystem storage
    backend, not something this app controls), with down-windows up to
    ~50s. A single failed connection attempt would otherwise 500 the whole
    dashboard for a condition that reliably clears within a minute, so
    retry with a budget wide enough to span one down-window. This only
    costs latency on the *first* successful fetch of a given cache key —
    fetch_seed/fetch_same_as/fetch_supersedes all cache their result
    indefinitely once they succeed once."""
    last_exc: Optional[Exception] = None
    for attempt in range(tries):
        try:
            client = client_factory()
            client.__enter__()
            return client
        except Exception as exc:
            last_exc = exc
            if attempt < tries - 1:
                time.sleep(delay)
    raise last_exc


@contextmanager
def _client_ctx(client_factory, tries: int = 3, delay: float = 2.0):
    client = _open_client_with_retry(client_factory, tries, delay)
    try:
        yield client
    finally:
        client.close()


class TopologyCache:
    """
    The graph is static after ingestion (nothing in this UI writes to it), so
    results are cached indefinitely per unique query and warmed once at
    startup rather than re-fetched on every dashboard load.
    """

    def __init__(self, client_factory=GraphClient) -> None:
        self._client_factory = client_factory
        # RLock (not Lock): fetch_seed/expand_node call _get_loser_ids() while
        # already holding this lock, and that in turn calls fetch_supersedes()
        # which re-acquires it -- a plain Lock deadlocks on that same-thread
        # re-entry.
        self._lock = threading.RLock()
        self._seed_cache: Dict[int, Dict[str, Any]] = {}
        self._expand_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._same_as: Optional[List[Dict[str, Any]]] = None
        self._supersedes: Optional[List[Dict[str, Any]]] = None
        self._loser_ids: Optional[set] = None

    # ---- warm-up -----------------------------------------------------------

    def warm(self, doc_limit: int = 30) -> None:
        """Runs the default seed + edge-set fetch once in a background thread."""

        def _run() -> None:
            try:
                t0 = time.perf_counter()
                self.fetch_seed(doc_limit=doc_limit)
                self.fetch_same_as()
                self.fetch_supersedes()
                logger.info("Topology cache warmed in %.2fs", time.perf_counter() - t0)
            except Exception:
                logger.exception("Topology cache warm-up failed (HydraDB may be unreachable)")

        threading.Thread(target=_run, name="topology-warm", daemon=True).start()

    def clear_cache(self, workspace_id: Optional[str] = None) -> None:
        with self._lock:
            if workspace_id:
                keys_to_del = [k for k in self._seed_cache if str(k).startswith(f"{workspace_id}_") or str(k).startswith(f"{workspace_id}")]
                for k in keys_to_del:
                    self._seed_cache.pop(k, None)
            else:
                self._seed_cache.clear()
            self._expand_cache.clear()
            self._same_as = None
            self._supersedes = None
            self._loser_ids = None

    # ---- seed ----------------------------------------------------------------

    def fetch_seed(self, doc_limit: int = 30, refresh: bool = False, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        cache_key = f"{workspace_id or 'default'}_{doc_limit}"
        if not refresh and cache_key in self._seed_cache:
            return self._seed_cache[cache_key]

        with self._lock:
            if not refresh and cache_key in self._seed_cache:
                return self._seed_cache[cache_key]

            with _client_ctx(self._client_factory) as client:
                if workspace_id:
                    doc_rows = client.run(
                        "MATCH (d:Document {workspace_id: $ws}) RETURN d.doc_id, d.title, d.source, d.created_at "
                        "ORDER BY d.doc_id LIMIT $lim",
                        {"ws": workspace_id, "lim": doc_limit},
                    )
                else:
                    doc_rows = client.run(
                        "MATCH (d:Document) RETURN d.doc_id, d.title, d.source, d.created_at "
                        "ORDER BY d.doc_id LIMIT $lim",
                        {"lim": doc_limit},
                    )

                nodes: List[Dict[str, Any]] = [_doc_node(r) for r in doc_rows]
                node_ids = {n["data"]["id"] for n in nodes}
                edges: List[Dict[str, Any]] = []
                eidx = 0
                losers = self._get_loser_ids(workspace_id=workspace_id)

                for r in doc_rows:
                    did = r["d.doc_id"]
                    doc_nid = _node_id("Document", did)

                    for label in _ENTITY_LABELS:
                        rows = client.run(
                            f"MATCH (d:Document {{doc_id: $did}})-[:MENTIONS]->(e:{label}) "
                            f"RETURN e.id, e.name LIMIT 15",
                            {"did": did},
                        )
                        for row in rows:
                            nid = _node_id(label, row["e.id"])
                            if nid not in node_ids:
                                node_ids.add(nid)
                                nodes.append(_entity_node(label, "e.name", "e.id", row))
                            eidx += 1
                            edges.append(_edge(f"e{eidx}", doc_nid, nid, "MENTIONS"))

                    fact_rows = client.run(
                        "MATCH (d:Document {doc_id: $did})-[:HAS_FACT]->(f:Fact) "
                        "RETURN f.id, f.subject, f.attribute, f.value LIMIT 8",
                        {"did": did},
                    )
                    for row in fact_rows:
                        nid = _node_id("Fact", row["f.id"])
                        if nid not in node_ids:
                            node_ids.add(nid)
                            nodes.append(_fact_node(row, is_active=row["f.id"] not in losers))
                        eidx += 1
                        edges.append(_edge(f"e{eidx}", doc_nid, nid, "HAS_FACT"))

                result = {"nodes": nodes, "edges": edges}
                self._seed_cache[cache_key] = result
                return result

    # ---- expand one node -----------------------------------------------------

    def expand_node(self, label: str, key: str, refresh: bool = False) -> Dict[str, Any]:
        cache_key = (label, key)
        if not refresh and cache_key in self._expand_cache:
            return self._expand_cache[cache_key]

        with self._lock:
            if not refresh and cache_key in self._expand_cache:
                return self._expand_cache[cache_key]

            with _client_ctx(self._client_factory) as client:
                nodes: List[Dict[str, Any]] = []
                edges: List[Dict[str, Any]] = []
                eidx = 0

                if label == "Document":
                    origin = _node_id("Document", key)
                    for ent_label in _ENTITY_LABELS:
                        rows = client.run(
                            f"MATCH (d:Document {{doc_id: $did}})-[:MENTIONS]->(e:{ent_label}) "
                            f"RETURN e.id, e.name LIMIT 25",
                            {"did": key},
                        )
                        for row in rows:
                            nid = _node_id(ent_label, row["e.id"])
                            nodes.append(_entity_node(ent_label, "e.name", "e.id", row))
                            eidx += 1
                            edges.append(_edge(f"x{eidx}", origin, nid, "MENTIONS"))

                    fact_rows = client.run(
                        "MATCH (d:Document {doc_id: $did})-[:HAS_FACT]->(f:Fact) "
                        "RETURN f.id, f.subject, f.attribute, f.value LIMIT 15",
                        {"did": key},
                    )
                    fact_losers = self._get_loser_ids()
                    for row in fact_rows:
                        nid = _node_id("Fact", row["f.id"])
                        nodes.append(_fact_node(row, is_active=row["f.id"] not in fact_losers))
                        eidx += 1
                        edges.append(_edge(f"x{eidx}", origin, nid, "HAS_FACT"))

                elif label in _ENTITY_LABELS:
                    origin = _node_id(label, key)
                    # documents that mention this entity, anchored on the entity's int id
                    rows = client.run(
                        f"MATCH (d:Document)-[:MENTIONS]->(e:{label} {{id: $eid}}) "
                        f"RETURN d.doc_id, d.title, d.source, d.created_at LIMIT 25",
                        {"eid": int(key)},
                    )
                    for row in rows:
                        nid = _node_id("Document", row["d.doc_id"])
                        nodes.append(_doc_node(row))
                        eidx += 1
                        edges.append(_edge(f"x{eidx}", nid, origin, "MENTIONS"))

                    if label == "Person":
                        same = client.run(
                            "MATCH (a:Person {id: $pid})-[:SAME_AS]->(b:Person) "
                            "RETURN b.id, b.name LIMIT 10",
                            {"pid": int(key)},
                        )
                        for row in same:
                            nid = _node_id("Person", row["b.id"])
                            nodes.append(_entity_node("Person", "b.name", "b.id", row))
                            eidx += 1
                            edges.append(_edge(f"x{eidx}", origin, nid, "SAME_AS", confidence=1.0))

                        same_rev = client.run(
                            "MATCH (a:Person)-[:SAME_AS]->(b:Person {id: $pid}) "
                            "RETURN a.id, a.name LIMIT 10",
                            {"pid": int(key)},
                        )
                        for row in same_rev:
                            nid = _node_id("Person", row["a.id"])
                            nodes.append(_entity_node("Person", "a.name", "a.id", row))
                            eidx += 1
                            edges.append(_edge(f"x{eidx}", nid, origin, "SAME_AS", confidence=1.0))

                elif label == "Fact":
                    origin = _node_id("Fact", key)
                    winners = client.run(
                        "MATCH (w:Fact)-[:SUPERSEDES]->(l:Fact {id: $fid}) "
                        "RETURN w.id, w.subject, w.attribute, w.value LIMIT 5",
                        {"fid": int(key)},
                    )
                    for row in winners:
                        nid = _node_id("Fact", row["w.id"])
                        nodes.append(_fact_node({
                            "f.id": row["w.id"], "f.subject": row["w.subject"],
                            "f.attribute": row["w.attribute"], "f.value": row["w.value"],
                        }, is_active=True))
                        eidx += 1
                        edges.append(_edge(f"x{eidx}", nid, origin, "SUPERSEDES"))

                    loser_rows = client.run(
                        "MATCH (w:Fact {id: $fid})-[:SUPERSEDES]->(l:Fact) "
                        "RETURN l.id, l.subject, l.attribute, l.value LIMIT 5",
                        {"fid": int(key)},
                    )
                    for row in loser_rows:
                        nid = _node_id("Fact", row["l.id"])
                        nodes.append(_fact_node({
                            "f.id": row["l.id"], "f.subject": row["l.subject"],
                            "f.attribute": row["l.attribute"], "f.value": row["l.value"],
                        }, is_active=False))
                        eidx += 1
                        edges.append(_edge(f"x{eidx}", origin, nid, "SUPERSEDES"))

                result = {"nodes": nodes, "edges": edges}
                self._expand_cache[cache_key] = result
                return result

    # ---- full edge-set pulls (small, safe to cache whole) ---------------------

    def fetch_same_as(self, refresh: bool = False) -> List[Dict[str, Any]]:
        if not refresh and self._same_as is not None:
            return self._same_as
        with self._lock:
            if not refresh and self._same_as is not None:
                return self._same_as
            with _client_ctx(self._client_factory) as client:
                rows = client.run(
                    "MATCH (a:Person)-[r:SAME_AS]->(b:Person) "
                    "RETURN a.id, a.name, b.id, b.name, r.confidence"
                )
                edges = []
                for i, row in enumerate(rows):
                    edges.append(_edge(
                        f"same_{i}",
                        _node_id("Person", row["a.id"]),
                        _node_id("Person", row["b.id"]),
                        "SAME_AS",
                        confidence=row.get("r.confidence", 1.0),
                    ))
                self._same_as = edges
                return edges

    def fetch_supersedes(self, refresh: bool = False) -> List[Dict[str, Any]]:
        if not refresh and self._supersedes is not None:
            return self._supersedes
        with self._lock:
            if not refresh and self._supersedes is not None:
                return self._supersedes
            with _client_ctx(self._client_factory) as client:
                rows = client.run(
                    "MATCH (a:Fact)-[:SUPERSEDES]->(b:Fact) "
                    "RETURN a.id, a.subject, a.value, b.id, b.value"
                )
                edges = []
                losers = set()
                for i, row in enumerate(rows):
                    reason = f"{row.get('a.value', '')} supersedes {row.get('b.value', '')}"
                    edges.append(_edge(
                        f"super_{i}",
                        _node_id("Fact", row["a.id"]),
                        _node_id("Fact", row["b.id"]),
                        "SUPERSEDES",
                        reason=reason,
                    ))
                    losers.add(row["b.id"])
                self._supersedes = edges
                self._loser_ids = losers
                return edges

    def _get_loser_ids(self, workspace_id: Optional[str] = None) -> set:
        """Fact ids on the losing side of a SUPERSEDES edge."""
        if self._loser_ids is None:
            self.fetch_supersedes()
        return self._loser_ids or set()


# Module-level singleton -- the graph is process-wide and read-only from this
# API's perspective, so one cache shared across requests is correct.
cache = TopologyCache()
