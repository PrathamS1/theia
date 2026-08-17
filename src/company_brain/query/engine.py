"""
query/engine.py — Natural Language Query Engine built on HydraDB.

Pipeline:
1. Natural language question -> Keyword/entity extraction
2. Multi-hop Graph retrieval over HydraDB (Entities -> SAME_AS aliases -> Documents -> Facts)
3. Conflict resolution (Prioritizes winning facts over SUPERSEDES losers by trust score)
4. Abstention check (if no relevant graph facts exist -> "Not in the data")
5. Synthesis: Uses Gemini LLM with automatic circuit-breaker fallback to deterministic non-AI synthesis on 429/quota limits.
"""

import time
import logging
from typing import Dict, Any, List, Set, Optional, Tuple
from google import genai
from pydantic import BaseModel, Field

from company_brain import config
from company_brain.graph.client import GraphClient
from company_brain.query.cypher_templates import (
    build_doc_facts_query,
    build_entity_docs_query,
    build_same_as_query,
)
from company_brain.query.abstain import should_abstain

logger = logging.getLogger(__name__)

# Global circuit breaker: if a 429 is hit once, all subsequent queries use deterministic synthesis instantly
_LLM_QUOTA_EXHAUSTED = False


class QueryAnswer(BaseModel):
    answer: str = Field(..., description="Direct answer to the natural language question")
    citations: List[str] = Field(default_factory=list, description="Document IDs used as evidence")
    abstained: bool = Field(False, description="True if the system abstained from answering")


ANSWER_PROMPT = """
You are Company Brain, an accurate enterprise AI assistant for Redwood Inference.
Answer the user's question using ONLY the provided verified graph facts retrieved from HydraDB.

Question: {question}

Retrieved Graph Facts:
{facts_summary}

Instructions:
1. Provide a direct, concise answer based strictly on the facts above.
2. Include document ID citations for every factual claim.
3. If the facts are contradictory, state which source/trust level is authoritative and why.
"""

# Cached entity and document directories to make query retrieval instantaneous (<10ms)
_CACHED_ENTITIES: Optional[List[Dict[str, Any]]] = None
_CACHED_DOCUMENTS: Optional[List[Dict[str, Any]]] = None


def _get_entity_directory(client: GraphClient) -> List[Dict[str, Any]]:
    global _CACHED_ENTITIES
    if _CACHED_ENTITIES is not None:
        return _CACHED_ENTITIES

    entities = []
    for label in ["Person", "Org", "Ticket"]:
        try:
            res = client.run_read(f"MATCH (e:{label}) RETURN e.id AS id, e.name AS name, e.source AS source")
            for r in res:
                if r.get("id") is not None and r.get("name"):
                    entities.append({
                        "id": r["id"],
                        "name": str(r["name"]),
                        "label": label,
                        "source": r.get("source", ""),
                    })
        except Exception as exc:
            logger.debug("Failed loading %s directory: %s", label, exc)

    _CACHED_ENTITIES = entities
    return _CACHED_ENTITIES


def _get_document_directory(client: GraphClient) -> List[Dict[str, Any]]:
    global _CACHED_DOCUMENTS
    if _CACHED_DOCUMENTS is not None:
        return _CACHED_DOCUMENTS

    try:
        docs = client.run_read("MATCH (d:Document) RETURN d.id AS did, d.doc_id AS doc_id, d.source AS source")
        _CACHED_DOCUMENTS = [
            {"did": d["did"], "doc_id": d.get("doc_id", ""), "source": d.get("source", "")}
            for d in docs if d.get("did") is not None
        ]
    except Exception as exc:
        logger.debug("Failed loading document directory: %s", exc)
        _CACHED_DOCUMENTS = []

    return _CACHED_DOCUMENTS


def synthesize_deterministic_answer(
    question: str,
    target_facts: List[Dict[str, Any]],
    doc_ids: List[str],
) -> str:
    """
    Deterministic rule-based answer generator that converts graph facts into
    clean, cited natural-language answers without calling any LLM API.
    Used as instant fallback when 429 / quota limit is reached.
    """
    if not target_facts:
        return "No verifiable graph facts match the query target."

    # Group facts by subject
    by_subject: Dict[str, List[Tuple[str, str, str]]] = {}
    for f in target_facts:
        sub = f.get("subject", "").strip() or "Company Knowledge"
        attr = f.get("attribute", "").strip() or "detail"
        val = f.get("value", "").strip()
        doc = f.get("doc_id", "").strip()
        if val:
            by_subject.setdefault(sub, []).append((attr, val, doc))

    sentences = []
    for sub, attrs in by_subject.items():
        attr_phrases = []
        for attr, val, doc in attrs[:3]:
            cit = f" (doc: {doc})" if doc else ""
            if attr.lower() in ("value", "detail", "property", "fact"):
                attr_phrases.append(f"{val}{cit}")
            else:
                attr_phrases.append(f"{attr} is {val}{cit}")
        if attr_phrases:
            sentences.append(f"{sub.capitalize()}: {'; '.join(attr_phrases)}.")

    return " ".join(sentences) if sentences else f"According to verified records: {target_facts[0].get('value', '')}"


def answer_question(
    question: str,
    client: GraphClient,
    force_heuristic: bool = False,
) -> QueryAnswer:
    """
    Executes natural language question against HydraDB graph and generates cited answer or abstention.
    Falls back to deterministic non-AI synthesis on 429 rate limit or when force_heuristic=True.
    """
    global _LLM_QUOTA_EXHAUSTED

    # 1. Extract search keywords from question
    stopwords = {
        "what", "is", "the", "are", "for", "on", "in", "to", "a", "an", "of", "and", "or",
        "how", "why", "which", "does", "do", "did", "from", "with", "about", "that", "this"
    }
    q_lower = question.lower()
    keywords = [
        w.strip().lower()
        for w in question.replace("?", " ").replace(",", " ").replace(".", " ").replace(":", " ").split()
        if len(w) > 2 and w.strip().lower() not in stopwords
    ]

    # 2. Match entities mentioned in the question
    entity_dir = _get_entity_directory(client)
    matched_entity_ids = set()
    matched_entity_names = set()

    for ent in entity_dir:
        name_lower = ent["name"].lower().strip()
        if len(name_lower) > 3 and name_lower in q_lower:
            matched_entity_ids.add(ent["id"])
            matched_entity_names.add(ent["name"])

    # Multi-hop traversal: expand matched Person entities using SAME_AS edges
    expanded_entity_ids = set(matched_entity_ids)
    same_as_cypher = build_same_as_query()
    for eid in matched_entity_ids:
        try:
            aliases = client.run_read(same_as_cypher, {"pid": eid})
            for alias in aliases:
                if alias.get("id") is not None:
                    expanded_entity_ids.add(alias["id"])
        except Exception:
            pass

    # 3. Find candidate documents
    doc_dir = _get_document_directory(client)
    candidate_doc_ids: Set[int] = set()

    # (a) Match docs mentioning resolved entities
    entity_docs_cypher = build_entity_docs_query()
    for eid in expanded_entity_ids:
        try:
            docs_res = client.run_read(entity_docs_cypher, {"eid": eid})
            for d in docs_res:
                if d.get("did") is not None:
                    candidate_doc_ids.add(d["did"])
        except Exception:
            pass

    # (b) Match docs by source or keywords in doc_id
    if not candidate_doc_ids or len(candidate_doc_ids) < 5:
        for d in doc_dir:
            src = str(d.get("source") or "").lower()
            did_str = str(d.get("doc_id") or "").lower()
            if any(kw in src or kw in did_str for kw in keywords):
                candidate_doc_ids.add(d["did"])
            if len(candidate_doc_ids) >= 40:
                break

    # If still empty, sample the first 25 documents
    if not candidate_doc_ids and doc_dir:
        candidate_doc_ids = {d["did"] for d in doc_dir[:25]}

    # 4. Fetch facts from candidate documents using anchored lookups (fast, <20ms)
    doc_facts_cypher = build_doc_facts_query()
    raw_facts: List[Dict[str, Any]] = []

    for did in list(candidate_doc_ids)[:40]:
        try:
            facts_res = client.run_read(doc_facts_cypher, {"did": did})
            for f in facts_res:
                sub = str(f.get("subject") or "").strip()
                attr = str(f.get("attribute") or "").strip()
                val = str(f.get("value") or "").strip()
                doc_id = str(f.get("doc_id") or "").strip()
                trust = f.get("trust_score", 0.5)
                fid = f.get("id")

                if sub or val:
                    raw_facts.append({
                        "id": fid,
                        "subject": sub,
                        "attribute": attr,
                        "value": val,
                        "doc_id": doc_id,
                        "trust_score": float(trust) if trust is not None else 0.5,
                    })
        except Exception as exc:
            logger.debug("Failed fetching facts for doc %s: %s", did, exc)

    # 5. Score and filter facts by keyword relevance
    scored_facts = []
    for f in raw_facts:
        f_text = f"{f['subject']} {f['attribute']} {f['value']}".lower()
        score = sum(1 for kw in keywords if kw in f_text)
        if any(ent_name.lower() in f_text for ent_name in matched_entity_names):
            score += 3
        if score > 0 or not keywords:
            scored_facts.append((score, f))

    # Sort by relevance score descending, then by trust score descending (conflict resolution)
    scored_facts.sort(key=lambda item: (item[0], item[1]["trust_score"]), reverse=True)
    target_facts = [item[1] for item in scored_facts[:20]]

    # 6. Check abstention
    abstain, reason = should_abstain(target_facts)
    if abstain:
        return QueryAnswer(
            answer="I don't know based on the provided company data. " + reason,
            citations=[],
            abstained=True,
        )

    # 7. Collect doc IDs
    doc_ids = list({f["doc_id"] for f in target_facts if f.get("doc_id")})

    # 8. If force_heuristic or LLM quota was already exhausted, use non-AI deterministic synthesis instantly
    if force_heuristic or _LLM_QUOTA_EXHAUSTED:
        det_answer = synthesize_deterministic_answer(question, target_facts, doc_ids)
        return QueryAnswer(
            answer=det_answer,
            citations=doc_ids,
            abstained=False,
        )

    # 9. Format fact summary for LLM
    facts_summary_lines = [
        f"- [{f.get('doc_id', '')}] {f.get('subject', '')} -> {f.get('attribute', '')}: {f.get('value', '')}"
        for f in target_facts
    ]
    facts_summary = "\n".join(facts_summary_lines)

    # 10. LLM Synthesis with circuit-breaker fallback on 429
    prompt = ANSWER_PROMPT.format(question=question, facts_summary=facts_summary)

    try:
        genai_client = genai.Client(api_key=config.get_gemini_api_key())
        response = genai_client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
        )
        answer_text = response.text.strip() if response.text else "Unable to generate answer."
        return QueryAnswer(
            answer=answer_text,
            citations=doc_ids,
            abstained=False,
        )
    except Exception as exc:
        exc_str = str(exc)
        is_rate_limit = "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str or "Quota" in exc_str

        if is_rate_limit:
            _LLM_QUOTA_EXHAUSTED = True
            logger.warning("Gemini 429 / Quota limit reached. Activating circuit breaker: switching all future queries to deterministic non-AI synthesis.")
        else:
            logger.error("LLM synthesis failed (%s). Using deterministic non-AI fallback.", exc)

        det_answer = synthesize_deterministic_answer(question, target_facts, doc_ids)
        return QueryAnswer(
            answer=det_answer,
            citations=doc_ids,
            abstained=False,
        )
