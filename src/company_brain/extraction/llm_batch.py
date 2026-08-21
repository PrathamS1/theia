"""
extraction/llm_batch.py — batched, rate-limit-aware Gemini extraction.

Why this exists rather than calling extractor.extract_from_document per document:

* The free tier allows **5 requests per minute** for gemini-3.6-flash. One request
  per document puts an 812-document gold ingest at ~2.7 hours, and every 429 along
  the way risks silently degrading the result.
* `extractor.py`'s circuit breaker trips permanently on the first exception --
  including a 429, which is a "wait and retry" signal, not a failure -- and then
  falls back to `_heuristic_fallback_extract`, which emits assertions shaped like
  `(doc_id, "heads-up", "<sentence fragment>")`. A run that trips early produces a
  graph that is part LLM, part low-grade heuristic, with no record of the split.

This module batches several documents into one request, so the same 5 RPM budget
covers 5*BATCH_SIZE documents per minute, treats 429 as retryable with the
server's own suggested delay, and reports exactly which documents were extracted
by the LLM versus left to the caller's heuristic path.
"""

from __future__ import annotations

import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, Field

from company_brain import config
from company_brain.extraction.prompts import (
    ExtractedEntity,
    ExtractedFact,
    DocumentExtractionResult,
)

logger = logging.getLogger(__name__)


class _DocResult(BaseModel):
    doc_id: str = Field(..., description="The document id exactly as given in the input")
    entities: List[ExtractedEntity] = Field(default_factory=list)
    facts: List[ExtractedFact] = Field(default_factory=list)


class _BatchResult(BaseModel):
    documents: List[_DocResult] = Field(default_factory=list)


BATCH_SYSTEM_PROMPT = """
You are an expert enterprise ontology extractor for Redwood Inference.

You will receive SEVERAL internal documents in one message, each delimited by a
line of the form `### DOC <doc_id> (source)`. Extract typed entities and factual
assertions for EVERY document, and return one entry per document, echoing its
doc_id exactly.

Guidelines:
1. Extract named entities: Person, Org, Project, Ticket, Deal. Only real people
   are Person -- team names, systems and products (e.g. "Eng Platform",
   "Serving Runtime", "HubSpot") are NOT people.
2. Extract precise (subject, attribute, value) assertions. Examples:
   - subject: "multipart upload", attribute: "max_file_size", value: "10 MiB"
   - subject: "MedThink EU failover", attribute: "RTO_target", value: "30 minutes"
3. Never emit a fact whose value merely repeats its subject. A fact must assert
   something about the subject; "catalog.md is catalog.md" is not a fact.
4. Prefer exact numbers, configuration keys, limits, dates and version strings.
5. If a document contains nothing assertable, return it with empty lists rather
   than inventing content.
"""


@dataclass
class BatchStats:
    """Provenance for a run: which documents the LLM actually extracted."""
    llm_docs: int = 0
    heuristic_docs: int = 0
    requests: int = 0
    retries: int = 0
    failures: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "llm_docs": self.llm_docs,
            "heuristic_docs": self.heuristic_docs,
            "requests": self.requests,
            "retries": self.retries,
            "failures": len(self.failures),
        }


class _RateLimiter:
    """Simple sliding-window limiter: at most `per_minute` acquisitions a minute."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = max(1, per_minute)
        self._times: List[float] = []
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.time()
                self._times = [t for t in self._times if now - t < 60.0]
                if len(self._times) < self.per_minute:
                    self._times.append(now)
                    return
                wait = 60.0 - (now - self._times[0]) + 0.5
            time.sleep(max(wait, 0.5))


_RETRY_DELAY_RE = re.compile(r"retry in ([0-9.]+)s", re.I)


def _suggested_delay(exc: Exception, default: float) -> float:
    m = _RETRY_DELAY_RE.search(str(exc))
    if m:
        try:
            return min(float(m.group(1)) + 1.0, 120.0)
        except ValueError:
            pass
    return default


def _is_retryable(exc: Exception) -> bool:
    """
    True for conditions that clear on their own.

    Both matter in practice: 429 is the free tier's 5 req/min quota, and 503
    ("this model is currently experiencing high demand") shows up in bursts when
    several requests are in flight. Treating 503 as permanent — the original
    behaviour — silently dropped whole batches to the heuristic path; a 48-document
    trial lost all 48 that way.
    """
    s = str(exc)
    return any(tok in s for tok in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "500", "INTERNAL"))


def extract_batched(
    docs: Sequence[Tuple[str, str, str]],
    batch_size: int = 8,
    requests_per_minute: int = 5,
    max_retries: int = 6,
    max_chars_per_doc: int = 5000,
    concurrency: int = 4,
) -> Tuple[Dict[str, DocumentExtractionResult], BatchStats]:
    """
    Extract entities/facts for `docs` = [(doc_id, source, text), ...].

    Returns {doc_id: DocumentExtractionResult} containing only the documents the
    LLM successfully handled, plus a BatchStats describing coverage. Documents
    absent from the mapping must be extracted by the caller's heuristic path --
    which is deliberate: the caller owns the fallback, so it is always visible
    rather than silently substituted here.
    """
    from google import genai  # imported lazily so a missing key/SDK is not fatal

    results: Dict[str, DocumentExtractionResult] = {}
    stats = BatchStats()

    api_key = config.get_gemini_api_key()
    if not api_key:
        logger.info("No GEMINI_API_KEY set — skipping LLM extraction entirely.")
        stats.heuristic_docs = len(docs)
        return results, stats

    client = genai.Client(api_key=api_key)
    limiter = _RateLimiter(requests_per_minute)

    batches = [docs[i:i + batch_size] for i in range(0, len(docs), batch_size)]
    logger.info(
        "LLM extraction: %d documents in %d batches of %d (%d req/min, model=%s)",
        len(docs), len(batches), batch_size, requests_per_minute, config.GEMINI_MODEL,
    )

    # Generation, not the quota, is the bottleneck: one batch takes ~50s to come
    # back, so running them strictly in sequence uses barely one of the five
    # requests available each minute. Run several in flight against the shared
    # limiter, which still enforces the real ceiling.
    lock = threading.Lock()

    def run_batch(indexed: Tuple[int, Sequence[Tuple[str, str, str]]]) -> None:
        bi, batch = indexed
        prompt_parts = []
        for doc_id, source, text in batch:
            body = (text or "")[:max_chars_per_doc]
            prompt_parts.append(f"### DOC {doc_id} ({source})\n{body}")
        prompt = "\n\n".join(prompt_parts)

        parsed: Optional[_BatchResult] = None
        for attempt in range(max_retries):
            limiter.acquire()
            try:
                with lock:
                    stats.requests += 1
                response = client.models.generate_content(
                    model=config.GEMINI_MODEL,
                    contents=prompt,
                    config={
                        "system_instruction": BATCH_SYSTEM_PROMPT,
                        "response_mime_type": "application/json",
                        "response_schema": _BatchResult,
                    },
                )
                parsed = response.parsed
                break
            except Exception as exc:  # noqa: BLE001 - provider raises many types
                if _is_retryable(exc) and attempt < max_retries - 1:
                    # Exponential backoff for 503 bursts; the server's own retry hint
                    # wins when it supplies one (429 does).
                    delay = _suggested_delay(exc, default=min(8.0 * (2 ** attempt), 90.0))
                    with lock:
                        stats.retries += 1
                    logger.info(
                        "Batch %d/%d retrying in %.0fs (attempt %d/%d): %s",
                        bi, len(batches), delay, attempt + 1, max_retries, str(exc)[:60],
                    )
                    time.sleep(delay)
                    continue
                logger.warning("Batch %d/%d failed permanently: %s", bi, len(batches), str(exc)[:160])
                with lock:
                    stats.failures.extend(d[0] for d in batch)
                parsed = None
                break

        if not parsed or not parsed.documents:
            with lock:
                stats.heuristic_docs += len(batch)
            return

        returned = {d.doc_id for d in parsed.documents}
        with lock:
            for d in parsed.documents:
                # Drop any fact that asserts nothing, whatever the model said.
                facts = [
                    f for f in d.facts
                    if str(f.subject).strip().lower() != str(f.value).strip().lower()
                ]
                results[d.doc_id] = DocumentExtractionResult(entities=d.entities, facts=facts)
                stats.llm_docs += 1
            stats.heuristic_docs += len([d[0] for d in batch if d[0] not in returned])
            done = stats.llm_docs + stats.heuristic_docs
            logger.info(
                "  %d/%d docs — llm=%d heuristic=%d retries=%d",
                done, len(docs), stats.llm_docs, stats.heuristic_docs, stats.retries,
            )

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        list(pool.map(run_batch, enumerate(batches, 1)))

    return results, stats
