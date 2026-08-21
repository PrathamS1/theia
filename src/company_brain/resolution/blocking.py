"""
resolution/blocking.py — High-recall candidate entity pair generation using rapidfuzz & graph co-occurrence.

Groups Person and Org entities into candidate clusters based on:
1. Exact email prefix / Slack handle matches
2. Name fuzzy similarity (token_sort_ratio / partial_ratio)
3. Shared document co-occurrences in HydraDB
"""

import logging
import re
from typing import List, Tuple, Dict, Any, Set, Optional
from rapidfuzz import fuzz

from company_brain import config
from company_brain.extraction.hybrid_extractor import _looks_like_person
from company_brain.graph.client import GraphClient

logger = logging.getLogger(__name__)


def generate_candidate_pairs(
    client: GraphClient,
    workspace_id: Optional[str] = None,
    doc_ids: Optional[Set[str]] = None,
) -> List[Tuple[Dict[str, Any], Dict[str, Any], float, List[str]]]:
    """
    Fetch Person entities from HydraDB and find matching candidate pairs.

    `doc_ids` restricts the candidate set to people mentioned by those documents.
    This matters because, despite the module name, there is no blocking here: the
    comparison is O(n^2) over every Person. On the full noisy corpus that is
    ~11.6k people, i.e. ~68M fuzzy comparisons, and the unanchored co-occurrence
    query below exceeds HydraDB's 30s statement timeout as well. Scoping to the
    812 benchmark documents keeps both tractable and puts the precision where it
    is actually measured.
    """
    try:
        if doc_ids:
            # Anchored per-document lookups: unanchored MENTIONS scans time out at
            # this graph size, and these are ~40ms each.
            seen: Dict[Any, Dict[str, Any]] = {}
            for did in doc_ids:
                try:
                    rows = client.run(
                        "MATCH (d:Document {doc_id: $did})-[:MENTIONS]->(p:Person) "
                        "RETURN p.id AS id, p.name AS name, p.source AS source",
                        {"did": did},
                    )
                except Exception:
                    continue
                for r in rows:
                    if r.get("id") is not None:
                        seen[r["id"]] = r
            persons = list(seen.values())
            logger.info("Scoped resolution to %d documents -> %d distinct persons.", len(doc_ids), len(persons))
        elif workspace_id:
            persons = client.run(f"MATCH (p:Person {{workspace_id: '{workspace_id}'}}) RETURN p.id AS id, p.name AS name, p.source AS source")
        else:
            persons = client.run("MATCH (p:Person) RETURN p.id AS id, p.name AS name, p.source AS source")
    except Exception as e:
        logger.warning("Failed to fetch Person nodes: %s", e)
        persons = []

    if not persons:
        return []

    # Map name -> list of person records
    candidate_pairs = []
    threshold = config.BLOCKING_THRESHOLD  # 85

    # Fetch document co-occurrence links: which persons are mentioned in the same documents
    co_occurrences: Dict[int, Set[str]] = {}
    try:
        if doc_ids:
            # Anchored, same as the person fetch above. The unanchored form below
            # exceeds the statement timeout once the graph is large, and because it
            # is caught and logged at debug level the failure is invisible: pairs
            # then get scored on fuzzy string similarity alone, with no evidence
            # that two names ever appeared in the same document.
            doc_mentions = []
            for did in doc_ids:
                try:
                    doc_mentions.extend(
                        client.run(
                            "MATCH (d:Document {doc_id: $did})-[:MENTIONS]->(p:Person) "
                            "RETURN p.id AS person_id, d.doc_id AS doc_id",
                            {"did": did},
                        )
                    )
                except Exception:
                    continue
        elif workspace_id:
            doc_mentions = client.run(
                f"MATCH (d:Document {{workspace_id: '{workspace_id}'}})-[:MENTIONS]->(p:Person {{workspace_id: '{workspace_id}'}}) RETURN p.id AS person_id, d.doc_id AS doc_id"
            )
        else:
            doc_mentions = client.run(
                "MATCH (d:Document)-[:MENTIONS]->(p:Person) RETURN p.id AS person_id, d.doc_id AS doc_id"
            )
        for row in doc_mentions:
            pid = row.get("person_id")
            did = row.get("doc_id")
            if pid and did:
                co_occurrences.setdefault(pid, set()).add(did)
        logger.info("Co-occurrence evidence loaded for %d persons.", len(co_occurrences))
    except Exception as e:
        logger.warning("Document co-occurrence lookup failed (pairs will score on names alone): %s", str(e)[:120])

    # Teams and systems still reach this point even though extraction now rejects
    # them: Person nodes are also minted from email local-parts and @handles, which
    # bypass that filter. Without this second gate the graph gains bridges like
    # `storage-team <-> edge-team` and `Finance-Ops <-> Finance`.
    before = len(persons)
    persons = [p for p in persons if _looks_like_person(str(p.get("name", "")))]
    if before != len(persons):
        logger.info("Dropped %d team/system-shaped names before pairing.", before - len(persons))

    # Compare pairs
    n = len(persons)
    # 70 was far too permissive. Measured on the rebuilt graph it merged
    # `Nadia Rahman`/`Priya Raman` (0.737), `Samantha`/`Sahana` (0.719) and
    # `Alisha`/`Lina` (0.800) -- distinct people with superficially similar
    # letters. Genuine cross-source aliases score well above this: `Lina Gomez`/
    # `Lina` and `Samantha`/`sam` are 0.90, `Connor Obrien`/`Connor_Obrien` 0.92.
    # A false identity bridge is far more damaging than a missed one, because it
    # silently merges two people's evidence into one answer.
    cross_source_threshold = 88
    for i in range(n):
        p1 = persons[i]
        name1 = str(p1.get("name", "")).strip()
        id1 = p1.get("id")
        source1 = str(p1.get("source", "")).lower()

        for j in range(i + 1, n):
            p2 = persons[j]
            name2 = str(p2.get("name", "")).strip()
            id2 = p2.get("id")
            source2 = str(p2.get("source", "")).lower()

            if not name1 or not name2 or name1.lower() == name2.lower():
                if name1 and name2 and name1.lower() == name2.lower():
                    # Same name mention from different sources
                    shared_docs = list(co_occurrences.get(id1, set()).intersection(co_occurrences.get(id2, set())))
                    candidate_pairs.append((p1, p2, 100.0, shared_docs))
                continue

            # Determine if this is a cross-source pair (e.g., slack vs github)
            is_cross_source = source1 != source2 and source1 and source2

            if is_cross_source:
                # Use handle-aware cross-source similarity with lower threshold
                score = _cross_source_similarity(name1, name2)
                effective_threshold = cross_source_threshold
            else:
                # Same-source: use standard name comparison
                score = _compute_name_similarity(name1, name2)
                effective_threshold = threshold

            # Check shared graph context
            shared_docs = list(co_occurrences.get(id1, set()).intersection(co_occurrences.get(id2, set())))
            # Co-occurrence is deliberately NOT a confidence boost.
            #
            # It used to add +20 to any pair scoring >=60, on the theory that two
            # names in the same document are probably the same person. The
            # opposite is usually true: a document names its distinct
            # participants. That boost is what pushed `R Mendes`/`Lucas Mendes`
            # (0.888), `R Mendes`/`Sofia Mendes` (0.880) and `Rafael`/`Rafael
            # Ortiz` (0.900) over the line -- colleagues who share a surname or a
            # first name and appear in the same thread.
            #
            # Shared documents are still recorded as evidence on the SAME_AS edge,
            # so a reviewer can see the basis for a merge; they just no longer
            # manufacture one.

            if score >= effective_threshold and not _same_surname_conflict(name1, name2):
                candidate_pairs.append((p1, p2, score, shared_docs))

    candidate_pairs = _drop_ambiguous(candidate_pairs)
    logger.info("Generated %d candidate entity pairs for resolution.", len(candidate_pairs))
    return candidate_pairs


def _same_surname_conflict(name1: str, name2: str) -> bool:
    """
    True when two names share a surname but their given names cannot be the same
    person -- i.e. colleagues, not aliases.

    `R Mendes` / `Rafael Mendes` is compatible: `R` is an initial of `Rafael`.
    `R Mendes` / `Lucas Mendes` and `R Mendes` / `Sofia Mendes` are not, and fuzzy
    scoring rates all three ~0.88 because the surname dominates the string.
    """
    a = [t for t in re.split(r"[\s\-_.]+", name1.lower()) if t]
    b = [t for t in re.split(r"[\s\-_.]+", name2.lower()) if t]
    if len(a) < 2 or len(b) < 2:
        return False
    if a[-1] != b[-1]:
        return False  # different surnames: this rule does not apply
    first_a, first_b = a[0], b[0]
    if first_a == first_b:
        return False
    # An initial or a truncation of the other is the same person.
    if first_a.startswith(first_b) or first_b.startswith(first_a):
        return False
    return True


def _drop_ambiguous(
    pairs: List[Tuple[Dict[str, Any], Dict[str, Any], float, List[str]]],
) -> List[Tuple[Dict[str, Any], Dict[str, Any], float, List[str]]]:
    """
    Discard merges for any short name that matches more than one distinct full name.

    `Rafael` scores 1.00 against `Rafael Mendes` and 0.90 against `Rafael Ortiz`;
    `R Mendes` matches `Rafael Mendes`, `Lucas Mendes` and `Sofia Mendes`. Keeping
    all of them silently fuses several colleagues into one identity, which is worse
    than leaving the mention unresolved -- an answer would then attribute one
    person's evidence to another.

    A partial name that is genuinely unambiguous in the corpus still resolves; only
    the contested ones are dropped.
    """
    by_short: Dict[str, set] = {}
    for p1, p2, _score, _docs in pairs:
        n1, n2 = str(p1.get("name", "")).strip(), str(p2.get("name", "")).strip()
        short, full = (n1, n2) if len(n1.split()) <= len(n2.split()) else (n2, n1)
        if len(short.split()) < len(full.split()):
            by_short.setdefault(short.lower(), set()).add(full.lower())

    contested = {s for s, fulls in by_short.items() if len(fulls) > 1}
    if not contested:
        return pairs

    kept = []
    for pair in pairs:
        n1 = str(pair[0].get("name", "")).strip().lower()
        n2 = str(pair[1].get("name", "")).strip().lower()
        if n1 in contested or n2 in contested:
            continue
        kept.append(pair)

    logger.info(
        "Dropped %d ambiguous pairs covering %d contested short names (e.g. %s).",
        len(pairs) - len(kept), len(contested), sorted(contested)[:3],
    )
    return kept


def _compute_name_similarity(name1: str, name2: str) -> float:
    """Calculates multi-angle fuzzy similarity between two entity names/handles."""
    n1 = name1.lower().replace("@", "").replace(".", " ")
    n2 = name2.lower().replace("@", "").replace(".", " ")

    # Direct token sort ratio
    sort_score = fuzz.token_sort_ratio(n1, n2)
    # Token set ratio (handles subset names like "Selene" vs "Selene Huang")
    set_score = fuzz.token_set_ratio(n1, n2)
    # Partial ratio (handles handle prefixes like "clara" in "Clara Nguyen")
    partial_score = fuzz.partial_ratio(n1, n2)

    return max(sort_score, (set_score * 0.7 + partial_score * 0.3))


def _normalize_handle(name: str) -> str:
    """
    Strips platform-specific noise from handles/logins for cross-source matching.
    '@pratham' -> 'pratham', 'PrathamS1' -> 'prathams', 'soham.r' -> 'soham r'
    """
    import re
    n = name.lower().strip()
    n = n.lstrip("@")
    n = re.sub(r"[._-]", " ", n)
    # Strip trailing digits (GitHub login suffixes like 'PrathamS1' -> 'prathams')
    n = re.sub(r"\d+$", "", n)
    return n.strip()


def _cross_source_similarity(name1: str, name2: str) -> float:
    """
    Computes similarity between handles from different platforms.
    Uses normalized handles for a fairer comparison.
    """
    h1 = _normalize_handle(name1)
    h2 = _normalize_handle(name2)

    sort_score = fuzz.token_sort_ratio(h1, h2)
    set_score = fuzz.token_set_ratio(h1, h2)
    partial_score = fuzz.partial_ratio(h1, h2)

    # Exact prefix match (e.g., 'pratham' starts with 'pratham' in 'prathams')
    if h1.startswith(h2) or h2.startswith(h1):
        return max(90.0, sort_score)

    return max(sort_score, (set_score * 0.6 + partial_score * 0.4))

