"""
composio_client.py — Managed Composio SDK client for live enterprise SaaS authentication & tool execution.
"""

from typing import Dict, Any, List, Optional
import logging
from company_brain.config import COMPOSIO_API_KEY

logger = logging.getLogger("company_brain.integrations.composio")


class ComposioManager:
    """
    Wraps the official Composio SDK (v0.20+) to manage user OAuth connections
    and execute live actions across enterprise SaaS platforms.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or COMPOSIO_API_KEY
        if not self.api_key:
            raise ValueError(
                "COMPOSIO_API_KEY is not set. Please set it in .env or pass it explicitly."
            )

        from composio import Composio
        self.sdk = Composio(api_key=self.api_key)

    def initiate_slack_connection(self, user_id: str = "default_user", callback_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Initiates a managed OAuth connection for Slack for the specified user_id using the Composio link API.
        Returns the connection_id and authorization URL (Connect Link).
        """
        logger.info("Initiating Slack connection for user_id=%s...", user_id)
        auth_config_id = self.sdk.toolkits._get_auth_config_id("slack")
        connection_req = self.sdk.connected_accounts.link(
            user_id=user_id,
            auth_config_id=auth_config_id,
            callback_url=callback_url,
        )

        redirect_url = getattr(connection_req, "redirect_url", None)
        conn_id = getattr(connection_req, "id", None)

        return {
            "user_id": user_id,
            "toolkit": "slack",
            "connection_id": conn_id,
            "auth_url": redirect_url,
            "status": "INITIATED",
        }

    def get_connection_status(self, user_id: str = "default_user", toolkit: str = "slack") -> Dict[str, Any]:
        """
        Retrieves the current connection status of a toolkit for the given user_id.
        """
        logger.info("Checking connection status for user_id=%s, toolkit=%s...", user_id, toolkit)
        accounts_resp = self.sdk.connected_accounts.list(
            user_ids=[user_id],
            toolkit_slugs=[toolkit],
        )

        items = getattr(accounts_resp, "items", []) or []
        if not items:
            return {
                "user_id": user_id,
                "toolkit": toolkit,
                "status": "DISCONNECTED",
                "connected_account_id": None,
                "account_name": None,
            }

        # Take latest connection
        acc = items[0]
        status = getattr(acc, "status", "UNKNOWN")
        acc_id = getattr(acc, "id", None)
        acc_name = getattr(acc, "account_name", None) or getattr(acc, "user_id", None)

        return {
            "user_id": user_id,
            "toolkit": toolkit,
            "status": status,
            "connected_account_id": acc_id,
            "account_name": acc_name,
            "created_at": str(getattr(acc, "created_at", "")),
        }

    def fetch_slack_channels(self, user_id: str = "default_user") -> List[Dict[str, Any]]:
        """
        Fetches public/accessible channels in the connected Slack workspace using SLACK_LIST_ALL_CHANNELS.
        """
        logger.info("Fetching Slack channels for user_id=%s...", user_id)
        try:
            res = self.sdk.tools.execute(
                slug="SLACK_LIST_ALL_CHANNELS",
                user_id=user_id,
                arguments={"types": "public_channel,private_channel", "limit": 50},
                dangerously_skip_version_check=True,
            )
            data = res.get("data", {}) if isinstance(res, dict) else getattr(res, "data", {})
            if isinstance(data, dict):
                channels = data.get("channels", [])
            else:
                channels = []
            return channels
        except Exception as e:
            logger.error("Failed to fetch Slack channels: %s", e)
            return []

    def fetch_slack_messages(
        self,
        channel_id: str,
        user_id: str = "default_user",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Fetches conversation history for a specific Slack channel using SLACK_FETCH_CONVERSATION_HISTORY.
        """
        logger.info("Fetching messages for channel=%s (limit=%d)...", channel_id, limit)
        try:
            res = self.sdk.tools.execute(
                slug="SLACK_FETCH_CONVERSATION_HISTORY",
                user_id=user_id,
                arguments={
                    "channel": channel_id,
                    "limit": limit,
                },
                dangerously_skip_version_check=True,
            )
            data = res.get("data", {}) if isinstance(res, dict) else getattr(res, "data", {})
            if isinstance(data, dict):
                messages = data.get("messages", [])
            else:
                messages = []
            return messages
        except Exception as e:
            logger.error("Failed to fetch Slack messages for channel %s: %s", channel_id, e)
            return []
