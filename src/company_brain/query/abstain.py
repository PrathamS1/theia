"""
query/abstain.py — Graph-Native Abstention Engine for HydraDB.

Evaluates retrieved fact sets, graph connectivity, and target predicates.
If no traversable path or relevant fact is confirmed in HydraDB,
returns structured abstention ("Not in company knowledge base") with zero citations.
"""

from typing import List, Dict, Any, Tuple, Optional, Set


def should_abstain(
    retrieved_facts: List[Dict[str, Any]],
    graph_connected_docs: Optional[Set[str]] = None,
    missing_target_tokens: Optional[List[str]] = None,
    top_doc_overlap: float = 1.0,
    top_vector_score: float = 1.0,
) -> Tuple[bool, str]:
    """
    Evaluates multi-signal graph grounding for closed-world verification.
    Balances precision on missing facts without sacrificing recall on semantic paraphrases.
    """
    # If dense semantic vector score is strong (>= 0.46), trust the semantic topic match
    if top_vector_score >= 0.46:
        return False, ""

    # Signal B1: Multiple required domain entities/tokens completely absent from entire company corpus
    if missing_target_tokens and len(missing_target_tokens) >= 2 and top_vector_score < 0.40:
        return True, f"Multiple target entities ({', '.join(missing_target_tokens[:2])}) do not exist in company records."

    # Signal B2: A single essential domain term missing AND candidate document cannot ground it
    if missing_target_tokens and len(missing_target_tokens) == 1 and top_vector_score < 0.35:
        return True, f"Target concept ({missing_target_tokens[0]}) is not recorded in company knowledge base."

    # Signal B3: Zero graph facts and zero graph paths with weak match
    if not retrieved_facts and not graph_connected_docs and top_vector_score < 0.28 and top_doc_overlap < 0.10:
        return True, "No traversable path or verifiable facts exist in HydraDB graph."

    return False, ""
