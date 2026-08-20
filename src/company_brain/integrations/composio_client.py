"""
composio_client.py — Managed Composio SDK client for live enterprise SaaS authentication & tool execution.
"""

import time
from typing import Dict, Any, List, Optional, Tuple
import logging
from company_brain.config import COMPOSIO_API_KEY

logger = logging.getLogger("company_brain.integrations.composio")

# In-memory cache for user repositories: user_id -> (timestamp, repos)
_REPOS_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}


class ComposioManager:
    """
    Wraps the official Composio SDK (v0.20+) to manage user OAuth connections
    and execute live actions across enterprise SaaS platforms.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or COMPOSIO_API_KEY
        self.sdk = None
        if self.api_key:
            try:
                from composio import Composio
                self.sdk = Composio(api_key=self.api_key)
            except Exception as e:
                logger.debug("Could not initialize Composio SDK: %s", e)

    def _ensure_sdk(self):
        if not self.sdk:
            if not self.api_key:
                raise ValueError("COMPOSIO_API_KEY is not set. Please configure it in .env to use live SaaS integrations.")
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

    # ── GitHub Toolkit Methods ────────────────────────────────────────────────

    def initiate_github_connection(self, user_id: str = "default_user", callback_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Initiates a managed OAuth connection for GitHub for the specified user_id.
        Returns the connection_id and authorization URL (Connect Link).
        """
        logger.info("Initiating GitHub connection for user_id=%s...", user_id)
        auth_config_id = self.sdk.toolkits._get_auth_config_id("github")
        connection_req = self.sdk.connected_accounts.link(
            user_id=user_id,
            auth_config_id=auth_config_id,
            callback_url=callback_url,
        )

        redirect_url = getattr(connection_req, "redirect_url", None)
        conn_id = getattr(connection_req, "id", None)

        return {
            "user_id": user_id,
            "toolkit": "github",
            "connection_id": conn_id,
            "auth_url": redirect_url,
            "status": "INITIATED",
        }

    def fetch_github_repositories(self, user_id: str = "default_user", force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetches accessible repositories for the authenticated GitHub user using GITHUB_LIST_REPOSITORIES_FOR_THE_AUTHENTICATED_USER.
        Caches results in memory for fast UI access.
        """
        now = time.time()
        if not force_refresh and user_id in _REPOS_CACHE:
            cached_time, cached_data = _REPOS_CACHE[user_id]
            if now - cached_time < 300:
                logger.info("Returning %d cached repositories for user_id=%s.", len(cached_data), user_id)
                return cached_data

        logger.info("Fetching GitHub repositories from Composio for user_id=%s...", user_id)
        try:
            res = self.sdk.tools.execute(
                slug="GITHUB_LIST_REPOSITORIES_FOR_THE_AUTHENTICATED_USER",
                user_id=user_id,
                arguments={"per_page": 30, "sort": "updated"},
                dangerously_skip_version_check=True,
            )
            data = res.get("data", {}) if isinstance(res, dict) else getattr(res, "data", {})
            repos_list = []
            if isinstance(data, list):
                repos_list = data
            elif isinstance(data, dict):
                repos_list = data.get("repositories") or data.get("repos") or []

            if repos_list:
                _REPOS_CACHE[user_id] = (now, repos_list)
            return repos_list
        except Exception as e:
            logger.error("Failed to fetch GitHub repositories: %s", e)
            return []

    def fetch_github_pull_requests(
        self,
        owner: str,
        repo: str,
        user_id: str = "default_user",
        state: str = "all",
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Fetches pull requests for a repository using GITHUB_LIST_PULL_REQUESTS.
        Requires both owner and repo parameters.
        """
        logger.info("Fetching GitHub pull requests for %s/%s (state=%s)...", owner, repo, state)
        try:
            res = self.sdk.tools.execute(
                slug="GITHUB_LIST_PULL_REQUESTS",
                user_id=user_id,
                arguments={
                    "owner": owner,
                    "repo": repo,
                    "state": state,
                    "per_page": limit,
                },
                dangerously_skip_version_check=True,
            )
            data = res.get("data", {}) if isinstance(res, dict) else getattr(res, "data", {})
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("pull_requests") or data.get("prs") or []
            return []
        except Exception as e:
            logger.error("Failed to fetch GitHub pull requests for %s/%s: %s", owner, repo, e)
            return []

    def fetch_github_issues(
        self,
        owner: str,
        repo: str,
        user_id: str = "default_user",
        state: str = "all",
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Fetches repository issues using GITHUB_LIST_REPOSITORY_ISSUES.
        Requires both owner and repo parameters.
        """
        logger.info("Fetching GitHub issues for %s/%s (state=%s)...", owner, repo, state)
        try:
            res = self.sdk.tools.execute(
                slug="GITHUB_LIST_REPOSITORY_ISSUES",
                user_id=user_id,
                arguments={
                    "owner": owner,
                    "repo": repo,
                    "state": state,
                    "per_page": limit,
                },
                dangerously_skip_version_check=True,
            )
            data = res.get("data", {}) if isinstance(res, dict) else getattr(res, "data", {})
            if isinstance(data, list):
                # Filter out pure pull requests from issue list
                return [item for item in data if isinstance(item, dict) and "pull_request" not in item]
            elif isinstance(data, dict):
                return data.get("issues") or []
            return []
        except Exception as e:
            logger.error("Failed to fetch GitHub issues for %s/%s: %s", owner, repo, e)
            return []

    def fetch_github_commits(
        self,
        owner: str,
        repo: str,
        user_id: str = "default_user",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Fetches recent repository commits using GITHUB_LIST_COMMITS.
        """
        logger.info("Fetching GitHub commits for %s/%s...", owner, repo)
        try:
            res = self.sdk.tools.execute(
                slug="GITHUB_LIST_COMMITS",
                user_id=user_id,
                arguments={
                    "owner": owner,
                    "repo": repo,
                    "per_page": limit,
                },
                dangerously_skip_version_check=True,
            )
            data = res.get("data", {}) if isinstance(res, dict) else getattr(res, "data", {})
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("commits") or []
            return []
        except Exception as e:
            logger.error("Failed to fetch GitHub commits for %s/%s: %s", owner, repo, e)
            return []

    def fetch_github_readme(
        self,
        owner: str,
        repo: str,
        user_id: str = "default_user",
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches repository README using GITHUB_GET_A_REPOSITORY_README.
        """
        logger.info("Fetching GitHub README for %s/%s...", owner, repo)
        try:
            res = self.sdk.tools.execute(
                slug="GITHUB_GET_A_REPOSITORY_README",
                user_id=user_id,
                arguments={
                    "owner": owner,
                    "repo": repo,
                },
                dangerously_skip_version_check=True,
            )
            data = res.get("data", {}) if isinstance(res, dict) else getattr(res, "data", {})
            if isinstance(data, dict) and (data.get("content") or data.get("download_url")):
                return data
            return None
        except Exception as e:
            logger.debug("README fetch skipped for %s/%s: %s", owner, repo, e)
            return None

    # ── Discord Toolkit Methods ───────────────────────────────────────────────

    def initiate_discord_connection(self, user_id: str = "default_user", callback_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Initiates a managed OAuth connection for Discord for the specified user_id.
        Returns the connection_id and authorization URL (Connect Link).
        """
        logger.info("Initiating Discord connection for user_id=%s...", user_id)
        auth_config_id = self.sdk.toolkits._get_auth_config_id("discord")
        connection_req = self.sdk.connected_accounts.link(
            user_id=user_id,
            auth_config_id=auth_config_id,
            callback_url=callback_url,
        )
        return {
            "user_id": user_id,
            "toolkit": "discord",
            "connection_id": getattr(connection_req, "id", None),
            "auth_url": getattr(connection_req, "redirect_url", None),
            "status": "INITIATED",
        }

    def fetch_discord_guilds(self, user_id: str = "default_user") -> List[Dict[str, Any]]:
        """
        Fetches the list of Discord guilds (servers) the user is a member of
        using DISCORD_LIST_MY_GUILDS.
        """
        logger.info("Fetching Discord guilds for user_id=%s...", user_id)
        try:
            res = self.sdk.tools.execute(
                slug="DISCORD_LIST_MY_GUILDS",
                user_id=user_id,
                arguments={},
                dangerously_skip_version_check=True,
            )
            data = res.get("data", {}) if isinstance(res, dict) else getattr(res, "data", {})
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("guilds") or data.get("items") or []
            return []
        except Exception as e:
            logger.error("Failed to fetch Discord guilds: %s", e)
            return []

    def fetch_discord_channels(
        self,
        guild_id: str,
        user_id: str = "default_user",
    ) -> List[Dict[str, Any]]:
        """
        Fetches the list of channels in a Discord guild using DISCORD_GET_GUILD_CHANNELS.
        """
        logger.info("Fetching Discord channels for guild=%s...", guild_id)
        try:
            res = self.sdk.tools.execute(
                slug="DISCORD_GET_GUILD_CHANNELS",
                user_id=user_id,
                arguments={"guild_id": guild_id},
                dangerously_skip_version_check=True,
            )
            data = res.get("data", {}) if isinstance(res, dict) else getattr(res, "data", {})
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("channels") or data.get("items") or []
            return []
        except Exception as e:
            logger.error("Failed to fetch Discord channels for guild %s: %s", guild_id, e)
            return []

    def fetch_discord_messages(
        self,
        channel_id: str,
        user_id: str = "default_user",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Fetches message history for a Discord channel using DISCORD_GET_CHANNEL_MESSAGES.
        """
        logger.info("Fetching Discord messages for channel=%s (limit=%d)...", channel_id, limit)
        try:
            res = self.sdk.tools.execute(
                slug="DISCORD_GET_CHANNEL_MESSAGES",
                user_id=user_id,
                arguments={"channel_id": channel_id, "limit": limit},
                dangerously_skip_version_check=True,
            )
            data = res.get("data", {}) if isinstance(res, dict) else getattr(res, "data", {})
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("messages") or data.get("items") or []
            return []
        except Exception as e:
            logger.error("Failed to fetch Discord messages for channel %s: %s", channel_id, e)
            return []

    # ── Gmail Toolkit Methods ─────────────────────────────────────────────────

    def initiate_gmail_connection(self, user_id: str = "default_user", callback_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Initiates a managed OAuth connection for Gmail for the specified user_id.
        Returns the connection_id and authorization URL (Connect Link).
        """
        logger.info("Initiating Gmail connection for user_id=%s...", user_id)
        auth_config_id = self.sdk.toolkits._get_auth_config_id("gmail")
        connection_req = self.sdk.connected_accounts.link(
            user_id=user_id,
            auth_config_id=auth_config_id,
            callback_url=callback_url,
        )
        return {
            "user_id": user_id,
            "toolkit": "gmail",
            "connection_id": getattr(connection_req, "id", None),
            "auth_url": getattr(connection_req, "redirect_url", None),
            "status": "INITIATED",
        }

    def fetch_gmail_email_ids(
        self,
        user_id: str = "default_user",
        query: str = "label:inbox",
        max_results: int = 50,
    ) -> List[str]:
        """
        Lists Gmail message IDs using GMAIL_LIST_EMAILS.
        Returns a list of message_id strings for subsequent GMAIL_GET_MESSAGE calls.
        """
        logger.info("Listing Gmail emails for user_id=%s (query=%r, max=%d)...", user_id, query, max_results)
        for slug in ["GMAIL_FETCH_EMAILS", "GMAIL_LIST_MESSAGES", "GMAIL_LIST_EMAILS"]:
            try:
                res = self.sdk.tools.execute(
                    slug=slug,
                    user_id=user_id,
                    arguments={"q": query, "max_results": max_results},
                    dangerously_skip_version_check=True,
                )
                data = res.get("data", {}) if isinstance(res, dict) else getattr(res, "data", {})
                if isinstance(data, list):
                    return [str(m.get("id") or m.get("message_id") or m) for m in data if m]
                if isinstance(data, dict):
                    messages = data.get("messages") or data.get("response_data") or data.get("emails") or []
                    if isinstance(messages, list):
                        return [str(m.get("id") or m.get("message_id") or m) for m in messages if m]
            except Exception as e:
                logger.debug("Gmail tool slug %s failed: %s", slug, e)
        return []

    def fetch_gmail_message(
        self,
        message_id: str,
        user_id: str = "default_user",
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches a full Gmail message by ID using GMAIL_GET_MESSAGE.
        Returns the raw message dict with payload/headers/body.
        """
        logger.info("Fetching Gmail message id=%s for user_id=%s...", message_id, user_id)
        try:
            res = self.sdk.tools.execute(
                slug="GMAIL_GET_MESSAGE",
                user_id=user_id,
                arguments={"message_id": message_id, "format": "full"},
                dangerously_skip_version_check=True,
            )
            data = res.get("data", {}) if isinstance(res, dict) else getattr(res, "data", {})
            if isinstance(data, dict) and data:
                return data
            return None
        except Exception as e:
            logger.error("Failed to fetch Gmail message %s: %s", message_id, e)
            return None

    # ── Google Drive Toolkit Methods ──────────────────────────────────────────

    def initiate_googledrive_connection(self, user_id: str = "default_user", callback_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Initiates a managed OAuth connection for Google Drive for the specified user_id.
        Returns the connection_id and authorization URL (Connect Link).
        """
        logger.info("Initiating Google Drive connection for user_id=%s...", user_id)
        auth_config_id = self.sdk.toolkits._get_auth_config_id("googledrive")
        connection_req = self.sdk.connected_accounts.link(
            user_id=user_id,
            auth_config_id=auth_config_id,
            callback_url=callback_url,
        )
        return {
            "user_id": user_id,
            "toolkit": "googledrive",
            "connection_id": getattr(connection_req, "id", None),
            "auth_url": getattr(connection_req, "redirect_url", None),
            "status": "INITIATED",
        }

    def fetch_drive_files(
        self,
        user_id: str = "default_user",
        query: str = "",
        max_files: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Lists files on Google Drive using GOOGLEDRIVE_LIST_FILES.
        Returns file metadata dicts (id, name, mimeType, modifiedTime, etc.).
        """
        logger.info("Fetching Google Drive files for user_id=%s (max=%d)...", user_id, max_files)
        try:
            args: Dict[str, Any] = {"page_size": max_files}
            if query:
                args["q"] = query
            res = self.sdk.tools.execute(
                slug="GOOGLEDRIVE_LIST_FILES",
                user_id=user_id,
                arguments=args,
                dangerously_skip_version_check=True,
            )
            data = res.get("data", {}) if isinstance(res, dict) else getattr(res, "data", {})
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("files") or data.get("items") or []
            return []
        except Exception as e:
            logger.error("Failed to fetch Google Drive files: %s", e)
            return []

    def fetch_drive_file_content(
        self,
        file_id: str,
        mime_type: str = "",
        user_id: str = "default_user",
    ) -> Optional[str]:
        """
        Exports/fetches the text content of a Google Drive file using GOOGLEDRIVE_EXPORT_FILE
        for Google Workspace formats, or GOOGLEDRIVE_GET_FILE for native text files.
        Returns plain text string or None if content cannot be retrieved.
        """
        logger.info("Fetching content for Drive file_id=%s (mime=%s)...", file_id, mime_type)

        # Google Workspace types require export to plain text
        _GOOGLE_WORKSPACE_TYPES = {
            "application/vnd.google-apps.document",
            "application/vnd.google-apps.spreadsheet",
            "application/vnd.google-apps.presentation",
        }

        try:
            if mime_type in _GOOGLE_WORKSPACE_TYPES:
                export_mime = "text/plain"
                if "spreadsheet" in mime_type:
                    export_mime = "text/csv"
                res = self.sdk.tools.execute(
                    slug="GOOGLEDRIVE_EXPORT_FILE",
                    user_id=user_id,
                    arguments={"file_id": file_id, "mime_type": export_mime},
                    dangerously_skip_version_check=True,
                )
            else:
                res = self.sdk.tools.execute(
                    slug="GOOGLEDRIVE_GET_FILE",
                    user_id=user_id,
                    arguments={"file_id": file_id},
                    dangerously_skip_version_check=True,
                )

            data = res.get("data", {}) if isinstance(res, dict) else getattr(res, "data", {})
            if isinstance(data, str):
                return data
            if isinstance(data, dict):
                return data.get("content") or data.get("text") or data.get("body") or None
            return None
        except Exception as e:
            logger.error("Failed to fetch content for Drive file %s: %s", file_id, e)
            return None
