"""
extraction/extractor.py — document extraction engine using Google GenAI SDK
with automatic circuit breaker and instant heuristic extraction fallback.
"""

import re
import time
import logging
from typing import Optional, List
from google import genai

from company_brain import config
from company_brain.extraction.prompts import (
    ExtractedEntity,
    ExtractedFact,
    DocumentExtractionResult,
    EXTRACTION_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

# Circuit breaker flag: if Gemini daily quota or rate limit is hit, switch immediately to heuristic extraction for all subsequent docs
_QUOTA_EXHAUSTED = False

# Initialize GenAI Client lazily
_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        config.validate()
        _client = genai.Client(api_key=config.get_gemini_api_key())
    return _client


def extract_from_document(
    doc_text: str,
    doc_id: str,
    source: str,
    force_heuristic: bool = False,
) -> DocumentExtractionResult:
    """
    Calls Gemini API to extract typed entities and facts.
    If force_heuristic=True or any API error/rate limit occurs, immediately triggers instant heuristic extraction without sleeping.
    """
    global _QUOTA_EXHAUSTED

    if not doc_text or not doc_text.strip():
        return DocumentExtractionResult(entities=[], facts=[])

    # If force_heuristic or circuit breaker triggered, run instant heuristic extraction immediately
    if force_heuristic or _QUOTA_EXHAUSTED:
        return _heuristic_fallback_extract(doc_text, doc_id, source)

    try:
        client = get_client()
        prompt = f"Source Type: {source}\nDocument ID: {doc_id}\n\nDocument Content:\n{doc_text[:8000]}"

        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config={
                "system_instruction": EXTRACTION_SYSTEM_PROMPT,
                "response_mime_type": "application/json",
                "response_schema": DocumentExtractionResult,
            },
        )
        if response.parsed:
            return response.parsed
        return DocumentExtractionResult(entities=[], facts=[])

    except Exception as exc:
        # On ANY API failure or 429 error, activate circuit breaker immediately
        logger.warning(
            "Gemini API call failed for doc_id=%s: %s. Activating instant heuristic circuit breaker.",
            doc_id, exc
        )
        _QUOTA_EXHAUSTED = True
        return _heuristic_fallback_extract(doc_text, doc_id, source)


def _heuristic_fallback_extract(doc_text: str, doc_id: str, source: str) -> DocumentExtractionResult:
    """
    Comprehensive rule-based heuristic extractor for enterprise documents.
    Extracts Person, Org, Ticket, and Fact assertions using pattern recognition & metadata parsing.
    Instant execution with 0 network calls and 0 sleep delay.
    """
    entities: List[ExtractedEntity] = []
    facts: List[ExtractedFact] = []
    seen_entities = set()

    # 1. Extract Emails -> Person entities
    emails = set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', doc_text))
    for email in emails:
        name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
        if name not in seen_entities:
            seen_entities.add(name)
            entities.append(ExtractedEntity(name=name, entity_type="Person", email=email))

        # Extract Org domain from non-generic email domains
        domain = email.split('@')[1].lower()
        if domain not in ("gmail.com", "yahoo.com", "hotmail.com", "outlook.com") and domain not in seen_entities:
            seen_entities.add(domain)
            org_name = domain.split('.')[0].title()
            entities.append(ExtractedEntity(name=org_name, entity_type="Org", domain=domain))

    # 2. Extract Handles (@username) -> Person entities
    handles = set(re.findall(r'@([a-zA-Z0-9_-]{3,20})', doc_text))
    for handle in handles:
        name = handle.replace('_', ' ').replace('-', ' ').title()
        if handle not in seen_entities and name not in ("Here", "Channel", "Everyone", "All"):
            seen_entities.add(handle)
            entities.append(ExtractedEntity(name=name, entity_type="Person", handle=handle))

    # 3. Extract Ticket keys (e.g. RED-104, ENG-402, LIN-89, SEC-12) -> Ticket entities
    tickets = set(re.findall(r'\b([A-Z]{2,6}-\d{1,6})\b', doc_text))
    for ticket in tickets:
        if ticket not in seen_entities:
            seen_entities.add(ticket)
            entities.append(ExtractedEntity(name=ticket, entity_type="Ticket", status="Open"))

    # 4. Extract Key-Value Fact assertions (e.g. "max_file_size: 10 MiB", "RTO_target = 30 minutes")
    kv_matches = re.findall(r'([a-zA-Z0-9_-]{3,30})\s*[:=]\s*([^\n,;]{1,80})', doc_text)
    ignore_keys = {"http", "https", "http_code", "url", "doc_id", "id", "created_at", "type", "content"}
    for k, v in kv_matches[:15]:
        attr = k.strip().lower()
        val = v.strip()
        if attr not in ignore_keys and len(val) > 1 and not val.startswith("//"):
            facts.append(ExtractedFact(
                subject=doc_id,
                attribute=attr,
                value=val,
                confidence=0.75,
            ))

    # 5. Extract bullet-point policy facts (e.g., "- Default expiration: 30 days")
    bullet_facts = re.findall(r'[-*]\s*([A-Za-z0-9 _-]{3,30})\s*:\s*([^\n]{1,80})', doc_text)
    for b_attr, b_val in bullet_facts[:10]:
        attr = b_attr.strip().lower()
        val = b_val.strip()
        if attr not in ignore_keys:
            facts.append(ExtractedFact(
                subject=doc_id,
                attribute=attr,
                value=val,
                confidence=0.75,
            ))

    return DocumentExtractionResult(entities=entities, facts=facts)
