#!/usr/bin/env python3
"""
scripts/cli_composio.py — CLI for Composio Enterprise SaaS Authentication & Live Slack Sync.

Usage:
  # 1. Generate Slack OAuth Connect Link:
  python3 scripts/cli_composio.py auth-slack --user-id default_user

  # 2. Check connection status:
  python3 scripts/cli_composio.py status --user-id default_user

  # 3. Pull live Slack messages & ingest into Vectors + HydraDB:
  python3 scripts/cli_composio.py sync-slack --user-id default_user --max-channels 5

  # 4. Query live enterprise memory:
  python3 scripts/cli_composio.py query "What was discussed about the deployment rollback?" --user-id default_user
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Ensure src/ is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("company_brain.cli_composio")

from company_brain.config import COMPOSIO_API_KEY, LIVE_DATA_DIR
from company_brain.integrations.composio_client import ComposioManager
from company_brain.integrations.sync_worker import LiveSyncWorker
from company_brain.query.engine import QueryEngine
from company_brain.indexing.vector_store import VectorStore


def cmd_auth_slack(args):
    """Generates the Composio Connect Link for Slack."""
    print("=" * 80)
    print("  🔗 COMPOSIO SLACK OAUTH CONNECT")
    print("=" * 80)

    if not COMPOSIO_API_KEY:
        print("❌ Error: COMPOSIO_API_KEY is not set in .env!")
        return

    mgr = ComposioManager()
    res = mgr.initiate_slack_connection(user_id=args.user_id)

    auth_url = res.get("auth_url")
    print(f"\n✅ Connection Initiated for user_id: '{args.user_id}'")
    print("\n👉 Please open the following URL in your browser to authorize Slack:")
    print("-" * 80)
    print(f"  {auth_url}")
    print("-" * 80)
    print("\nOnce authorized in your browser, run:")
    print(f"  python3 scripts/cli_composio.py status --user-id {args.user_id}\n")


def cmd_auth_github(args):
    """Generates the Composio Connect Link for GitHub."""
    print("=" * 80)
    print("  🔗 COMPOSIO GITHUB OAUTH CONNECT")
    print("=" * 80)

    if not COMPOSIO_API_KEY:
        print("❌ Error: COMPOSIO_API_KEY is not set in .env!")
        return

    mgr = ComposioManager()
    res = mgr.initiate_github_connection(user_id=args.user_id)

    auth_url = res.get("auth_url")
    print(f"\n✅ Connection Initiated for user_id: '{args.user_id}'")
    print("\n👉 Please open the following URL in your browser to authorize GitHub:")
    print("-" * 80)
    print(f"  {auth_url}")
    print("-" * 80)
    print("\nOnce authorized in your browser, run:")
    print(f"  python3 scripts/cli_composio.py status --user-id {args.user_id}\n")


def cmd_status(args):
    """Checks the live connection status for both Slack and GitHub."""
    print("=" * 80)
    print("  📊 COMPOSIO SAAS CONNECTION STATUS")
    print("=" * 80)

    if not COMPOSIO_API_KEY:
        print("❌ Error: COMPOSIO_API_KEY is not set in .env!")
        return

    mgr = ComposioManager()
    print(f"\nUser ID:   {args.user_id}\n")

    for tk in ["slack", "github"]:
        res = mgr.get_connection_status(user_id=args.user_id, toolkit=tk)
        status = res.get("status", "DISCONNECTED")
        status_icon = "🟢" if status == "ACTIVE" else ("🟡" if status == "INITIATED" else "⚪")
        print(f"  [{tk.upper():<6}] Status: {status_icon} {status:<12} | Account: {res.get('account_name') or 'N/A'}")

    print("\n" + "=" * 80 + "\n")


def cmd_sync_slack(args):
    """Pulls live Slack messages and updates HydraDB and vector store."""
    print("=" * 80)
    print("  🔄 SYNCING LIVE SLACK WORKSPACE INTO COMPANY BRAIN")
    print("=" * 80)

    worker = LiveSyncWorker(user_id=args.user_id)
    result = worker.sync_slack(
        max_channels=args.max_channels,
        messages_per_channel=args.messages_per_channel,
    )

    if result.get("status") == "SUCCESS":
        print("\n" + "=" * 80)
        print("  🎉 SLACK SYNC COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print(f"  • Documents Synced:     {result.get('documents_synced', 0)}")
        print(f"  • Chunks Vectorized:    {result.get('chunks_vectorized', 0)}")
        print(f"  • Facts Extracted:      {result.get('facts_extracted', 0)}")
        print(f"  • Resolution Summary:   {result.get('resolution')}")
        print("=" * 80 + "\n")
    else:
        print(f"\n❌ Sync Failed: {result.get('message')}\n")


def cmd_sync_github(args):
    """Pulls live GitHub repositories, PRs, and issues and updates HydraDB and vector store."""
    print("=" * 80)
    print("  🔄 SYNCING LIVE GITHUB REPOSITORIES INTO COMPANY BRAIN")
    print("=" * 80)

    worker = LiveSyncWorker(user_id=args.user_id)
    result = worker.sync_github(
        max_repos=args.max_repos,
        prs_per_repo=args.prs_per_repo,
        issues_per_repo=args.issues_per_repo,
    )

    if result.get("status") == "SUCCESS":
        print("\n" + "=" * 80)
        print("  🎉 GITHUB SYNC COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print(f"  • Documents Synced:     {result.get('documents_synced', 0)}")
        print(f"  • Chunks Vectorized:    {result.get('chunks_vectorized', 0)}")
        print(f"  • Facts Extracted:      {result.get('facts_extracted', 0)}")
        print(f"  • Resolution Summary:   {result.get('resolution')}")
        print("=" * 80 + "\n")
    else:
        print(f"\n❌ Sync Failed: {result.get('message')}\n")


def cmd_query(args):
    """Queries the live synchronized data."""
    print("=" * 80)
    print("  💬 QUERYING LIVE COMPANY BRAIN")
    print("=" * 80)

    user_live_dir = LIVE_DATA_DIR / args.user_id
    vectors_dir = user_live_dir / "vectors"
    staged_file = user_live_dir / "live_staged_docs.json"

    if not staged_file.exists():
        print(f"⚠️  No live synced data found for user_id='{args.user_id}'. Please run sync-slack first.")
        return

    # Initialize QueryEngine over the live directory with strict workspace isolation
    engine = QueryEngine(
        vector_dir=str(vectors_dir),
        staged_docs_path=str(staged_file),
        workspace_id=args.user_id,
    )

    print(f"\nQuestion: {args.question}\n")
    result = engine.query(args.question)

    print("-" * 80)
    print(f"Answer:\n{result.answer}\n")
    print(f"Citations: {result.citations}")
    print(f"Confidence: {result.confidence:.4f}")
    print("-" * 80 + "\n")


def cmd_chat(args):
    """Interactive multi-turn query REPL with warm in-memory model and indices for instant answers."""
    user_live_dir = LIVE_DATA_DIR / args.user_id
    vectors_dir = user_live_dir / "vectors"
    staged_file = user_live_dir / "live_staged_docs.json"

    if not staged_file.exists():
        print(f"⚠️  No live synced data found for user_id='{args.user_id}'. Please run sync-slack first.")
        return

    print("=" * 80)
    print("  💬 COMPANY BRAIN LIVE INTERACTIVE CHAT (Warm Memory Mode)")
    print("  Type your questions below. Type 'exit' or 'quit' to stop.")
    print("=" * 80)

    print("Loading models and vector index into memory (one-time initialization)...")
    engine = QueryEngine(
        vector_dir=str(vectors_dir),
        staged_docs_path=str(staged_file),
        workspace_id=args.user_id,
    )
    print("Ready! Ask any question about your workspace:\n")

    while True:
        try:
            q = input("Brain > ").strip()
            if not q:
                continue
            if q.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break
            
            result = engine.query(q)
            print("\n" + "-" * 60)
            print(f"Answer:\n{result.answer}\n")
            print(f"Citations: {result.citations} | Confidence: {result.confidence:.4f}")
            print("-" * 60 + "\n")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break


def main():
    parser = argparse.ArgumentParser(description="Composio Live Integration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. auth-slack
    p_auth_slack = subparsers.add_parser("auth-slack", help="Generate Slack OAuth Connect Link")
    p_auth_slack.add_argument("--user-id", default="default_user", help="Workspace / User ID")

    # 2. auth-github
    p_auth_gh = subparsers.add_parser("auth-github", help="Generate GitHub OAuth Connect Link")
    p_auth_gh.add_argument("--user-id", default="default_user", help="Workspace / User ID")

    # 3. status
    p_status = subparsers.add_parser("status", help="Check connection status (Slack & GitHub)")
    p_status.add_argument("--user-id", default="default_user", help="Workspace / User ID")

    # 4. sync-slack
    p_sync_slack = subparsers.add_parser("sync-slack", help="Sync live Slack workspace into HydraDB")
    p_sync_slack.add_argument("--user-id", default="default_user", help="Workspace / User ID")
    p_sync_slack.add_argument("--max-channels", type=int, default=5, help="Max channels to sync")
    p_sync_slack.add_argument("--messages-per-channel", type=int, default=30, help="Messages per channel")

    # 5. sync-github
    p_sync_gh = subparsers.add_parser("sync-github", help="Sync live GitHub repositories into HydraDB")
    p_sync_gh.add_argument("--user-id", default="default_user", help="Workspace / User ID")
    p_sync_gh.add_argument("--max-repos", type=int, default=5, help="Max repositories to sync")
    p_sync_gh.add_argument("--prs-per-repo", type=int, default=20, help="Max PRs per repository")
    p_sync_gh.add_argument("--issues-per-repo", type=int, default=20, help="Max issues per repository")

    # 6. query
    p_query = subparsers.add_parser("query", help="Query the live knowledge base")
    p_query.add_argument("question", help="The question to ask")
    p_query.add_argument("--user-id", default="default_user", help="Workspace / User ID")

    # 7. chat
    p_chat = subparsers.add_parser("chat", help="Interactive real-time chat with warm in-memory index")
    p_chat.add_argument("--user-id", default="default_user", help="Workspace / User ID")

    args = parser.parse_args()

    if args.command == "auth-slack":
        cmd_auth_slack(args)
    elif args.command == "auth-github":
        cmd_auth_github(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "sync-slack":
        cmd_sync_slack(args)
    elif args.command == "sync-github":
        cmd_sync_github(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "chat":
        cmd_chat(args)


if __name__ == "__main__":
    main()
