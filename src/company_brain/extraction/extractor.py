"""
extraction/extractor.py — document extraction engine using Google GenAI SDK
with automatic exponential backoff retries, rate-limiting delay, and heuristic fallback.
"""

import re
import time
import logging
from typing import Optional
from google import genai

from company_brain import config
from company_brain.extraction.prompts import (
    ExtractedEntity,
    ExtractedFact,
    DocumentExtractionResult,
    EXTRACTION_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

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
) -> DocumentExtractionResult:
    """
    Calls Gemini API with structured output config to extract typed entities and facts.
    Includes exponential backoff on 429 rate limits, pacing delay, and rule-based fallback.
    """
    if not doc_text or not doc_text.strip():
        return DocumentExtractionResult(entities=[], facts=[])

    client = get_client()
    prompt = f"Source Type: {source}\nDocument ID: {doc_id}\n\nDocument Content:\n{doc_text[:8000]}"

    max_retries = config.LLM_MAX_RETRIES
    backoff = config.LLM_RETRY_BACKOFF
    delay = config.LLM_DELAY_SECONDS

    for attempt in range(max_retries + 1):
        try:
            # Respect rate limit pacing
            if delay > 0:
                time.sleep(delay)

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
            exc_str = str(exc)
            is_rate_limit = "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str or "Quota" in exc_str
            
            if is_rate_limit and attempt < max_retries:
                wait_time = (backoff ** (attempt + 1)) * max(1.0, delay)
                logger.warning(
                    "Rate limit (429) hit for doc_id=%s (attempt %d/%d). Retrying in %.1fs...",
                    doc_id, attempt + 1, max_retries, wait_time
                )
                time.sleep(wait_time)
            else:
                logger.error("Extraction API call failed for doc_id=%s: %s. Using heuristic fallback.", doc_id, exc)
                return _heuristic_fallback_extract(doc_text, doc_id, source)

    return _heuristic_fallback_extract(doc_text, doc_id, source)


def _heuristic_fallback_extract(doc_text: str, doc_id: str, source: str) -> DocumentExtractionResult:
    """
    Rule-based heuristic extractor used when LLM API rate limits are exhausted.
    Extracts emails, handles, and key-value pair assertions using regex.
    """
    entities = []
    facts = []

    # 1. Extract Emails -> Person entities
    emails = set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', doc_text))
    for email in emails:
        name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
        entities.append(ExtractedEntity(name=name, entity_type="Person", email=email))

    # 2. Extract Handles (@username) -> Person entities
    handles = set(re.findall(r'@([a-zA-Z0-9_-]{3,20})', doc_text))
    for handle in handles:
        entities.append(ExtractedEntity(name=handle.title(), entity_type="Person", handle=handle))

    # 3. Extract Key-Value assertions (e.g., "max_file_size: 10 MiB", "status = active")
    kv_matches = re.findall(r'([a-zA-Z0-9_-]{3,30})\s*[:=]\s*([^\n,;]{1,60})', doc_text)
    for k, v in kv_matches[:12]:
        attr = k.strip().lower()
        val = v.strip()
        if attr not in ("http", "https", "http_code", "url", "doc_id") and len(val) > 1:
            facts.append(ExtractedFact(
                subject=doc_id,
                attribute=attr,
                value=val,
                confidence=0.7,
            ))

    logger.info("  [FALLBACK] Extracted %d entities, %d facts via heuristics for doc_id=%s", len(entities), len(facts), doc_id)
    return DocumentExtractionResult(entities=entities, facts=facts)
