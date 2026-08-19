"""
indexing/chunker.py — Recursive Document & Passage Chunker for Full-Corpus Indexing.

Splits long technical documents, Slack threads, Confluence runbooks, and PRs
into semantically cohesive passages while preserving parent document provenance.
"""

import re
from typing import List, Dict, Any, Optional


class DocumentChunker:
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_document(self, doc_id: str, text: str, meta: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Splits a document text into overlapping passages respecting natural boundaries.
        Returns a list of structured chunk dicts.
        """
        clean_text = (text or "").strip()
        if not clean_text:
            return []

        # If document is short enough, return as single chunk
        if len(clean_text) <= self.chunk_size:
            return [{
                "chunk_id": f"{doc_id}_0",
                "doc_id": doc_id,
                "chunk_index": 0,
                "text": clean_text,
                "char_length": len(clean_text),
                "meta": meta or {},
            }]

        chunks: List[Dict[str, Any]] = []
        # Recursive splitting on natural structural boundaries
        paragraphs = re.split(r"\n\s*\n", clean_text)
        current_chunk = ""
        chunk_idx = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If a single paragraph is longer than chunk_size, split by sentences
            if len(para) > self.chunk_size:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                    if len(current_chunk) + len(sent) + 1 > self.chunk_size and len(current_chunk) >= self.min_chunk_size:
                        chunks.append({
                            "chunk_id": f"{doc_id}_{chunk_idx}",
                            "doc_id": doc_id,
                            "chunk_index": chunk_idx,
                            "text": current_chunk.strip(),
                            "char_length": len(current_chunk.strip()),
                            "meta": meta or {},
                        })
                        chunk_idx += 1
                        # Retain overlap from end of current chunk
                        current_chunk = current_chunk[-self.chunk_overlap :] + " " + sent if self.chunk_overlap > 0 else sent
                    else:
                        current_chunk = (current_chunk + " " + sent).strip()
            else:
                if len(current_chunk) + len(para) + 2 > self.chunk_size and len(current_chunk) >= self.min_chunk_size:
                    chunks.append({
                        "chunk_id": f"{doc_id}_{chunk_idx}",
                        "doc_id": doc_id,
                        "chunk_index": chunk_idx,
                        "text": current_chunk.strip(),
                        "char_length": len(current_chunk.strip()),
                        "meta": meta or {},
                    })
                    chunk_idx += 1
                    current_chunk = current_chunk[-self.chunk_overlap :] + "\n\n" + para if self.chunk_overlap > 0 else para
                else:
                    current_chunk = (current_chunk + "\n\n" + para).strip() if current_chunk else para

        # Flush trailing chunk
        if current_chunk.strip() and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append({
                "chunk_id": f"{doc_id}_{chunk_idx}",
                "doc_id": doc_id,
                "chunk_index": chunk_idx,
                "text": current_chunk.strip(),
                "char_length": len(current_chunk.strip()),
                "meta": meta or {},
            })

        return chunks

    def chunk_all_documents(self, staged_docs: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunks all staged documents in the corpus.
        """
        all_chunks: List[Dict[str, Any]] = []
        for doc_id, dinfo in staged_docs.items():
            meta = {
                "source": dinfo.get("source", "unknown"),
                "title": dinfo.get("title", ""),
                "author": dinfo.get("author", ""),
                "created_at": dinfo.get("created_at", ""),
            }
            doc_chunks = self.chunk_document(doc_id, dinfo.get("text") or dinfo.get("body", ""), meta)
            all_chunks.extend(doc_chunks)
        return all_chunks
