"""
extraction/extractor.py — document extraction engine using Google GenAI SDK.
"""

import logging
from typing import Optional
from google import genai

from company_brain import config
from company_brain.extraction.prompts import (
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
    """
    if not doc_text or not doc_text.strip():
        return DocumentExtractionResult(entities=[], facts=[])

    client = get_client()
    prompt = f"Source Type: {source}\nDocument ID: {doc_id}\n\nDocument Content:\n{doc_text[:8000]}"

    try:
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
        logger.error("Extraction failed for doc_id=%s: %s", doc_id, exc)
        return DocumentExtractionResult(entities=[], facts=[])
