"""
integrations/normalizers/discord_normalizer.py — Discord Data Normalizer.

Transforms raw Discord API message payloads obtained from Composio's Discord Toolkit
into canonical StagedDocument dictionaries for chunking, vector embedding,
and HydraDB knowledge graph insertion.
"""

import hashlib
import logging
from typing import Dict, Any, List, Optional

from company_brain.integrations.normalizers.base_normalizer import BaseNormalizer, create_staged_document

logger = logging.getLogger("company_brain.integrations.discord_normalizer")


class DiscordNormalizer(BaseNormalizer):
    """
    Normalizes raw Discord API message payloads into canonical StagedDocument records.
    """

    def __init__(self, workspace_id: Optional[str] = None):
        self.workspace_id = workspace_id

    @property
    def source_name(self) -> str:
        return "discord"

    def normalize(self, raw_payload: Any) -> List[Dict[str, Any]]:
        """Generic entrypoint: accepts a list of messages or a single message dict."""
        docs = []
        if isinstance(raw_payload, list):
            for item in raw_payload:
                doc = self.normalize_message(item)
                if doc:
                    docs.append(doc)
        elif isinstance(raw_payload, dict):
            doc = self.normalize_message(raw_payload)
            if doc:
                docs.append(doc)
        return docs

    @staticmethod
    def _extract_message_text(msg: Dict[str, Any]) -> str:
        """
        Extracts readable text from a Discord message dict.
        Handles plain content, embeds, and attachments.
        """
        parts: List[str] = []

        # 1. Plain message content
        content = str(msg.get("content") or "").strip()
        if content:
            parts.append(content)

        # 2. Embeds (rich cards from bots/webhooks)
        for embed in msg.get("embeds", []):
            if not isinstance(embed, dict):
                continue
            title = str(embed.get("title") or "").strip()
            description = str(embed.get("description") or "").strip()
            if title:
                parts.append(f"Embed Title: {title}")
            if description:
                parts.append(f"Embed Description: {description}")
            for field in embed.get("fields", []):
                if isinstance(field, dict):
                    fname = str(field.get("name") or "").strip()
                    fvalue = str(field.get("value") or "").strip()
                    if fname and fvalue:
                        parts.append(f"{fname}: {fvalue}")

        # 3. Attachments (filenames only — we can't download binary files)
        for att in msg.get("attachments", []):
            if isinstance(att, dict):
                fname = str(att.get("filename") or att.get("url", "")).strip()
                if fname:
                    parts.append(f"Attachment: {fname}")

        return "\n\n".join(parts)

    def normalize_message(
        self,
        msg: Dict[str, Any],
        channel_name: str = "unknown-channel",
        channel_id: str = "",
        guild_name: str = "unknown-server",
        guild_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Normalizes a single Discord message into a Company Brain StagedDocument.
        Returns None if the message has no meaningful content.
        """
        text = self._extract_message_text(msg).strip()
        if not text:
            return None

        message_id = str(msg.get("id") or "")
        author_obj = msg.get("author") or {}
        author = str(
            author_obj.get("global_name")
            or author_obj.get("username")
            or author_obj.get("id")
            or "discord_user"
        )

        # Deterministic doc_id from guild+channel+message
        hash_input = f"{guild_id or guild_name}_{channel_id or channel_name}_{message_id or text[:50]}"
        doc_id = f"discord_{hashlib.sha256(hash_input.encode()).hexdigest()[:24]}"

        # ISO timestamp from Discord snowflake or timestamp field
        created_at = str(msg.get("timestamp") or "")

        title = f"{guild_name} #{channel_name} — @{author}"
        formatted_text = (
            f"Server: {guild_name}\n"
            f"Channel: #{channel_name}\n"
            f"Author: @{author}\n"
            f"Timestamp: {created_at}\n\n"
            f"{text}"
        )

        doc = create_staged_document(
            doc_id=doc_id,
            source="discord",
            author=author,
            created_at=created_at,
            text=formatted_text,
            title=title,
            url=f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}" if guild_id and channel_id and message_id else "",
            workspace_id=self.workspace_id,
            metadata={
                "guild_id": guild_id,
                "guild_name": guild_name,
                "channel_id": channel_id,
                "channel_name": channel_name,
                "message_id": message_id,
                "reactions": [r.get("emoji", {}).get("name") for r in msg.get("reactions", []) if isinstance(r, dict)],
            },
        )
        return doc

    def normalize_channel_messages(
        self,
        messages: List[Dict[str, Any]],
        channel_name: str = "general",
        channel_id: str = "",
        guild_name: str = "unknown-server",
        guild_id: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Normalizes a list of Discord channel messages, skipping empty ones.
        """
        docs = []
        for msg in messages:
            doc = self.normalize_message(
                msg,
                channel_name=channel_name,
                channel_id=channel_id,
                guild_name=guild_name,
                guild_id=guild_id,
            )
            if doc:
                docs.append(doc)
        return docs
