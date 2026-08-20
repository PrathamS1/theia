"""
integrations.py — FastAPI routes for Composio SaaS authentication & live workspace synchronization.

Supports: Slack, GitHub, Discord, Gmail, Google Drive.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import logging

from company_brain.integrations.composio_client import ComposioManager
from company_brain.integrations.sync_worker import LiveSyncWorker
from company_brain.config import COMPOSIO_API_KEY

logger = logging.getLogger("company_brain.server.integrations")
router = APIRouter(prefix="/api/integrations", tags=["Integrations"])


# ── Request Models ────────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    user_id: str = "default_user"


class SyncRequest(BaseModel):
    user_id: str = "default_user"
    max_channels: int = 5
    messages_per_channel: int = 30


class GitHubSyncRequest(BaseModel):
    user_id: str = "default_user"
    selected_repos: Optional[List[str]] = None
    max_repos: int = 10
    prs_per_repo: int = 50
    issues_per_repo: int = 50
    commits_per_repo: int = 50


class DiscordSyncRequest(BaseModel):
    user_id: str = "default_user"
    guild_id: str = ""
    max_channels: int = 5
    messages_per_channel: int = 50


class GmailSyncRequest(BaseModel):
    user_id: str = "default_user"
    query: str = "label:inbox"
    max_emails: int = 50


class DriveSyncRequest(BaseModel):
    user_id: str = "default_user"
    max_files: int = 30
    query: str = ""


class SyncAllRequest(BaseModel):
    user_id: str = "default_user"
    selected_repos: Optional[List[str]] = None


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status")
def get_integrations_status(user_id: str = "default_user"):
    """
    Returns the connection status of all SaaS integrations for the user:
    Slack, GitHub, Discord, Gmail, Google Drive.
    """
    if not COMPOSIO_API_KEY:
        return {
            "user_id": user_id,
            "configured": False,
            "error": "COMPOSIO_API_KEY is not configured in .env",
            "integrations": [],
        }

    try:
        mgr = ComposioManager()
        integrations = []
        for toolkit in ["slack", "github", "discord", "gmail", "googledrive"]:
            try:
                status = mgr.get_connection_status(user_id=user_id, toolkit=toolkit)
                integrations.append(status)
            except Exception as e:
                integrations.append({
                    "user_id": user_id,
                    "toolkit": toolkit,
                    "status": "UNKNOWN",
                    "error": str(e),
                })
        return {
            "user_id": user_id,
            "configured": True,
            "integrations": integrations,
        }
    except Exception as e:
        logger.error("Failed to retrieve integration status: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── GitHub: List Repos ────────────────────────────────────────────────────────

@router.get("/github/repos")
def list_github_repositories(user_id: str = "default_user"):
    """
    Returns the list of accessible GitHub repositories for the authenticated user.
    """
    if not COMPOSIO_API_KEY:
        raise HTTPException(status_code=400, detail="COMPOSIO_API_KEY is not configured in .env")

    try:
        mgr = ComposioManager()
        repos = mgr.fetch_github_repositories(user_id=user_id)
        summary = []
        for r in repos:
            owner_login = r.get("owner", {}).get("login", "") if isinstance(r.get("owner"), dict) else ""
            full_name = r.get("full_name") or (f"{owner_login}/{r.get('name')}" if owner_login else r.get("name", ""))
            summary.append({
                "id": r.get("id"),
                "name": r.get("name"),
                "full_name": full_name,
                "description": r.get("description") or "",
                "private": r.get("private", False),
                "html_url": r.get("html_url") or "",
                "stars": r.get("stargazers_count", 0),
                "updated_at": r.get("updated_at", ""),
            })
        return {
            "user_id": user_id,
            "total_repositories": len(summary),
            "repositories": summary,
        }
    except Exception as e:
        logger.error("Failed to list GitHub repositories for user_id=%s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Discord: List Guilds ──────────────────────────────────────────────────────

@router.get("/discord/guilds")
def list_discord_guilds(user_id: str = "default_user"):
    """
    Returns the list of Discord guilds (servers) accessible to the authenticated user.
    """
    if not COMPOSIO_API_KEY:
        raise HTTPException(status_code=400, detail="COMPOSIO_API_KEY is not configured in .env")

    try:
        mgr = ComposioManager()
        guilds = mgr.fetch_discord_guilds(user_id=user_id)
        summary = [
            {
                "id": g.get("id"),
                "name": g.get("name"),
                "icon": g.get("icon"),
                "owner": g.get("owner", False),
                "member_count": g.get("approximate_member_count"),
            }
            for g in guilds if isinstance(g, dict)
        ]
        return {"user_id": user_id, "total_guilds": len(summary), "guilds": summary}
    except Exception as e:
        logger.error("Failed to list Discord guilds for user_id=%s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Connect Endpoints ─────────────────────────────────────────────────────────

@router.post("/connect/slack")
def connect_slack(req: ConnectRequest):
    """Initiates Composio OAuth connection for Slack."""
    if not COMPOSIO_API_KEY:
        raise HTTPException(status_code=400, detail="COMPOSIO_API_KEY is missing. Please set it in .env first.")
    try:
        mgr = ComposioManager()
        return mgr.initiate_slack_connection(user_id=req.user_id)
    except Exception as e:
        logger.error("Failed to initiate Slack connection: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect/github")
def connect_github(req: ConnectRequest):
    """Initiates Composio OAuth connection for GitHub."""
    if not COMPOSIO_API_KEY:
        raise HTTPException(status_code=400, detail="COMPOSIO_API_KEY is missing. Please set it in .env first.")
    try:
        mgr = ComposioManager()
        return mgr.initiate_github_connection(user_id=req.user_id)
    except Exception as e:
        logger.error("Failed to initiate GitHub connection: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect/discord")
def connect_discord(req: ConnectRequest):
    """Initiates Composio OAuth connection for Discord and returns the authorization Connect Link."""
    if not COMPOSIO_API_KEY:
        raise HTTPException(status_code=400, detail="COMPOSIO_API_KEY is missing. Please set it in .env first.")
    try:
        mgr = ComposioManager()
        return mgr.initiate_discord_connection(user_id=req.user_id)
    except Exception as e:
        logger.error("Failed to initiate Discord connection: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect/gmail")
def connect_gmail(req: ConnectRequest):
    """Initiates Composio OAuth connection for Gmail and returns the authorization Connect Link."""
    if not COMPOSIO_API_KEY:
        raise HTTPException(status_code=400, detail="COMPOSIO_API_KEY is missing. Please set it in .env first.")
    try:
        mgr = ComposioManager()
        return mgr.initiate_gmail_connection(user_id=req.user_id)
    except Exception as e:
        logger.error("Failed to initiate Gmail connection: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect/googledrive")
def connect_googledrive(req: ConnectRequest):
    """Initiates Composio OAuth connection for Google Drive and returns the authorization Connect Link."""
    if not COMPOSIO_API_KEY:
        raise HTTPException(status_code=400, detail="COMPOSIO_API_KEY is missing. Please set it in .env first.")
    try:
        mgr = ComposioManager()
        return mgr.initiate_googledrive_connection(user_id=req.user_id)
    except Exception as e:
        logger.error("Failed to initiate Google Drive connection: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Sync Endpoints ────────────────────────────────────────────────────────────

@router.post("/sync/slack")
def sync_slack(req: SyncRequest, background_tasks: BackgroundTasks):
    """Synchronizes messages from connected Slack channels into Company Brain."""
    if not COMPOSIO_API_KEY:
        raise HTTPException(status_code=400, detail="COMPOSIO_API_KEY is missing. Please set it in .env first.")
    try:
        worker = LiveSyncWorker(user_id=req.user_id)
        return worker.sync_slack(
            max_channels=req.max_channels,
            messages_per_channel=req.messages_per_channel,
        )
    except Exception as e:
        logger.error("Error during Slack sync: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/github")
def sync_github(req: GitHubSyncRequest, background_tasks: BackgroundTasks):
    """Synchronizes repositories, pull requests, and issues from GitHub into Company Brain."""
    if not COMPOSIO_API_KEY:
        raise HTTPException(status_code=400, detail="COMPOSIO_API_KEY is missing. Please set it in .env first.")
    try:
        worker = LiveSyncWorker(user_id=req.user_id)
        return worker.sync_github(
            selected_repos=req.selected_repos,
            max_repos=req.max_repos,
            prs_per_repo=req.prs_per_repo,
            issues_per_repo=req.issues_per_repo,
            commits_per_repo=req.commits_per_repo,
        )
    except Exception as e:
        logger.error("Error during GitHub sync: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/discord")
def sync_discord(req: DiscordSyncRequest, background_tasks: BackgroundTasks):
    """
    Synchronizes messages from connected Discord channels into Company Brain (Vectors + HydraDB).
    Provide guild_id to sync a specific server, or leave empty to auto-select the first available guild.
    """
    if not COMPOSIO_API_KEY:
        raise HTTPException(status_code=400, detail="COMPOSIO_API_KEY is missing. Please set it in .env first.")
    try:
        worker = LiveSyncWorker(user_id=req.user_id)
        return worker.sync_discord(
            guild_id=req.guild_id,
            max_channels=req.max_channels,
            messages_per_channel=req.messages_per_channel,
        )
    except Exception as e:
        logger.error("Error during Discord sync: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/gmail")
def sync_gmail(req: GmailSyncRequest, background_tasks: BackgroundTasks):
    """
    Synchronizes emails from connected Gmail account into Company Brain (Vectors + HydraDB).
    Use the 'query' field to filter emails (Gmail search syntax, e.g. 'label:inbox after:2024/01/01').
    """
    if not COMPOSIO_API_KEY:
        raise HTTPException(status_code=400, detail="COMPOSIO_API_KEY is missing. Please set it in .env first.")
    try:
        worker = LiveSyncWorker(user_id=req.user_id)
        return worker.sync_gmail(
            query=req.query,
            max_emails=req.max_emails,
        )
    except Exception as e:
        logger.error("Error during Gmail sync: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/googledrive")
def sync_googledrive(req: DriveSyncRequest, background_tasks: BackgroundTasks):
    """
    Synchronizes text-exportable files from connected Google Drive into Company Brain.
    Binary files (images, videos) are automatically skipped.
    Use 'query' for Google Drive search syntax (e.g. "mimeType='application/vnd.google-apps.document'").
    """
    if not COMPOSIO_API_KEY:
        raise HTTPException(status_code=400, detail="COMPOSIO_API_KEY is missing. Please set it in .env first.")
    try:
        worker = LiveSyncWorker(user_id=req.user_id)
        return worker.sync_googledrive(
            max_files=req.max_files,
            query=req.query,
        )
    except Exception as e:
        logger.error("Error during Google Drive sync: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/all")
def sync_all(req: SyncAllRequest, background_tasks: BackgroundTasks):
    """
    Synchronizes ALL active connected SaaS tools for the specified user_id.
    Checks and syncs: Slack, GitHub, Discord, Gmail, Google Drive.
    """
    if not COMPOSIO_API_KEY:
        raise HTTPException(status_code=400, detail="COMPOSIO_API_KEY is missing. Please set it in .env first.")

    mgr = ComposioManager()
    worker = LiveSyncWorker(user_id=req.user_id)
    results: Dict[str, Any] = {}

    _TOOLKIT_SYNCS = {
        "slack":       ("ACTIVE",              lambda: worker.sync_slack()),
        "github":      ("ACTIVE|CONNECTED",    lambda: worker.sync_github(selected_repos=req.selected_repos)),
        "discord":     ("ACTIVE",              lambda: worker.sync_discord()),
        "gmail":       ("ACTIVE",              lambda: worker.sync_gmail()),
        "googledrive": ("ACTIVE",              lambda: worker.sync_googledrive()),
    }

    for toolkit, (active_states, sync_fn) in _TOOLKIT_SYNCS.items():
        try:
            status_info = mgr.get_connection_status(user_id=req.user_id, toolkit=toolkit)
            current_status = status_info.get("status", "")
            allowed = {s.strip() for s in active_states.split("|")}
            if current_status in allowed:
                results[toolkit] = sync_fn()
            else:
                results[toolkit] = {
                    "status": "SKIPPED",
                    "message": f"{toolkit.capitalize()} is not connected (current: {current_status}).",
                }
        except Exception as e:
            results[toolkit] = {"status": "ERROR", "error": str(e)}

    # After all syncs, run cross-source resolution to link persons across platforms
    resolution_result = worker.run_cross_source_resolution()

    return {
        "status": "SUCCESS",
        "user_id": req.user_id,
        "results": results,
        "cross_source_resolution": resolution_result,
    }


# ── Workspace Purge ───────────────────────────────────────────────────────────

@router.delete("/workspace/{user_id}")
def purge_workspace_data(user_id: str):
    """
    Purges all ingested graph nodes, edges, vectors, and staged files for the given workspace.
    Allows user to cleanly re-sync or reset their live data.
    """
    try:
        worker = LiveSyncWorker(user_id=user_id)
        return worker.purge_workspace()
    except Exception as e:
        logger.error("Failed to purge workspace %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspace/purge")
def purge_workspace_post(req: ConnectRequest):
    """POST alternative for purging workspace data."""
    return purge_workspace_data(user_id=req.user_id)


# ── Cross-Source Resolution ───────────────────────────────────────────────────

@router.post("/resolve")
def run_resolution(req: ConnectRequest):
    """
    Runs cross-source entity resolution across ALL ingested sources for a workspace.
    Links Person entities that appear under different names across Slack (@handles)
    and GitHub (logins) by fuzzy matching with handle normalization.

    Should be called AFTER all individual syncs are complete.
    """
    try:
        worker = LiveSyncWorker(user_id=req.user_id)
        return worker.run_cross_source_resolution()
    except Exception as e:
        logger.error("Failed to run cross-source resolution for %s: %s", req.user_id, e)
        raise HTTPException(status_code=500, detail=str(e))
