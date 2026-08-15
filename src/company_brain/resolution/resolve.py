"""
resolution/resolve.py — Entity Resolution engine.

Evaluates candidate pairs, checks shared graph context, invokes LLM adjudication when needed,
and writes SAME_AS {confidence, evidence} edges to HydraDB.
Includes instant circuit breaker, pacing, and rule-based fallback on API limit exhaustion.
"""

import time
import logging
from typing import List, Tuple, Dict, Any, Optional
from google import genai
from pydantic import BaseModel, Field

from company_brain import config
from company_brain.graph.client import GraphClient
from company_brain.resolution.blocking import generate_candidate_pairs

logger = logging.getLogger(__name__)

# Circuit breaker flag for resolution adjudication
_QUOTA_EXHAUSTED = False


class AdjudicationResult(BaseModel):
    is_same_entity: bool = Field(..., description="True if both refers to the same real-world person/org")
    confidence: float = Field(..., description="Confidence score 0.0 to 1.0")
    reasoning: str = Field(..., description="Brief explanation of why they are or are not the same entity")


ADJUDICATION_PROMPT = """
You are an entity resolution expert for Redwood Inference's enterprise data.
Determine whether Entity A and Entity B refer to the exact same real-world person, organisation, or project.

Entity A:
Name: {name_a}
Email: {email_a}
Source: {source_a}

Entity B:
Name: {name_b}
Email: {email_b}
Source: {source_b}

Respond with JSON adhering to the schema.
"""


def resolve_entities(client: GraphClient, force_heuristic: bool = False) -> int:
    """
    Runs blocking, adjudicates candidate pairs, and writes SAME_AS edges into HydraDB.
    Returns count of SAME_AS edges created.
    """
    pairs = generate_candidate_pairs(client)
    same_as_count = 0

    genai_client = None
    if not force_heuristic and not _QUOTA_EXHAUSTED:
        try:
            genai_client = genai.Client(api_key=config.get_gemini_api_key())
        except Exception:
            genai_client = None

    for p1, p2, score in pairs:
        # High similarity / exact attribute match -> auto resolve
        if score >= 95.0:
            confidence = round(score / 100.0, 2)
            evidence = f"High fuzzy match ({score:.1f}%) between '{p1['name']}' and '{p2['name']}'"
            if _write_same_as(client, p1, p2, confidence, evidence):
                same_as_count += 1
        elif score >= 85.0:
            # LLM Adjudication for ambiguous cases with instant fallback
            adjudicated = _adjudicate_pair_with_fallback(genai_client, p1, p2, score, force_heuristic)
            if adjudicated and adjudicated.is_same_entity:
                if _write_same_as(client, p1, p2, adjudicated.confidence, adjudicated.reasoning):
                    same_as_count += 1

    logger.info("Entity resolution complete. Created %d SAME_AS edges.", same_as_count)
    return same_as_count


def _adjudicate_pair_with_fallback(
    genai_client: Optional[genai.Client],
    p1: Dict[str, Any],
    p2: Dict[str, Any],
    score: float,
    force_heuristic: bool = False,
) -> AdjudicationResult:
    """
    Adjudicates candidate pair using Gemini API if available, or instantly falls back to rule-based logic.
    """
    global _QUOTA_EXHAUSTED

    if force_heuristic or _QUOTA_EXHAUSTED or genai_client is None:
        return _rule_fallback(p1, p2, score)

    prompt = ADJUDICATION_PROMPT.format(
        name_a=p1.get("name"), email_a=p1.get("email"), source_a=p1.get("source"),
        name_b=p2.get("name"), email_b=p2.get("email"), source_b=p2.get("source"),
    )

    try:
        res = genai_client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": AdjudicationResult,
            },
        )
        if res.parsed:
            return res.parsed
        return _rule_fallback(p1, p2, score)

    except Exception as exc:
        logger.warning(
            "API failure during adjudication of %s vs %s: %s. Activating instant rule fallback.",
            p1.get('name'), p2.get('name'), exc
        )
        _QUOTA_EXHAUSTED = True
        return _rule_fallback(p1, p2, score)


def _rule_fallback(p1: Dict[str, Any], p2: Dict[str, Any], score: float) -> AdjudicationResult:
    """Instant rule-based entity adjudication without network calls."""
    if score >= 88.0:
        return AdjudicationResult(
            is_same_entity=True,
            confidence=round(score / 100.0, 2),
            reasoning=f"Rule-based fallback: High name similarity ({score:.1f}%) between '{p1.get('name')}' and '{p2.get('name')}'"
        )
    return AdjudicationResult(
        is_same_entity=False,
        confidence=0.5,
        reasoning="Rule-based fallback: Similarity score below auto-merge threshold"
    )


def _write_same_as(client: GraphClient, p1: Dict[str, Any], p2: Dict[str, Any], confidence: float, evidence: str) -> bool:
    """
    Writes a SAME_AS edge between two resolved entity nodes in HydraDB.
    Uses HydraDB-compliant one-hop CREATE pattern: (a:Person)-[:SAME_AS]->(b:Person).
    """
    clean_evidence = _sanitize(evidence)
    name1 = _sanitize(str(p1.get("name", "")))
    name2 = _sanitize(str(p2.get("name", "")))
    src1 = str(p1.get("source", "raw")).lower()
    src2 = str(p2.get("source", "raw")).lower()

    cypher = (
        f"CREATE (a:Person {{id: {p1['id']}, name: '{name1}', source: '{src1}'}})"
        f"-[:SAME_AS {{confidence: {confidence}, evidence: '{clean_evidence}'}}]->"
        f"(b:Person {{id: {p2['id']}, name: '{name2}', source: '{src2}'}})"
    )
    try:
        client.run_write(cypher)
        return True
    except Exception as exc:
        logger.warning("Failed to write SAME_AS edge between %d and %d: %s", p1['id'], p2['id'], exc)
        return False


def _sanitize(text: str) -> str:
    if not text:
        return ""
    return text.replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
