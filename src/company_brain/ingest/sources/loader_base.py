"""
ingest/sources/loader_base.py — Base loader helper for iterating dataset JSON/JSONL files.
"""

import os
import json
import zipfile
from pathlib import Path
from typing import Generator, Dict, Any


def iter_documents_from_dir(dir_path: Path, max_docs: int = 0) -> Generator[Dict[str, Any], None, None]:
    """
    Iterates over JSON, JSONL, or TXT document files in a directory or extracted zip slice.
    Yields normalized dict: {'doc_id': str, 'source': str, 'created_at': str, 'text': str}
    Stops immediately when max_docs is reached (if max_docs > 0).
    """
    if not dir_path.exists():
        return

    dir_str = str(dir_path)
    seen_doc_ids = set()

    unzipped_files = []
    zip_files = []

    for root, _, files in os.walk(dir_str):
        for file in files:
            full_path = Path(root) / file
            if file.endswith(".zip"):
                zip_files.append(full_path)
            elif file.endswith((".json", ".jsonl", ".txt", ".md", ".html")):
                unzipped_files.append(full_path)

    # Prefer reading unzipped files directly to eliminate 1.2 GB zip archive parsing overhead
    files_to_process = unzipped_files if unzipped_files else zip_files

    for file_path in files_to_process:
        if max_docs > 0 and len(seen_doc_ids) >= max_docs:
            break

        ext = file_path.suffix.lower()
        if ext == ".zip":
            try:
                with zipfile.ZipFile(file_path, "r") as z:
                    for name in z.namelist():
                        if max_docs > 0 and len(seen_doc_ids) >= max_docs:
                            break
                        if name.endswith("/"):
                            continue
                        try:
                            with z.open(name) as f:
                                raw_content = f.read().decode("utf-8", errors="ignore")
                                if name.endswith(".json"):
                                    data = json.loads(raw_content)
                                    if isinstance(data, dict):
                                        doc = _normalize_doc(data, file_path, name)
                                        if doc["doc_id"] not in seen_doc_ids:
                                            seen_doc_ids.add(doc["doc_id"])
                                            yield doc
                                    elif isinstance(data, list):
                                        for item in data:
                                            if max_docs > 0 and len(seen_doc_ids) >= max_docs:
                                                break
                                            if isinstance(item, dict):
                                                doc = _normalize_doc(item, file_path, name)
                                                if doc["doc_id"] not in seen_doc_ids:
                                                    seen_doc_ids.add(doc["doc_id"])
                                                    yield doc
                                elif name.endswith(".jsonl"):
                                    for line in raw_content.splitlines():
                                        if max_docs > 0 and len(seen_doc_ids) >= max_docs:
                                            break
                                        if line.strip():
                                            doc = _normalize_doc(json.loads(line), file_path, name)
                                            if doc["doc_id"] not in seen_doc_ids:
                                                seen_doc_ids.add(doc["doc_id"])
                                                yield doc
                                else:
                                    doc = _normalize_raw_text(raw_content, file_path, name)
                                    if doc["doc_id"] not in seen_doc_ids:
                                        seen_doc_ids.add(doc["doc_id"])
                                        yield doc
                        except Exception:
                            pass
            except Exception:
                pass
        elif ext == ".json":
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        doc = _normalize_doc(data, file_path)
                        if doc["doc_id"] not in seen_doc_ids:
                            seen_doc_ids.add(doc["doc_id"])
                            yield doc
                    elif isinstance(data, list):
                        for item in data:
                            if max_docs > 0 and len(seen_doc_ids) >= max_docs:
                                break
                            if isinstance(item, dict):
                                doc = _normalize_doc(item, file_path)
                                if doc["doc_id"] not in seen_doc_ids:
                                    seen_doc_ids.add(doc["doc_id"])
                                    yield doc
            except Exception:
                pass
        elif ext == ".jsonl":
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if max_docs > 0 and len(seen_doc_ids) >= max_docs:
                            break
                        if line.strip():
                            doc = _normalize_doc(json.loads(line), file_path)
                            if doc["doc_id"] not in seen_doc_ids:
                                seen_doc_ids.add(doc["doc_id"])
                                yield doc
            except Exception:
                pass
        elif ext in [".txt", ".md", ".html"]:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                    doc = _normalize_raw_text(text, file_path)
                    if doc["doc_id"] not in seen_doc_ids:
                        seen_doc_ids.add(doc["doc_id"])
                        yield doc
            except Exception:
                pass


def _normalize_doc(data: Dict[str, Any], file_path: Path, zip_member_name: str = "") -> Dict[str, Any]:
    doc_id = data.get("doc_id") or data.get("id") or (Path(zip_member_name).stem if zip_member_name else file_path.stem)
    source = data.get("source") or data.get("source_type") or file_path.parent.name
    created_at = data.get("created_at") or data.get("timestamp") or data.get("date") or "2026-01-01T00:00:00Z"
    text = data.get("text") or data.get("content") or data.get("body") or json.dumps(data)
    
    return {
        "doc_id": str(doc_id),
        "source": str(source).lower(),
        "created_at": str(created_at),
        "text": str(text),
    }


def _normalize_raw_text(text: str, file_path: Path, zip_member_name: str = "") -> Dict[str, Any]:
    doc_id = Path(zip_member_name).stem if zip_member_name else file_path.stem
    source = file_path.parent.name or "unknown"
    return {
        "doc_id": str(doc_id),
        "source": str(source).lower(),
        "created_at": "2026-01-01T00:00:00Z",
        "text": text,
    }
