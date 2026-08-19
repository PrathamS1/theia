"""
integrations.py — FastAPI routes for Composio SaaS authentication & live workspace synchronization.
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
    prs_per_repo: int = 20
    issues_per_repo: int = 20


class SyncAllRequest(BaseModel):
    user_id: str = "default_user"
    selected_repos: Optional[List[str]] = None


@router.get("/status")
def get_integrations_status(user_id: str = "default_user"):
    """
    Returns the connection status of SaaS integrations (Slack, GitHub, etc.) for the user.
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
        slack_status = mgr.get_connection_status(user_id=user_id, toolkit="slack")
        github_status = mgr.get_connection_status(user_id=user_id, toolkit="github")
        return {
            "user_id": user_id,
            "configured": True,
            "integrations": [
                slack_status,
                github_status,
            ],
        }
    except Exception as e:
        logger.error("Failed to retrieve integration status: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/github/repos")
def list_github_repositories(user_id: str = "default_user"):
    """
    Returns the list of accessible GitHub repositories for the authenticated user so they can choose which ones to sync.
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


@router.post("/connect/slack")
def connect_slack(req: ConnectRequest):
    """
    Initiates Composio OAuth connection for Slack and returns the authorization Connect Link.
    """
    if not COMPOSIO_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="COMPOSIO_API_KEY is missing. Please set it in .env first."
        )

    try:
        mgr = ComposioManager()
        result = mgr.initiate_slack_connection(user_id=req.user_id)
        return result
    except Exception as e:
        logger.error("Failed to initiate Slack connection: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect/github")
def connect_github(req: ConnectRequest):
    """
    Initiates Composio OAuth connection for GitHub and returns the authorization Connect Link.
    """
    if not COMPOSIO_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="COMPOSIO_API_KEY is missing. Please set it in .env first."
        )

    try:
        mgr = ComposioManager()
        result = mgr.initiate_github_connection(user_id=req.user_id)
        return result
    except Exception as e:
        logger.error("Failed to initiate GitHub connection: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/slack")
def sync_slack(req: SyncRequest, background_tasks: BackgroundTasks):
    """
    Synchronizes messages from connected Slack channels into Company Brain (Vectors + HydraDB).
    """
    if not COMPOSIO_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="COMPOSIO_API_KEY is missing. Please set it in .env first."
        )

    try:
        worker = LiveSyncWorker(user_id=req.user_id)
        result = worker.sync_slack(
            max_channels=req.max_channels,
            messages_per_channel=req.messages_per_channel,
        )
        return result
    except Exception as e:
        logger.error("Error during Slack sync: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/github")
def sync_github(req: GitHubSyncRequest, background_tasks: BackgroundTasks):
    """
    Synchronizes repositories, pull requests, and issues from GitHub into Company Brain.
    """
    if not COMPOSIO_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="COMPOSIO_API_KEY is missing. Please set it in .env first."
        )

    try:
        worker = LiveSyncWorker(user_id=req.user_id)
        result = worker.sync_github(
            selected_repos=req.selected_repos,
            max_repos=req.max_repos,
            prs_per_repo=req.prs_per_repo,
            issues_per_repo=req.issues_per_repo,
        )
        return result
    except Exception as e:
        logger.error("Error during GitHub sync: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/all")
def sync_all(req: SyncAllRequest, background_tasks: BackgroundTasks):
    """
    Synchronizes all active connected SaaS tools (Slack, GitHub) for the specified user_id.
    """
    if not COMPOSIO_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="COMPOSIO_API_KEY is missing. Please set it in .env first."
        )

    mgr = ComposioManager()
    worker = LiveSyncWorker(user_id=req.user_id)
    results = {}

    # Check Slack
    slack_status = mgr.get_connection_status(user_id=req.user_id, toolkit="slack")
    if slack_status.get("status") == "ACTIVE":
        try:
            results["slack"] = worker.sync_slack()
        except Exception as e:
            results["slack"] = {"status": "ERROR", "error": str(e)}

    # Check GitHub
    github_status = mgr.get_connection_status(user_id=req.user_id, toolkit="github")
    if github_status.get("status") == "ACTIVE":
        try:
            results["github"] = worker.sync_github(selected_repos=req.selected_repos)
        except Exception as e:
            results["github"] = {"status": "ERROR", "error": str(e)}

    return {
        "status": "SUCCESS",
        "user_id": req.user_id,
        "results": results,
    }


@router.delete("/workspace/{user_id}")
def purge_workspace_data(user_id: str):
    """
    Purges all ingested graph nodes, edges, vectors, and staged files for the given workspace.
    Allows user to cleanly re-sync or reset their live data.
    """
    try:
        worker = LiveSyncWorker(user_id=user_id)
        result = worker.purge_workspace()
        return result
    except Exception as e:
        logger.error("Failed to purge workspace %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspace/purge")
def purge_workspace_post(req: ConnectRequest):
    """
    POST alternative for purging workspace data.
    """
    return purge_workspace_data(user_id=req.user_id)
