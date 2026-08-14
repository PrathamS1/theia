"""
query/engine.py — Natural Language Query Engine built on HydraDB.

Pipeline:
1. Natural language question -> Keyword/entity extraction via Gemini
2. Graph retrieval over HydraDB (Facts, Entities, Provenance, Conflict resolution)
3. Abstention check (if no graph facts exist -> "Not in the data")
4. LLM synthesis with strict citations
"""

import logging
from typing import Dict, Any, List
from google import genai
from pydantic import BaseModel, Field

from company_brain import config
from company_brain.graph.client import GraphClient
from company_brain.query.cypher_templates import build_fact_query
from company_brain.query.abstain import should_abstain

logger = logging.getLogger(__name__)


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


def answer_question(question: str, client: GraphClient) -> QueryAnswer:
    """
    Executes natural language question against HydraDB graph and generates cited answer or abstention.
    """
    genai_client = genai.Client(api_key=config.get_gemini_api_key())

    # 1. Extract search terms from question
    keywords = [w.strip() for w in question.replace("?", "").replace(",", "").split() if len(w) > 3]

    # 2. Retrieve facts from HydraDB
    cypher = build_fact_query(keywords[:5])
    try:
        facts = client.run(cypher)
    except Exception as exc:
        logger.warning("Fact retrieval query failed: %s", exc)
        facts = []

    # 3. Check abstention
    abstain, reason = should_abstain(facts)
    if abstain:
        return QueryAnswer(
            answer="I don't know based on the provided company data. " + reason,
            citations=[],
            abstained=True,
        )

    # 4. Format fact summary
    facts_summary_lines = []
    doc_ids = set()
    for f in facts:
        sub = f.get("f.subject", "")
        attr = f.get("f.attribute", "")
        val = f.get("f.value", "")
        doc = f.get("f.doc_id", "")
        if doc:
            doc_ids.add(str(doc))
        facts_summary_lines.append(f"- [{doc}] {sub} -> {attr}: {val}")

    facts_summary = "\n".join(facts_summary_lines)

    # 5. LLM Synthesis
    prompt = ANSWER_PROMPT.format(question=question, facts_summary=facts_summary)
    try:
        response = genai_client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
        )
        answer_text = response.text.strip() if response.text else "Unable to generate answer."
        return QueryAnswer(
            answer=answer_text,
            citations=list(doc_ids),
            abstained=False,
        )
    except Exception as exc:
        logger.error("LLM answer generation failed: %s", exc)
        return QueryAnswer(
            answer="Error processing question.",
            citations=[],
            abstained=True,
        )
