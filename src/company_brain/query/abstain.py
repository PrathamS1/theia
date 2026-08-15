"""
query/abstain.py — Abstention engine.

Evaluates retrieved fact sets and entity paths. If no path or relevant fact is found,
returns structured abstention ("I don't know" / "Not in the data") to prevent hallucination.
"""

from typing import List, Dict, Any, Tuple


def should_abstain(retrieved_facts: List[Dict[str, Any]], min_facts: int = 1) -> Tuple[bool, str]:
    """
    Determines if the query engine should abstain from answering.
    Returns tuple: (should_abstain: bool, abstention_reason: str)
    """
    if not retrieved_facts or len(retrieved_facts) < min_facts:
        return True, "Information requested is not found in the company data graph."

    # Check if facts contain any non-empty subject and value
    has_valid = any(f.get("subject") or f.get("f.subject") or f.get("value") or f.get("f.value") for f in retrieved_facts)
    if not has_valid:
        return True, "No verifiable graph facts match the query target."


    return False, ""
