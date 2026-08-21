#!/usr/bin/env python3
"""
scripts/llm_extract_gold.py — LLM fact extraction for the 812 benchmark documents.

Why only the gold documents: they are the only ones the benchmark ever queries, so
that is where extraction quality is measured. Running the LLM across all 25,812
documents is not viable on the free tier (~5 requests/minute).

Why this exists at all: after the tautological `(X, "metric_name", X)` facts were
removed, the sole remaining extractor is one limit/threshold regex. Measured over
300 gold documents, **85% had zero facts** and every fact that did exist used the
same `limit_or_target` attribute. The graph was structurally sound but said almost
nothing. Gemini measured 8.1 facts/document with real attribute names.

The run is resumable by design. Results are cached to disk after every batch, so a
quota stall, a 503 storm or a Ctrl-C never loses completed work -- re-run the script
and it picks up only the documents still missing.

Usage:
    python scripts/llm_extract_gold.py                 # extract (resumable)
    python scripts/llm_extract_gold.py --write         # extract, then write to HydraDB
    python scripts/llm_extract_gold.py --write-only    # write an existing cache, no API calls
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from company_brain.extraction.llm_batch import extract_batched
from company_brain.extraction.prompts import DocumentExtractionResult, ExtractedEntity, ExtractedFact
from company_brain.graph.client import GraphClient
from company_brain.graph.loader import GraphLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
for noisy in ("httpx", "google_genai", "google.genai", "httpcore"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
logger = logging.getLogger("llm_extract_gold")

GOLD_FILE = PROJECT_ROOT / "data" / "staged_gold_docs.json"
CACHE_FILE = PROJECT_ROOT / "data" / "llm_facts_gold.json"


def load_cache() -> Dict[str, Any]:
    if CACHE_FILE.exists():
        try:
            return json.load(open(CACHE_FILE, encoding="utf-8"))
        except Exception as exc:
            logger.warning("Cache unreadable (%s); starting fresh.", str(exc)[:100])
    return {}


def save_cache(cache: Dict[str, Any]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=1)
    tmp.replace(CACHE_FILE)  # atomic: a crash mid-write cannot corrupt the cache


def extract(gold: Dict[str, Any], batch_size: int, rpm: int, concurrency: int) -> Dict[str, Any]:
    cache = load_cache()
    todo = [(k, v.get("source", ""), v.get("text", "")) for k, v in gold.items() if k not in cache]
    logger.info("Gold documents: %d | cached: %d | to extract: %d", len(gold), len(cache), len(todo))
    if not todo:
        logger.info("Nothing to do — cache already covers every gold document.")
        return cache

    # Chunk the work so the cache is flushed regularly rather than only at the end.
    FLUSH_EVERY = 40
    for start in range(0, len(todo), FLUSH_EVERY):
        window = todo[start:start + FLUSH_EVERY]
        results, stats = extract_batched(
            window, batch_size=batch_size, requests_per_minute=rpm, concurrency=concurrency
        )
        for doc_id, res in results.items():
            cache[doc_id] = {
                "entities": [e.model_dump() for e in res.entities],
                "facts": [f.model_dump() for f in res.facts],
            }
        save_cache(cache)
        done = len(cache)
        logger.info(
            "cached %d/%d gold docs (+%d this window) | %s",
            done, len(gold), len(results), stats.as_dict(),
        )
    return cache


def write_to_graph(gold: Dict[str, Any], cache: Dict[str, Any]) -> None:
    """Replace heuristic facts with LLM facts for every cached gold document."""
    client = GraphClient()
    loader = GraphLoader(client)
    replaced = skipped = failed = 0
    t0 = time.time()

    for i, (doc_id, payload) in enumerate(cache.items(), 1):
        doc = gold.get(doc_id)
        if not doc:
            continue
        facts = payload.get("facts") or []
        if not facts:
            skipped += 1
            continue

        # Drop the document's existing facts first, so this is a replacement rather
        # than an accumulation. Anchored per-document: unanchored deletes exceed the
        # 30s statement timeout at this graph size.
        try:
            client.run_write(
                "MATCH (d:Document {doc_id: $did})-[:HAS_FACT]->(f:Fact) DETACH DELETE f",
                {"did": doc_id},
            )
        except Exception as exc:
            logger.debug("fact delete failed for %s: %s", doc_id, str(exc)[:90])

        extraction = DocumentExtractionResult(
            entities=[ExtractedEntity(**e) for e in (payload.get("entities") or [])],
            facts=[ExtractedFact(**f) for f in facts],
        )
        try:
            loader.load_document(
                doc_id=doc_id,
                source=doc.get("source", ""),
                title=doc.get("title", doc_id),
                created_at=doc.get("created_at") or "",
                text_snippet=(doc.get("text") or "")[:400],
                extraction=extraction,
            )
            replaced += 1
        except Exception as exc:
            failed += 1
            logger.debug("write failed for %s: %s", doc_id, str(exc)[:90])

        if i % 100 == 0:
            logger.info("  %d/%d written (%.0fs)", i, len(cache), time.time() - t0)

    logger.info("=" * 60)
    logger.info("Graph write complete in %.0fs", time.time() - t0)
    logger.info("  documents replaced : %d", replaced)
    logger.info("  no facts (skipped) : %d", skipped)
    logger.info("  failed             : %d", failed)


def main() -> None:
    ap = argparse.ArgumentParser(description="LLM fact extraction over the gold benchmark corpus.")
    ap.add_argument("--batch-size", type=int, default=8, help="Documents per request (default 8)")
    ap.add_argument("--rpm", type=int, default=5, help="Requests/minute ceiling (free tier is 5)")
    ap.add_argument("--concurrency", type=int, default=2,
                    help="Batches in flight. Keep low: retries also consume the quota, so high "
                         "concurrency turns a 503 burst into a death spiral (measured).")
    ap.add_argument("--write", action="store_true", help="Write results to HydraDB after extracting")
    ap.add_argument("--write-only", action="store_true", help="Write the existing cache; no API calls")
    args = ap.parse_args()

    gold = json.load(open(GOLD_FILE, encoding="utf-8"))

    if args.write_only:
        cache = load_cache()
        if not cache:
            logger.error("Cache is empty — run extraction first.")
            sys.exit(1)
        write_to_graph(gold, cache)
        return

    cache = extract(gold, args.batch_size, args.rpm, args.concurrency)
    covered = sum(1 for k in gold if k in cache)
    with_facts = sum(1 for k in gold if cache.get(k, {}).get("facts"))
    total_facts = sum(len(cache.get(k, {}).get("facts") or []) for k in gold)
    logger.info("=" * 60)
    logger.info("Coverage: %d/%d gold docs cached", covered, len(gold))
    logger.info("  with >=1 fact : %d (%.0f%%)", with_facts, 100 * with_facts / max(covered, 1))
    logger.info("  total facts   : %d (%.1f/doc)", total_facts, total_facts / max(covered, 1))

    if args.write:
        write_to_graph(gold, cache)


if __name__ == "__main__":
    main()
