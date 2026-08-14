"""
ingest/sources/loader_base.py — Base loader helper for iterating dataset JSON/JSONL files.
"""

import json
import zipfile
from pathlib import Path
from typing import Generator, Dict, Any


def iter_documents_from_dir(dir_path: Path) -> Generator[Dict[str, Any], None, None]:
    """
    Iterates over JSON, JSONL, or TXT document files in a directory or extracted zip slice.
    Yields normalized dict: {'doc_id': str, 'source': str, 'created_at': str, 'text': str}
    """
    if not dir_path.exists():
        return

    for file_path in dir_path.rglob("*"):
        if file_path.is_file():
            if file_path.suffix == ".zip":
                try:
                    with zipfile.ZipFile(file_path, "r") as z:
                        for name in z.namelist():
                            if name.endswith("/"):
                                continue
                            try:
                                with z.open(name) as f:
                                    raw_content = f.read().decode("utf-8", errors="ignore")
                                    if name.endswith(".json"):
                                        data = json.loads(raw_content)
                                        if isinstance(data, dict):
                                            yield _normalize_doc(data, file_path, name)
                                        elif isinstance(data, list):
                                            for item in data:
                                                if isinstance(item, dict):
                                                    yield _normalize_doc(item, file_path, name)
                                    elif name.endswith(".jsonl"):
                                        for line in raw_content.splitlines():
                                            if line.strip():
                                                yield _normalize_doc(json.loads(line), file_path, name)
                                    else:
                                        # Raw text/markdown file inside zip
                                        yield _normalize_raw_text(raw_content, file_path, name)
                            except Exception:
                                pass
                except Exception:
                    pass
            elif file_path.suffix == ".json":
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            yield _normalize_doc(data, file_path)
                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict):
                                    yield _normalize_doc(item, file_path)
                except Exception:
                    pass
            elif file_path.suffix == ".jsonl":
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if line.strip():
                                data = json.loads(line)
                                yield _normalize_doc(data, file_path)
                except Exception:
                    pass
            elif file_path.suffix in [".txt", ".md", ".html"]:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                        yield _normalize_raw_text(text, file_path)
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
