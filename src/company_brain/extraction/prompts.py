"""
extraction/prompts.py — Pydantic models & prompt templates for LLM entity & fact extraction.

Uses google-genai structured JSON outputs to guarantee clean schema parsing.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ── Extracted Schema Models ───────────────────────────────────────────────────

class ExtractedEntity(BaseModel):
    name: str = Field(..., description="Canonical or extracted name of the entity")
    entity_type: str = Field(
        ...,
        description="Type: 'Person', 'Org', 'Project', 'Ticket', or 'Deal'",
    )
    email: Optional[str] = Field(None, description="Email if entity is Person")
    handle: Optional[str] = Field(None, description="Slack/GitHub handle if entity is Person")
    domain: Optional[str] = Field(None, description="Domain if entity is Org")
    status: Optional[str] = Field(None, description="Status if entity is Project or Ticket")


class ExtractedFact(BaseModel):
    subject: str = Field(..., description="Entity or topic the fact is about")
    attribute: str = Field(..., description="Attribute/key being asserted (e.g. 'max_file_size', 'RTO_target', 'status', 'owner')")
    value: str = Field(..., description="The value asserted (e.g. '10 MiB', '30 minutes', 'active')")
    confidence: float = Field(0.9, description="Confidence score between 0.0 and 1.0")


class DocumentExtractionResult(BaseModel):
    entities: List[ExtractedEntity] = Field(default_factory=list)
    facts: List[ExtractedFact] = Field(default_factory=list)


# ── Prompt Template ───────────────────────────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """
You are an expert enterprise ontology extractor for Redwood Inference.
Your task is to analyze the provided internal document (from Slack, Gmail, Linear, Drive, HubSpot, Fireflies, GitHub, or Confluence) and extract key typed entities and factual assertions.

Guidelines:
1. Extract all named entities mentioned (Person, Org, Project, Ticket, Deal).
2. For Person entities, include emails or handles if present.
3. Extract precise factual assertions (subject, attribute, value). Examples:
   - subject: "multipart upload", attribute: "max_file_size", value: "10 MiB"
   - subject: "MedThink EU failover", attribute: "RTO_target", value: "30 minutes"
   - subject: "Contractor access policy", attribute: "default_expiration", value: "30 days"
4. Be precise with exact numbers, configuration keys, time limits, and version strings.
"""
