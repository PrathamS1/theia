"""
integrations.py — FastAPI routes for Composio SaaS authentication & live workspace synchronization.
"""

from typing import Dict, Any, Optional
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


@router.get("/status")
def get_integrations_status(user_id: str = "default_user"):
    """
    Returns the connection status of SaaS integrations (Slack, etc.) for the user.
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
        return {
            "user_id": user_id,
            "configured": True,
            "integrations": [
                slack_status,
            ],
        }
    except Exception as e:
        logger.error("Failed to retrieve integration status: %s", e)
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
