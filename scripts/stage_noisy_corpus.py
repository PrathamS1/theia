#!/usr/bin/env python3
"""
scripts/stage_noisy_corpus.py — Stage a realistic, noisy corpus.

`extract_gold_docs.py` stages exactly the documents named in the question sets'
`expected_doc_ids`. That is reproducible and fast, but it means 100% of the index
is a known answer document: there are no distractors, so retrieval is measured
without a haystack.

This script stages the same gold documents *plus* N randomly sampled non-gold
documents from the same nine sources, so retrieval is measured against real
enterprise noise — misfiled documents, near-duplicates and contradictions.

Writes data/staged_noisy_docs.json. Leaves staged_gold_docs.json untouched so
both corpora stay reproducible and results can be reported side by side.

Usage:
    python scripts/stage_noisy_corpus.py --distractors 25000
    python scripts/stage_noisy_corpus.py --distractors 50000 --seed 42
    python scripts/stage_noisy_corpus.py --raw-dir /path/to/data/raw
"""

import argparse
import json
import logging
import os
import random
import sys
from pathlib import Path
from typing import Dict, Set, Any, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stage_noisy_corpus")

SOURCES = [
    "slack", "gmail", "linear", "google_drive", "hubspot",
    "fireflies", "github", "jira", "confluence",
]


def get_target_doc_ids() -> Set[str]:
    """All unique expected_doc_ids across questions.jsonl and extra_questions.jsonl."""
    doc_ids: Set[str] = set()
    for name in ("questions.jsonl", "extra_questions.jsonl"):
        path = PROJECT_ROOT / "data" / "questions" / name
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    for did in json.loads(line).get("expected_doc_ids", []):
                        doc_ids.add(did.strip())
    logger.info("Gold target doc_ids: %d", len(doc_ids))
    return doc_ids


def _doc_id_from_filename(file_name: str) -> str:
    # dsid_<hex>__<slug>.txt  or  dsid_<hex>.txt
    return file_name.split("__")[0].split(".")[0]


def _read_doc(file_path: Path, did: str, source: str) -> Dict[str, Any]:
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        logger.debug("Could not read %s: %s", file_path, exc)
        text = ""
    title = file_path.name.replace(".txt", "").replace(".md", "")
    if "__" in title:
        title = title.split("__", 1)[1].replace("-", " ")
    return {
        "doc_id": did,
        "source": source.lower(),
        "title": title,
        "file_name": file_path.name,
        "file_path": str(file_path),
        "text": text,
    }


def scan(raw_dir: Path, target_ids: Set[str]) -> Tuple[Dict[str, Dict[str, Any]], List[Tuple[Path, str, str]]]:
    """Single pass: collect gold docs eagerly, and index non-gold paths for sampling."""
    gold: Dict[str, Dict[str, Any]] = {}
    non_gold: List[Tuple[Path, str, str]] = []  # (path, doc_id, source)

    for source in SOURCES:
        source_dir = raw_dir / source
        if not source_dir.exists():
            logger.warning("Missing source dir (skipping): %s", source_dir)
            continue
        count = 0
        for root, _dirs, files in os.walk(source_dir):
            for file_name in files:
                if not file_name.startswith("dsid_"):
                    continue
                did = _doc_id_from_filename(file_name)
                path = Path(root) / file_name
                if did in target_ids:
                    if did not in gold:
                        gold[did] = _read_doc(path, did, source)
                else:
                    non_gold.append((path, did, source))
                count += 1
        logger.info("  %-14s scanned %d files", source, count)

    logger.info("Gold found: %d / %d · non-gold available: %d",
                len(gold), len(target_ids), len(non_gold))
    return gold, non_gold


def main() -> None:
    ap = argparse.ArgumentParser(description="Stage a noisy corpus (gold + sampled distractors).")
    ap.add_argument("--distractors", type=int, default=25000,
                    help="Number of non-gold documents to sample (default 25000)")
    ap.add_argument("--seed", type=int, default=1337, help="Random seed (default 1337)")
    ap.add_argument("--raw-dir", type=str, default=os.getenv("RAW_DATASET_DIR", "data/raw"),
                    help="Raw dataset root (default data/raw, or $RAW_DATASET_DIR)")
    ap.add_argument("--output", type=str, default="data/staged_noisy_docs.json")
    args = ap.parse_args()

    raw_dir = Path(args.raw_dir)
    if not raw_dir.is_absolute():
        raw_dir = PROJECT_ROOT / raw_dir
    if not raw_dir.exists():
        logger.error("Raw dataset dir not found: %s — run scripts/download_dataset.sh --all first", raw_dir)
        sys.exit(1)

    target_ids = get_target_doc_ids()
    gold, non_gold = scan(raw_dir, target_ids)

    if not gold:
        logger.error("No gold documents found under %s — wrong --raw-dir?", raw_dir)
        sys.exit(1)

    rng = random.Random(args.seed)
    n = min(args.distractors, len(non_gold))
    if n < args.distractors:
        logger.warning("Only %d non-gold docs available (asked for %d)", n, args.distractors)
    sampled = rng.sample(non_gold, n) if n else []

    corpus = dict(gold)
    for path, did, source in sampled:
        if did not in corpus:
            corpus[did] = _read_doc(path, did, source)

    out = Path(args.output)
    if not out.is_absolute():
        out = PROJECT_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(corpus, f, indent=2)

    n_gold = len(gold)
    n_total = len(corpus)
    pct = 100.0 * (n_total - n_gold) / max(n_total, 1)
    logger.info("=" * 66)
    logger.info("Staged %d documents -> %s", n_total, out)
    logger.info("  gold        : %d", n_gold)
    logger.info("  distractors : %d (%.1f%% of corpus)", n_total - n_gold, pct)
    logger.info("  seed        : %d (reproducible)", args.seed)
    logger.info("=" * 66)


if __name__ == "__main__":
    main()
