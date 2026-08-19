"""
extraction/hybrid_extractor.py — Dual-layer extraction engine:
Layer A: Deterministic heuristics (regex, metadata, structured tickets, PRs, emails).
Layer B: Semantic fact extraction (LLM if configured, plus high-precision regex/NLP rules).
"""

import re
import logging
from typing import List, Dict, Any, Set
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
            if p_name not in seen_entities and len(p_name.split()) <= 3:
                seen_entities.add(p_name)
                entities.append(ExtractedEntity(
                    name=p_name,
                    entity_type="Person",
                ))

    # ── 6. Extract Precise Factual Propositions (Limits, Metrics, Policies) ────
    # Metric facts
    for match in METRIC_KEY_PATTERN.finditer(full_text):
        metric = match.group(1)
        if "." in metric and len(metric) > 5 and not metric.endswith(".com") and not metric.endswith(".txt"):
            facts.append(ExtractedFact(
                subject=metric,
                attribute="metric_name",
                value=metric,
                confidence=0.95,
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
