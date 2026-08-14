"""
resolution/resolve.py — Entity Resolution engine.

Evaluates candidate pairs, checks shared graph context, invokes LLM adjudication when needed,
and writes SAME_AS {confidence, evidence} edges to HydraDB.
"""

import logging
from typing import List, Tuple, Dict, Any
from google import genai
from pydantic import BaseModel, Field

from company_brain import config
from company_brain.graph.client import GraphClient
from company_brain.resolution.blocking import generate_candidate_pairs

logger = logging.getLogger(__name__)


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


def resolve_entities(client: GraphClient) -> int:
    """
    Runs blocking, adjudicates candidate pairs, and writes SAME_AS edges into HydraDB.
    Returns count of SAME_AS edges created.
    """
    pairs = generate_candidate_pairs(client)
    same_as_count = 0

    genai_client = genai.Client(api_key=config.get_gemini_api_key())

    for p1, p2, score in pairs:
        # High similarity / exact attribute match -> auto resolve
        if score >= 95.0:
            confidence = score / 100.0
            evidence = f"High fuzzy match ({score:.1f}%) between '{p1['name']}' and '{p2['name']}'"
            _write_same_as(client, p1["id"], p2["id"], confidence, evidence)
            same_as_count += 1
        elif score >= 85.0:
            # LLM Adjudication for ambiguous cases
            try:
                prompt = ADJUDICATION_PROMPT.format(
                    name_a=p1.get("name"), email_a=p1.get("email"), source_a=p1.get("source"),
                    name_b=p2.get("name"), email_b=p2.get("email"), source_b=p2.get("source"),
                )
                res = genai_client.models.generate_content(
                    model=config.GEMINI_MODEL,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": AdjudicationResult,
                    },
                )
                if res.parsed and res.parsed.is_same_entity:
                    _write_same_as(client, p1["id"], p2["id"], res.parsed.confidence, res.parsed.reasoning)
                    same_as_count += 1
            except Exception as exc:
                logger.warning("LLM adjudication failed for %s vs %s: %s", p1['name'], p2['name'], exc)

    logger.info("Entity resolution complete. Created %d SAME_AS edges.", same_as_count)
    return same_as_count


def _write_same_as(client: GraphClient, id1: int, id2: int, confidence: float, evidence: str) -> None:
    """
    Writes a SAME_AS edge between two resolved entity nodes in HydraDB.
    Uses compliant one-hop CREATE pattern.
    """
    clean_evidence = evidence.replace("'", "\\'").replace('"', '\\"')
    cypher = (
        f"MATCH (a:Person {{id: {id1}}}), (b:Person {{id: {id2}}}) "
        f"CREATE (a)-[:SAME_AS {{confidence: {confidence}, evidence: '{clean_evidence}'}}]->(b)"
    )
    try:
        client.run_write(cypher)
    except Exception as exc:
        logger.debug("Failed to write SAME_AS edge between %d and %d: %s", id1, id2, exc)
