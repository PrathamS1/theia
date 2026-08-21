"""
integrations/normalizers/base_normalizer.py — Canonical StagedDocument Protocol & Abstract Normalizer.

Standardizes all incoming raw payloads from Composio enterprise SaaS tools (Slack, GitHub, Jira, Gmail, etc.)
into canonical StagedDocument records for chunking, dense vector indexing, and HydraDB graph loading.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


def create_staged_document(
    doc_id: str,
    source: str,
    author: str,
    created_at: str,
    text: str,
    title: str = "",
    url: Optional[str] = None,
    workspace_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Creates a canonical StagedDocument dictionary conforming to the Company Brain standard.
    """
    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()
    if not title:
        title = doc_id

    meta = dict(metadata or {})
    if url:
        meta["url"] = url

    doc: Dict[str, Any] = {
        "doc_id": doc_id,
        "source": source.lower(),
        "author": author,
        "created_at": created_at,
        "title": title,
        "text": text.strip(),
        "url": url or "",
        "metadata": meta,
    }
    if workspace_id:
        doc["workspace_id"] = workspace_id
    return doc


class BaseNormalizer(ABC):
    """
    Abstract base normalizer for enterprise SaaS integrations.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Returns the canonical source name (e.g., 'github', 'slack', 'jira')."""
        pass

    @abstractmethod
    def normalize(self, raw_payload: Any) -> List[Dict[str, Any]]:
        """Transforms a raw Composio payload into a list of canonical StagedDocument dictionaries."""
        pass
