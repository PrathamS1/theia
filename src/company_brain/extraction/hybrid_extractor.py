"""
extraction/hybrid_extractor.py — Dual-layer extraction engine:
Layer A: Deterministic heuristics (regex, metadata, structured tickets, PRs, emails).
Layer B: Semantic fact extraction (LLM if configured, plus high-precision regex/NLP rules).
"""

import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from company_brain.extraction.prompts import (
    ExtractedEntity,
    ExtractedFact,
    DocumentExtractionResult,
)
from company_brain import config

logger = logging.getLogger(__name__)

# Known Redwood key organizations and entities
KNOWN_ORGS = {
    "MedThink", "Streamly AI", "Proxima Bank", "Satellite Grove", "EdgePath",
    "DossierHQ", "Ubiquiti", "GCP", "Google Cloud", "AWS", "Atelier Classroom AI",
    "Redwood", "Redwood Inference", "OpenAI", "Tethys Systems"
}

# Regex patterns
TICKET_PATTERN = re.compile(r"\b([A-Z]{2,6}-\d{3,7})\b")
PR_PATTERN = re.compile(r"\b(pr-\d{3,7}|PR\s*#?\d{3,7})\b", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b")
HANDLE_PATTERN = re.compile(r"(?<=[\s(])@([a-zA-Z0-9_.-]+)\b")
SYSTEM_POOL_PATTERN = re.compile(r"\b(dp-\d{2,4}-[a-z0-9]+)\b")
METRIC_KEY_PATTERN = re.compile(r"\b([a-z0-9_]+\.[a-z0-9_.]+[a-z0-9_])\b")

# A dotted token is not automatically a metric. Filenames, semantic versions and
# hostnames all match METRIC_KEY_PATTERN, and treating them as metrics is what
# filled the graph with `catalog.md`, `1.14.1` and `streamly.ai`.
_FILE_EXT = (
    ".py", ".md", ".txt", ".yaml", ".yml", ".json", ".ts", ".tsx", ".js", ".jsx",
    ".go", ".rs", ".java", ".sh", ".sql", ".toml", ".ini", ".cfg", ".csv", ".log",
    ".png", ".jpg", ".svg", ".pdf", ".html", ".css", ".lock", ".env",
)
_TLD = (".com", ".ai", ".io", ".net", ".org", ".dev", ".co", ".app", ".cloud", ".internal")
_SEMVER_RE = re.compile(r"^\d+(\.\d+)+[a-z0-9\-]*$")


# Words that mark a name as a team, system or product rather than a human. The
# graph currently carries `Eng Platform`, `Metrics Aggregation`, `Serving Runtime`
# and `HubSpot` as Person nodes, which then get bridged to each other by SAME_AS
# and make the identity-resolution demo look careless.
_NON_PERSON_WORDS = {
    "eng", "engineering", "team", "platform", "infra", "infrastructure", "ops",
    "devops", "sre", "support", "recruiting", "security", "legal", "finance",
    "sales", "marketing", "product", "design", "data", "analytics", "metrics",
    "aggregation", "runtime", "serving", "gateway", "pipeline", "service",
    "api", "backend", "frontend", "oncall", "on-call", "rotation", "channel",
    "group", "squad", "guild", "bot", "alerts", "notifications", "hubspot",
    "slack", "github", "jira", "confluence", "linear", "gmail", "fireflies",
    # Role and function nouns. These produced merges like `Lead <-> Comms Lead`,
    # `Procurement <-> Sarah_Procurement` and `Applied <-> Applied-Ml`: a shared
    # job title is not a shared identity.
    "lead", "leads", "comms", "procurement", "applied", "obs", "exec", "admin",
    "hr", "qa", "pm", "ml", "ai", "review", "reviewers", "approvals", "billing",
    "payments", "compliance", "risk", "partner", "partners", "vendor", "customer",
}


def _looks_like_person(name: str) -> bool:
    """
    Reject names that are clearly teams, systems or products.

    Conservative on purpose: a single shared word is enough to reject, because a
    false Person node is worse than a missed one here -- it pollutes SAME_AS,
    which is the feature the demo leans on.
    """
    n = name.strip()
    if not n or len(n) < 2:
        return False
    # Split on hyphens and underscores as well as whitespace: team handles are
    # routinely written `applied-ml-oncall`, `storage-team`, `Finance-Ops`, and
    # splitting on spaces alone treats each of those as one unrecognised word.
    words = {w.strip(".,:;()[]").lower() for w in re.split(r"[\s\-_/]+", n) if w}
    return not (words & _NON_PERSON_WORDS)


# The corpus is set in 2024-2027 (measured: 88% of recovered dates). Anything
# outside this window came from a 10-digit number that happened to look like an
# epoch, so it is discarded rather than trusted.
_CORPUS_MIN_YEAR = 2024
_CORPUS_MAX_YEAR = 2028

_EPOCH_RE = re.compile(r"\b(1[6-9]\d{8})\b")          # 10-digit unix seconds, 2020s
_YMD_RE = re.compile(r"\b(20[2-3]\d)([01]\d)([0-3]\d)\b")
_ISO_RE = re.compile(r"\b(20[2-3]\d-[01]\d-[0-3]\d)\b")


def infer_created_at(file_name: str, title: str, text: str) -> Optional[str]:
    """
    Recover a document's real timestamp from its filename or leading text.

    Every document in the corpus has a null `created_at`, so `conflicts.py` was
    sorting facts by the string `'None'` and silently falling through to
    trust_score -- i.e. "temporal supersession" had no temporal signal at all.
    Filenames carry unix epochs (`1763876000-dedicated-h200-eu-ap-launch`) and
    dates (`20270614-renewal-tier-consolidation`); measured recovery is ~56% of
    the corpus.

    Returns an ISO-8601 UTC string, or None when nothing credible is found --
    None is honest, whereas the previous hardcoded 2026-01-01 default was what
    made every fact look simultaneous.
    """
    body = f"{title} {text[:600]}"

    # Ordered by trust. The filename is authoritative when it carries a date at
    # all; inside prose, an explicit calendar date is far safer than a bare
    # 10-digit number, which is just as likely to be an id. Getting this ordering
    # wrong matters: created_at drives SUPERSEDES ranking, so a spurious future
    # timestamp would let a stale fact win.
    for candidate in (
        _epoch_in(file_name), _ymd_in(file_name), _iso_in(file_name),
        _iso_in(body), _ymd_in(body),
        _epoch_in(body),
    ):
        if candidate and _CORPUS_MIN_YEAR <= int(candidate[:4]) <= _CORPUS_MAX_YEAR:
            return candidate
    return None


def _epoch_in(s: str) -> Optional[str]:
    m = _EPOCH_RE.search(s or "")
    if not m:
        return None
    try:
        return datetime.fromtimestamp(int(m.group(1)), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, OSError, OverflowError):
        return None


def _ymd_in(s: str) -> Optional[str]:
    m = _YMD_RE.search(s or "")
    if not m:
        return None
    y, mo, d = (int(g) for g in m.groups())
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}T00:00:00Z"


def _iso_in(s: str) -> Optional[str]:
    m = _ISO_RE.search(s or "")
    return f"{m.group(1)}T00:00:00Z" if m else None


def _is_real_metric_key(token: str) -> bool:
    """
    True for dotted identifiers that plausibly name a metric or config key
    (`rlim.route.tokens.available`, `feature.enable_multipart_input`) and False for
    filenames, versions and hostnames.
    """
    t = token.lower().strip()
    if len(t) <= 5 or "." not in t:
        return False
    if t.endswith(_FILE_EXT) or t.endswith(_TLD):
        return False
    if _SEMVER_RE.match(t):
        return False
    # Real metric keys are namespaced words, not two bare numbers.
    head = t.split(".", 1)[0]
    return not head.isdigit()


def extract_entities_and_facts(
    doc_text: str,
    doc_id: str,
    source: str,
    title: str = "",
    created_at: str = "2026-01-01T00:00:00Z",
) -> DocumentExtractionResult:
    """
    Extracts entities and facts combining deterministic heuristics and semantic patterns.
    """
    entities: List[ExtractedEntity] = []
    facts: List[ExtractedFact] = []
    seen_entities: Set[str] = set()

    full_text = f"{title}\n{doc_text}"

    # ── 1. Extract Tickets & PRs ──────────────────────────────────────────────
    for match in TICKET_PATTERN.finditer(full_text):
        t_id = match.group(1)
        if t_id not in seen_entities:
            seen_entities.add(t_id)
            entities.append(ExtractedEntity(
                name=t_id,
                entity_type="Ticket",
                status="open",
            ))

    for match in PR_PATTERN.finditer(full_text):
        pr_id = match.group(1).lower().replace(" ", "")
        if pr_id not in seen_entities:
            seen_entities.add(pr_id)
            entities.append(ExtractedEntity(
                name=pr_id,
                entity_type="Project",
            ))

    # ── 2. Extract System Pools & Clusters ─────────────────────────────────────
    for match in SYSTEM_POOL_PATTERN.finditer(full_text):
        pool = match.group(1)
        if pool not in seen_entities:
            seen_entities.add(pool)
            entities.append(ExtractedEntity(
                name=pool,
                entity_type="Project",
            ))

    # ── 3. Extract Emails & Slack Handles ──────────────────────────────────────
    for match in EMAIL_PATTERN.finditer(full_text):
        email = match.group(1)
        name = email.split("@")[0].replace(".", " ").title()
        if name not in seen_entities:
            seen_entities.add(name)
            entities.append(ExtractedEntity(
                name=name,
                entity_type="Person",
                email=email,
            ))

    for match in HANDLE_PATTERN.finditer(full_text):
        handle = match.group(1)
        if handle.lower() not in ["here", "channel", "everyone"] and handle not in seen_entities:
            seen_entities.add(handle)
            entities.append(ExtractedEntity(
                name=handle,
                entity_type="Person",
                handle=f"@{handle}",
            ))

    # ── 4. Extract Known Orgs ──────────────────────────────────────────────────
    for org in KNOWN_ORGS:
        if re.search(r"\b" + re.escape(org) + r"\b", full_text, re.IGNORECASE):
            if org not in seen_entities:
                seen_entities.add(org)
                entities.append(ExtractedEntity(
                    name=org,
                    entity_type="Org",
                ))

    # ── 5. Extract Named Persons from Context Patterns ─────────────────────────
    person_patterns = [
        re.compile(r"(?:Founder|Author|Assignee|Reporter|Owner|Reviewer|Engineer|Lead):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"),
        re.compile(r"\b(?:with|by|from|to)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\b"),
    ]
    for pat in person_patterns:
        for match in pat.finditer(full_text):
            p_name = match.group(1).strip()
            if not _looks_like_person(p_name):
                continue
            if p_name not in seen_entities and len(p_name.split()) <= 3:
                seen_entities.add(p_name)
                entities.append(ExtractedEntity(
                    name=p_name,
                    entity_type="Person",
                ))

    # ── 6. Extract Precise Factual Propositions (Limits, Metrics, Policies) ────
    # Metric keys are recorded as *entities* the document references, not as Facts.
    #
    # This previously emitted ExtractedFact(subject=m, attribute="metric_name", value=m)
    # for every dotted token, which produced assertions of the form
    # "catalog.md metric_name is catalog.md" -- a triple whose subject equals its
    # value states nothing. Measured against the shipped graph those made up 96% of
    # all Fact nodes (19,193 of a 20,000 sample), burying the ~4% that carry a real
    # value and filling answers with dozens of lines of noise.
    for match in METRIC_KEY_PATTERN.finditer(full_text):
        metric = match.group(1)
        if not _is_real_metric_key(metric):
            continue
        if metric not in seen_entities:
            seen_entities.add(metric)
            entities.append(ExtractedEntity(
                name=metric,
                entity_type="Metric",
            ))

    # Size / Limit facts
    size_matches = re.finditer(r"(?:limit|size|cap|threshold|max|rpo|rto|p99|p95|p50|validity|credit|discount)[\s\w:]*?(\d+(?:\.\d+)?\s*(?:MiB|GiB|MB|GB|minutes?|hours?|days?|months?|ms|s|%|\$|USD))", full_text, re.IGNORECASE)
    for m in size_matches:
        val = m.group(1).strip()
        facts.append(ExtractedFact(
            subject=title or doc_id,
            attribute="limit_or_target",
            value=val,
            confidence=0.90,
        ))

    return DocumentExtractionResult(entities=entities, facts=facts)
