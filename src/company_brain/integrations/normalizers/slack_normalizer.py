import json
import hashlib
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _extract_plain_strings(obj: Any) -> List[str]:
    """Recursively extracts human readable text strings from arbitrary nested dicts/lists."""
    res = []
    if isinstance(obj, str):
        s = obj.strip()
        if s.startswith("[{") or s.startswith("{\""):
            try:
                parsed = json.loads(s)
                res.extend(_extract_plain_strings(parsed))
                return res
            except Exception:
                pass
        if s and not s.startswith("Opt") and not s.startswith("Col"):
            res.append(s)
    elif isinstance(obj, dict):
        if "text" in obj and isinstance(obj["text"], str):
            res.extend(_extract_plain_strings(obj["text"]))
        if "label" in obj and isinstance(obj["label"], str):
            res.extend(_extract_plain_strings(obj["label"]))
        for k, v in obj.items():
            if k not in ["text", "label", "block_id", "column_id", "type"]:
                res.extend(_extract_plain_strings(v))
    elif isinstance(obj, list):
        for item in obj:
            res.extend(_extract_plain_strings(item))
    return res


class SlackNormalizer:
    """
    Transforms raw Slack API conversation events and history payloads
    into standard StagedDocument dictionaries for chunking, vector indexing, and HydraDB ingestion.
    """

    @staticmethod
    def _extract_full_slack_text(msg: Dict[str, Any]) -> str:
        """
        Recursively and generically extracts all readable text content from a Slack message payload,
        including main text, rich blocks, attachments, embedded workflow forms, list records, fields, and file previews.
        Works generically for any app, bot, workflow, or user message with zero hardcoding.
        """
        parts: List[str] = []

        # 1. Main text
        main_text = str(msg.get("text") or "").strip()
        if main_text:
            parts.append(main_text)

        # 2. Rich Blocks (Block Kit)
        for block in msg.get("blocks", []):
            if not isinstance(block, dict):
                continue
            b_strings = _extract_plain_strings(block)
            for s in b_strings:
                if s and s not in parts:
                    parts.append(s)

        # 3. Attachments (Workflow Cards, Legacy Bots, Lists, Form Trackers)
        for att in msg.get("attachments", []):
            if not isinstance(att, dict):
                continue

            # Check author / pretext
            author_name = str(att.get("author_name") or "").strip()
            if author_name and author_name not in parts:
                parts.append(f"Source: {author_name}")

            # Check direct title and text
            for field_name in ["title", "text", "fallback", "pretext"]:
                val = att.get(field_name)
                if val:
                    for s in _extract_plain_strings(val):
                        if s and s not in parts:
                            parts.append(s)

            # Check Slack Lists / Workflow Records (list_record)
            list_rec = att.get("list_record")
            if isinstance(list_rec, dict):
                # Build schema lookup
                schema_map = {}
                for col in list_rec.get("schema", []):
                    if isinstance(col, dict):
                        cid = col.get("id") or col.get("key")
                        cname = col.get("name") or col.get("key") or "Field"
                        choices = {}
                        for ch in col.get("options", {}).get("choices", []):
                            if isinstance(ch, dict):
                                cval = ch.get("value")
                                clbl = ch.get("label") or cval
                                if cval and clbl:
                                    choices[str(cval)] = str(clbl)
                        if cid:
                            schema_map[cid] = {"name": cname, "choices": choices}

                # Extract fields from record
                record = list_rec.get("record", {})
                for f in record.get("fields", []):
                    if not isinstance(f, dict):
                        continue
                    col_id = f.get("column_id") or f.get("key")
                    s_info = schema_map.get(col_id, {})
                    field_name = s_info.get("name") or col_id or "Field"
                    choices = s_info.get("choices", {})

                    val_str = ""
                    # 1. Direct text
                    if f.get("text"):
                        val_str = str(f.get("text"))
                    # 2. Select choices
                    elif "select" in f and isinstance(f["select"], list):
                        val_str = ", ".join([choices.get(s, s) for s in f["select"]])
                    # 3. User
                    elif "user" in f and isinstance(f["user"], list):
                        val_str = ", ".join([f"@{u}" for u in f["user"]])
                    # 4. Rich text / value
                    elif "value" in f:
                        raw_v = f["value"]
                        if isinstance(raw_v, str) and raw_v in choices:
                            val_str = choices[raw_v]
                        else:
                            extracted = _extract_plain_strings(raw_v)
                            if extracted:
                                val_str = " ".join(extracted)

                    if val_str and val_str.strip():
                        card_entry = f"{field_name}: {val_str.strip()}"
                        if card_entry not in parts:
                            parts.append(card_entry)

            # Attachment fields (key-value metadata cards)
            for f in att.get("fields", []):
                if isinstance(f, dict):
                    f_title = str(f.get("title") or "").strip()
                    f_val = str(f.get("value") or "").strip()
                    if f_title and f_val:
                        card_field = f"{f_title}: {f_val}"
                        if card_field not in parts:
                            parts.append(card_field)
                    elif f_val and f_val not in parts:
                        parts.append(f_val)

        # 4. Files
        for file_obj in msg.get("files", []):
            if not isinstance(file_obj, dict):
                continue
            fname = str(file_obj.get("name") or "").strip()
            ftitle = str(file_obj.get("title") or "").strip()
            if ftitle and ftitle not in parts:
                parts.append(f"File: {ftitle}")
            elif fname and fname not in parts:
                parts.append(f"File: {fname}")

        return "\n\n".join(parts)

    @classmethod
    def normalize_message(
        cls,
        msg: Dict[str, Any],
        channel_name: str = "general",
        channel_id: str = "",
    ) -> Dict[str, Any]:
        """
        Normalizes a single Slack message into a Company Brain document.
        """
        ts = msg.get("ts", "")
        user = msg.get("user") or msg.get("username") or msg.get("bot_profile", {}).get("name") or "slack_user"
        full_text = cls._extract_full_slack_text(msg).strip()

        # Build stable deterministic doc_id
        hash_input = f"{channel_id or channel_name}_{ts}_{full_text[:50]}"
        doc_id = f"slack_{hashlib.sha256(hash_input.encode()).hexdigest()[:24]}"

        # Format ISO timestamp
        created_at_iso = ""
        if ts:
            try:
                unix_sec = float(ts.split(".")[0])
                created_at_iso = datetime.fromtimestamp(unix_sec, tz=timezone.utc).isoformat()
            except Exception:
                created_at_iso = str(ts)

        title = f"#{channel_name} - message from @{user}"
        formatted_text = f"Channel: #{channel_name}\nAuthor: @{user}\nTimestamp: {created_at_iso}\n\n{full_text}"

        return {
            "doc_id": doc_id,
            "source": "slack",
            "title": title,
            "text": formatted_text,
            "author": user,
            "created_at": created_at_iso,
            "metadata": {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "slack_ts": ts,
                "reactions": [r.get("name") for r in msg.get("reactions", [])],
                "reply_count": msg.get("reply_count", 0),
            },
        }

    @classmethod
    def normalize_channel_history(
        cls,
        messages: List[Dict[str, Any]],
        channel_name: str = "general",
        channel_id: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Filters out empty messages and normalizes meaningful messages.
        """
        documents = []
        for msg in messages:
            extracted_text = cls._extract_full_slack_text(msg).strip()
            if not extracted_text:
                continue

            doc = cls.normalize_message(msg, channel_name=channel_name, channel_id=channel_id)
            documents.append(doc)

        return documents
