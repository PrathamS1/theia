"""
integrations/normalizers/drive_normalizer.py — Google Drive Data Normalizer.

Transforms raw Google Drive file metadata and exported text content
obtained from Composio's Google Drive Toolkit into canonical StagedDocument
dictionaries for chunking, vector embedding, and HydraDB knowledge graph insertion.

Only text-exportable file types are indexed (Google Docs, Sheets, Slides, plain text, PDFs).
Binary files (images, videos, audio) are skipped entirely as their content cannot be meaningfully
indexed for semantic search.
"""

import hashlib
import logging
from typing import Dict, Any, List, Optional

from company_brain.integrations.normalizers.base_normalizer import BaseNormalizer, create_staged_document

logger = logging.getLogger("company_brain.integrations.drive_normalizer")


# MIME types we can meaningfully index (exportable to plain text)
_INDEXABLE_MIME_TYPES = {
    # Google Workspace exports
    "application/vnd.google-apps.document",       # Google Docs → text/plain
    "application/vnd.google-apps.spreadsheet",    # Google Sheets → text/csv
    "application/vnd.google-apps.presentation",   # Google Slides → text/plain
    # Native text formats
    "text/plain",
    "text/markdown",
    "text/csv",
    "text/html",
    "text/xml",
    # PDF
    "application/pdf",
    # Common document formats
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",        # .xlsx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation", # .pptx
}

# Friendly labels for Google Workspace types
_MIME_LABELS = {
    "application/vnd.google-apps.document": "Google Doc",
    "application/vnd.google-apps.spreadsheet": "Google Sheet",
    "application/vnd.google-apps.presentation": "Google Slides",
    "application/pdf": "PDF",
    "text/plain": "Text File",
    "text/markdown": "Markdown File",
}


class DriveNormalizer(BaseNormalizer):
    """
    Normalizes raw Google Drive file metadata and exported text content
    into canonical StagedDocument records.
    """

    def __init__(self, workspace_id: Optional[str] = None):
        self.workspace_id = workspace_id

    @property
    def source_name(self) -> str:
        return "googledrive"

    def normalize(self, raw_payload: Any) -> List[Dict[str, Any]]:
        """Generic entrypoint — not used directly; use normalize_file() instead."""
        docs = []
        if isinstance(raw_payload, list):
            for item in raw_payload:
                if isinstance(item, dict):
                    doc = self.normalize_file(item)
                    if doc:
                        docs.append(doc)
        elif isinstance(raw_payload, dict):
            doc = self.normalize_file(raw_payload)
            if doc:
                docs.append(doc)
        return docs

    @staticmethod
    def is_indexable(mime_type: str) -> bool:
        """Returns True if this file type can be meaningfully indexed for semantic search."""
        if not mime_type:
            return False
        if mime_type in _INDEXABLE_MIME_TYPES:
            return True
        if mime_type.startswith("text/"):
            return True
        return False

    def normalize_file(
        self,
        file_data: Dict[str, Any],
        content: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Normalizes a Google Drive file into a StagedDocument.

        Args:
            file_data: File metadata dict from GOOGLEDRIVE_LIST_FILES or GOOGLEDRIVE_GET_FILE.
            content: Optional pre-fetched text content of the file.
                     If None, metadata-only document is created.

        Returns:
            StagedDocument dict, or None if the file is not indexable.
        """
        file_id = str(file_data.get("id") or "")
        name = str(file_data.get("name") or file_data.get("title") or "Untitled File")
        mime_type = str(file_data.get("mimeType") or "")
        modified_time = str(file_data.get("modifiedTime") or file_data.get("createdTime") or "")
        web_view_link = str(file_data.get("webViewLink") or file_data.get("webContentLink") or "")

        # Get owner/author
        owners = file_data.get("owners") or []
        author = ""
        if owners and isinstance(owners[0], dict):
            author = str(owners[0].get("displayName") or owners[0].get("emailAddress") or "")
        if not author:
            last_mod = file_data.get("lastModifyingUser") or {}
            if isinstance(last_mod, dict):
                author = str(last_mod.get("displayName") or last_mod.get("emailAddress") or "")
        if not author:
            author = "google_drive_user"

        if not self.is_indexable(mime_type):
            logger.debug("Skipping non-indexable file: %s (mime: %s)", name, mime_type)
            return None

        mime_label = _MIME_LABELS.get(mime_type, mime_type.split("/")[-1] if "/" in mime_type else mime_type)

        # Build doc_id from stable file_id
        if file_id:
            doc_id = f"gdrive_{hashlib.sha256(file_id.encode()).hexdigest()[:24]}"
        else:
            doc_id = f"gdrive_{hashlib.sha256(name.encode()).hexdigest()[:24]}"

        # Build text body: exported content + file metadata context
        text_parts = [f"File: {name}", f"Type: {mime_label}"]
        if content and content.strip():
            text_parts.append(f"\n{content.strip()}")
        else:
            # Metadata-only fallback for when content fetch fails
            description = str(file_data.get("description") or "")
            if description:
                text_parts.append(f"Description: {description}")

        formatted_text = "\n".join(text_parts).strip()
        if not formatted_text:
            return None

        doc = create_staged_document(
            doc_id=doc_id,
            source="googledrive",
            author=author,
            created_at=modified_time,
            text=formatted_text,
            title=f"{mime_label}: {name}",
            url=web_view_link,
            workspace_id=self.workspace_id,
            metadata={
                "file_id": file_id,
                "name": name,
                "mime_type": mime_type,
                "mime_label": mime_label,
                "parents": file_data.get("parents", []),
                "shared": file_data.get("shared", False),
            },
        )
        return doc

    def normalize_files_batch(
        self,
        files_with_content: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Normalizes a batch of (file_data, content) tuples.
        Each dict should have keys: 'file_data' and optionally 'content'.
        """
        docs = []
        for item in files_with_content:
            if isinstance(item, dict) and "file_data" in item:
                doc = self.normalize_file(
                    file_data=item["file_data"],
                    content=item.get("content"),
                )
            elif isinstance(item, dict):
                doc = self.normalize_file(file_data=item)
            else:
                continue
            if doc:
                docs.append(doc)
        return docs
