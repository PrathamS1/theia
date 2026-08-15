"""
query/engine.py — Natural Language Query Engine built on HydraDB.

Pipeline:
1. NL question -> keyword + entity name extraction
2. Entity lookup: scan Person/Org names in graph for question mentions
3. Fact retrieval scoped to matched entity doc_ids (avoids full 10K fact scan)
4. Fallback: full fact retrieval if no entity match, filtered by keywords
5. Abstention check
6. LLM synthesis with cited graph facts
"""

import time
import logging
from typing import List, Dict, Any

from google import genai
from pydantic import BaseModel, Field

from company_brain import config
from company_brain.graph.client import GraphClient
from company_brain.query.cypher_templates import (
    build_fact_query,
    build_entity_name_query,
    build_org_name_query,
)
from company_brain.query.abstain import should_abstain

logger = logging.getLogger(__name__)

# Module-level entity cache — populated once on first call to answer_question.
# Avoids the 30s HydraDB timeout caused by traversing 4000 docs × 2914 persons
# on every single question.
_ENTITY_CACHE: List[Dict[str, Any]] = []
_ENTITY_CACHE_LOADED = False


def _load_entity_cache(client: GraphClient) -> None:
    """Pre-load all Person + Org entity names into memory (runs once per process)."""
    global _ENTITY_CACHE, _ENTITY_CACHE_LOADED
    if _ENTITY_CACHE_LOADED:
        return
    try:
        persons = client.run(build_entity_name_query())
        logger.info("Entity cache: loaded %d Person rows", len(persons))
        _ENTITY_CACHE.extend(persons)
    except Exception as exc:
        logger.warning("Could not load Person cache: %s", exc)
    try:
        orgs = client.run(build_org_name_query())
        logger.info("Entity cache: loaded %d Org rows", len(orgs))
        _ENTITY_CACHE.extend(orgs)
    except Exception as exc:
        logger.warning("Could not load Org cache: %s", exc)
    _ENTITY_CACHE_LOADED = True
    logger.info("Entity cache ready: %d total entities", len(_ENTITY_CACHE))

# Stop words for keyword extraction
_STOPWORDS = {
    "what", "is", "the", "are", "for", "on", "in", "to", "a", "an", "of",
    "and", "or", "how", "why", "which", "does", "do", "did", "was", "were",
    "has", "have", "had", "this", "that", "these", "those", "with", "from",
    "at", "by", "be", "been", "being", "their", "they", "it", "its",
}


class QueryAnswer(BaseModel):
    answer: str = Field(..., description="Direct answer to the natural language question")
    citations: List[str] = Field(default_factory=list, description="Document IDs used as evidence")
    abstained: bool = Field(False, description="True if the system abstained from answering")
    matched_entities: List[str] = Field(default_factory=list, description="Entity names matched from graph")


ANSWER_PROMPT = """\
You are Company Brain, an accurate enterprise AI assistant for Redwood Inference.
Answer the user's question using ONLY the provided verified graph facts retrieved from HydraDB.

Question: {question}

Retrieved Graph Facts (sorted by source trust, most authoritative first):
{facts_summary}

Instructions:
1. Provide a direct, concise answer based strictly on the facts above.
2. Include document ID citations [doc_id] for every factual claim.
3. If facts are contradictory, state which source is authoritative and why (trust_score).
4. If the facts are insufficient to answer, say "The available data does not fully address this question."
"""


def _extract_keywords(question: str) -> List[str]:
    """Extract meaningful keywords from a natural language question."""
    tokens = (
        question.lower()
        .replace("?", "")
        .replace(",", "")
        .replace(".", "")
        .replace("'s", "")
        .split()
    )
    return [t for t in tokens if len(t) > 2 and t not in _STOPWORDS]


def _match_entities(
    question_lower: str,
    keywords: List[str],
    entity_rows: List[Dict[str, Any]],
) -> List[str]:
    """
    Find entity names from the cache that appear in the question.
    Returns matched entity names (used for prompt context only).
    """
    matched_names: List[str] = []
    for row in entity_rows:
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        name_lower = name.lower()
        if any(kw in name_lower or name_lower in kw for kw in keywords):
            matched_names.append(name)
    return matched_names


def _filter_facts(
    facts: List[Dict[str, Any]],
    keywords: List[str],
    doc_ids: List[str] | None = None,
    limit: int = 40,
) -> List[Dict[str, Any]]:
    """
    Filter and rank facts by relevance:
    1. If doc_ids provided, restrict to those documents first
    2. Then keyword-match on subject/attribute/value
    3. Sort by trust_score descending
    4. Return top `limit` results
    """
    if doc_ids:
        doc_id_set = set(doc_ids)
        facts = [f for f in facts if str(f.get("doc_id") or f.get("f.doc_id", "")) in doc_id_set]

    if keywords:
        matched = []
        for f in facts:
            sub = str(f.get("subject") or f.get("f.subject", "")).lower()
            attr = str(f.get("attribute") or f.get("f.attribute", "")).lower()
            val = str(f.get("value") or f.get("f.value", "")).lower()
            if any(kw in sub or kw in attr or kw in val for kw in keywords):
                matched.append(f)
        facts = matched

    # Sort by trust_score descending (most authoritative first)
    facts.sort(
        key=lambda f: float(f.get("trust_score") or f.get("f.trust_score") or 0),
        reverse=True,
    )
    return facts[:limit]


def answer_question(question: str, client: GraphClient, use_llm: bool = True) -> QueryAnswer:
    """
    Execute a natural language question against HydraDB and return a cited answer.

    Strategy:
    - Extract keywords from question
    - Look up matching Person + Org entity names in graph
    - If entities matched: retrieve facts scoped to those entity doc_ids
    - If no entity match: retrieve facts from all docs, filter by keywords
    - Abstain if no relevant facts found
    - Synthesize answer with Gemini (or return raw facts if use_llm=False)
    """
    question_lower = question.lower()
    keywords = _extract_keywords(question)
    logger.debug("Keywords extracted: %s", keywords)

    # --- Step 1: Entity lookup from in-memory cache (loaded once at startup) ---
    matched_names: List[str] = []
    matched_doc_ids: List[str] = []
    _load_entity_cache(client)
    matched_names = _match_entities(question_lower, keywords, _ENTITY_CACHE)
    if matched_names:
        logger.debug("Matched entities: %s", matched_names[:3])

    # --- Step 2: Fact retrieval (full scan, filtered in Python) ---
    raw_facts: List[Dict[str, Any]] = []
    try:
        raw_facts = client.run(build_fact_query())
    except Exception as exc:
        logger.warning("Fact retrieval failed: %s", exc)

    # --- Step 3: Filter and rank facts by keyword relevance ---
    # Primary: keyword match on attribute + value (subject is doc_id, not useful)
    target_facts = _filter_facts(raw_facts, keywords, doc_ids=None, limit=40)

    # Fallback: if keyword matching returned nothing but graph has facts,
    # send top-40 facts by trust_score to LLM rather than blindly abstaining.
    # The LLM can determine relevance from the full question context.
    if not target_facts and raw_facts:
        logger.debug("Keyword match empty — falling back to top-40 facts by trust_score")
        sorted_all = sorted(
            raw_facts,
            key=lambda f: float(f.get("trust_score") or 0),
            reverse=True,
        )
        target_facts = sorted_all[:40]

    # --- Step 4: Abstention check ---
    abstain, reason = should_abstain(target_facts)
    if abstain:
        return QueryAnswer(
            answer="I don't know based on the available company data. " + reason,
            citations=[],
            abstained=True,
            matched_entities=matched_names,
        )

    # --- Step 5: Format fact summary ---
    facts_lines: List[str] = []
    doc_ids_cited: Set[str] = set()

    for f in target_facts:
        sub = f.get("subject") or f.get("f.subject", "")
        attr = f.get("attribute") or f.get("f.attribute", "")
        val = f.get("value") or f.get("f.value", "")
        doc = f.get("doc_id") or f.get("f.doc_id", "")
        trust = f.get("trust_score") or f.get("f.trust_score", "")
        src = f.get("source") or ""
        if doc:
            doc_ids_cited.add(str(doc))
        facts_lines.append(f"- [{doc}] (trust={trust}, src={src}) {sub} -> {attr}: {val}")

    facts_summary = "\n".join(facts_lines)

    # --- Step 6: LLM synthesis ---
    if not use_llm:
        return QueryAnswer(
            answer="According to verified company data:\n" + facts_summary,
            citations=list(doc_ids_cited),
            abstained=False,
            matched_entities=matched_names,
        )
    genai_client = genai.Client(api_key=config.get_gemini_api_key())
    prompt = ANSWER_PROMPT.format(question=question, facts_summary=facts_summary)

    max_retries = config.LLM_MAX_RETRIES
    backoff = config.LLM_RETRY_BACKOFF
    delay = config.LLM_DELAY_SECONDS

    for attempt in range(max_retries + 1):
        try:
            if delay > 0:
                time.sleep(delay)

            response = genai_client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
            )
            answer_text = response.text.strip() if response.text else "Unable to generate answer."
            return QueryAnswer(
                answer=answer_text,
                citations=list(doc_ids_cited),
                abstained=False,
                matched_entities=matched_names,
            )
        except Exception as exc:
            exc_str = str(exc)
            is_rate_limit = "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str or "Quota" in exc_str

            if is_rate_limit and attempt < max_retries:
                wait_time = (backoff ** (attempt + 1)) * max(1.0, delay)
                logger.warning(
                    "Rate limit hit during answer synthesis (attempt %d/%d). Retrying in %.1fs...",
                    attempt + 1, max_retries, wait_time,
                )
                time.sleep(wait_time)
            else:
                logger.error("LLM synthesis failed: %s. Returning raw facts.", exc)
                fallback = "According to verified company data:\n" + facts_summary
                return QueryAnswer(
                    answer=fallback,
                    citations=list(doc_ids_cited),
                    abstained=False,
                    matched_entities=matched_names,
                )

    return QueryAnswer(
        answer="According to verified company data:\n" + facts_summary,
        citations=list(doc_ids_cited),
        abstained=False,
        matched_entities=matched_names,
    )
