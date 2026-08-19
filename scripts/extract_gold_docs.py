#!/usr/bin/env python3
"""
scripts/extract_gold_docs.py — Fast targeted extraction of the ~812 gold documents.

Scans questions.jsonl and extra_questions.jsonl for all unique expected_doc_ids,
then traverses the 9 source folders in the raw dataset to extract and stage them.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Set, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("extract_gold_docs")

# Raw dataset source locations
RAW_DATASET_DIR = Path("/home/pratham/projects/hydra-brain/data/raw")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "data" / "staged_gold_docs.json"


def get_target_doc_ids() -> Set[str]:
    """Collect all unique expected_doc_ids from questions and extra_questions."""
    doc_ids: Set[str] = set()
    questions_file = PROJECT_ROOT / "data" / "questions" / "questions.jsonl"
    extra_file = PROJECT_ROOT / "data" / "questions" / "extra_questions.jsonl"

    if questions_file.exists():
        with open(questions_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    q = json.loads(line)
                    for did in q.get("expected_doc_ids", []):
                        doc_ids.add(did.strip())

    if extra_file.exists():
        with open(extra_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    q = json.loads(line)
                    for did in q.get("expected_doc_ids", []):
                        doc_ids.add(did.strip())

    logger.info("Found %d unique target gold doc_ids across question sets.", len(doc_ids))
    return doc_ids


def scan_and_extract(target_ids: Set[str]) -> Dict[str, Dict[str, Any]]:
    """Fast scan of the dataset folders using filename dsid prefix matching."""
    extracted: Dict[str, Dict[str, Any]] = {}
    
    if not RAW_DATASET_DIR.exists():
        logger.error("Raw dataset directory not found at %s", RAW_DATASET_DIR)
        return extracted

    sources = ["slack", "gmail", "linear", "google_drive", "hubspot", "fireflies", "github", "jira", "confluence"]

    logger.info("Scanning dataset source directories in %s...", RAW_DATASET_DIR)
    for source in sources:
        source_dir = RAW_DATASET_DIR / source
        if not source_dir.exists():
            continue

        logger.info("  Scanning source: %s ...", source)
        for root, dirs, files in os.walk(source_dir):
            for file_name in files:
                # Filename format: dsid_<hex>__<slug>.txt or dsid_<hex>.txt
                did = file_name.split("__")[0].split(".")[0]
                if did in target_ids and did not in extracted:
                    file_path = Path(root) / file_name
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read()
                    except Exception as e:
                        logger.warning("Could not read %s: %s", file_path, e)
                        text = ""

                    title = file_name.replace(".txt", "").replace(".md", "")
                    if "__" in title:
                        title = title.split("__", 1)[1].replace("-", " ")

                    extracted[did] = {
                        "doc_id": did,
                        "source": source.lower(),
                        "title": title,
                        "file_name": file_name,
                        "file_path": str(file_path),
                        "text": text,
                    }

    logger.info("Successfully extracted %d / %d target documents.", len(extracted), len(target_ids))
    return extracted


def main():
    target_ids = get_target_doc_ids()
    extracted = scan_and_extract(target_ids)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(extracted, f, indent=2)

    logger.info("Saved %d staged gold documents to %s", len(extracted), OUTPUT_FILE)


if __name__ == "__main__":
    main()
