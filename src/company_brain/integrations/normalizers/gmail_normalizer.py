"""
integrations/normalizers/gmail_normalizer.py — Gmail Data Normalizer.

Transforms raw Gmail API message payloads obtained from Composio's Gmail Toolkit
into canonical StagedDocument dictionaries for chunking, vector embedding,
and HydraDB knowledge graph insertion.

Gmail messages are base64url-encoded. This normalizer decodes body parts,
strips HTML to plain text, and extracts Subject/From/Date headers.
"""

import base64
import hashlib
import logging
import re
from typing import Dict, Any, List, Optional

from company_brain.integrations.normalizers.base_normalizer import BaseNormalizer, create_staged_document

logger = logging.getLogger("company_brain.integrations.gmail_normalizer")


def _strip_html(html: str) -> str:
    """
    Strips HTML tags from a string and collapses whitespace to plain text.
    Lightweight — no external dependency required.
    """
    # Remove style/script blocks entirely
    text = re.sub(r"<(style|script)[^>]*>.*?</(style|script)>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Replace block-level tags with newlines
    text = re.sub(r"<(br|p|div|tr|li|h[1-6])[^>]*>", "\n", text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode common HTML entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">") \
               .replace("&nbsp;", " ").replace("&quot;", '"').replace("&#39;", "'")
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _decode_base64url(data: str) -> str:
    """
    Decodes a base64url-encoded string to UTF-8 text.
    Silently returns empty string on errors.
    """
    if not data:
        return ""
    try:
        padded = data + "=" * (4 - len(data) % 4)
        decoded_bytes = base64.urlsafe_b64decode(padded)
        return decoded_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        logger.debug("base64url decode failed: %s", e)
        return ""


def _extract_body_from_payload(payload: Dict[str, Any]) -> str:
    """
    Recursively extracts plain text body from a Gmail message payload.
    Prefers text/plain parts over text/html.
    """
    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})
    data = body.get("data", "") if isinstance(body, dict) else ""

    # Direct single-part message
    if mime_type == "text/plain" and data:
        return _decode_base64url(data)
    if mime_type == "text/html" and data:
        return _strip_html(_decode_base64url(data))

    # Multipart — recurse into parts, preferring plain text
    parts = payload.get("parts", [])
    plain_text = ""
    html_text = ""
    for part in parts:
        if not isinstance(part, dict):
            continue
        part_mime = part.get("mimeType", "")
        part_body = part.get("body", {})
        part_data = part_body.get("data", "") if isinstance(part_body, dict) else ""
        if part_mime == "text/plain" and part_data:
            plain_text = _decode_base64url(part_data)
        elif part_mime == "text/html" and part_data:
            html_text = _strip_html(_decode_base64url(part_data))
        elif part_mime.startswith("multipart/"):
            # Nested multipart
            nested = _extract_body_from_payload(part)
            if nested and not plain_text:
                plain_text = nested

    return plain_text or html_text


class GmailNormalizer(BaseNormalizer):
    """
    Normalizes raw Gmail API message payloads into canonical StagedDocument records.
    """

    def __init__(self, workspace_id: Optional[str] = None):
        self.workspace_id = workspace_id

    @property
    def source_name(self) -> str:
        return "gmail"

    def normalize(self, raw_payload: Any) -> List[Dict[str, Any]]:
        """Generic entrypoint: accepts a list of messages or a single message dict."""
        docs = []
        if isinstance(raw_payload, list):
            for item in raw_payload:
                doc = self.normalize_email(item)
                if doc:
                    docs.append(doc)
        elif isinstance(raw_payload, dict):
            doc = self.normalize_email(raw_payload)
            if doc:
                docs.append(doc)
        return docs

    def normalize_email(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalizes a full Gmail message (as returned by GMAIL_GET_MESSAGE) into a StagedDocument.
        Returns None if the email has no readable content.
        """
        message_id = str(message_data.get("id") or "")
        thread_id = str(message_data.get("threadId") or "")

        # Extract headers
        payload = message_data.get("payload") or {}
        headers = payload.get("headers") or []
        headers_map: Dict[str, str] = {}
        for h in headers:
            if isinstance(h, dict):
                name = str(h.get("name") or "").lower()
                value = str(h.get("value") or "")
                headers_map[name] = value

        subject = headers_map.get("subject", "(no subject)")
        from_addr = headers_map.get("from", "unknown@unknown")
        to_addr = headers_map.get("to", "")
        date_str = headers_map.get("date", "")

        # Extract author name from From header
        author = from_addr.split("<")[0].strip() or from_addr

        # Decode body
        body_text = _extract_body_from_payload(payload)
        if not body_text and not subject:
            return None

        # Build doc_id from message_id (stable and unique)
        if message_id:
            doc_id = f"gmail_{hashlib.sha256(message_id.encode()).hexdigest()[:24]}"
        else:
            doc_id = f"gmail_{hashlib.sha256((subject + from_addr).encode()).hexdigest()[:24]}"

        formatted_text = (
            f"Subject: {subject}\n"
            f"From: {from_addr}\n"
            f"To: {to_addr}\n"
            f"Date: {date_str}\n\n"
            f"{body_text}"
        ).strip()

        if not formatted_text:
            return None

        doc = create_staged_document(
            doc_id=doc_id,
            source="gmail",
            author=author,
            created_at=date_str,
            text=formatted_text,
            title=f"Email: {subject}",
            url=f"https://mail.google.com/mail/u/0/#all/{thread_id}" if thread_id else "",
            workspace_id=self.workspace_id,
            metadata={
                "message_id": message_id,
                "thread_id": thread_id,
                "from": from_addr,
                "to": to_addr,
                "subject": subject,
                "label_ids": message_data.get("labelIds", []),
            },
        )
        return doc

    def normalize_email_list(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalizes a list of full Gmail message objects.
        """
        docs = []
        for msg in messages:
            doc = self.normalize_email(msg)
            if doc:
                docs.append(doc)
        return docs
