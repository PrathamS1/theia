"""
integrations/normalizers/github_normalizer.py — Production GitHub Data Normalizer.

Transforms raw GitHub payloads (Repositories, Pull Requests, Issues, Review Comments, and Commits)
obtained from Composio's GitHub Toolkit into canonical StagedDocument dictionaries for chunking,
vector embedding, and HydraDB knowledge graph insertion.
Completely source-independent with zero hardcoded repository names or company strings.
"""

import logging
from typing import Dict, List, Any, Optional
from company_brain.integrations.normalizers.base_normalizer import BaseNormalizer, create_staged_document

logger = logging.getLogger("company_brain.integrations.github_normalizer")


class GitHubNormalizer(BaseNormalizer):
    """
    Normalizes raw GitHub API payloads into canonical StagedDocument records.
    """

    def __init__(self, workspace_id: Optional[str] = None):
        self.workspace_id = workspace_id

    @property
    def source_name(self) -> str:
        return "github"

    def normalize(self, raw_payload: Any) -> List[Dict[str, Any]]:
        """
        Generic entrypoint accepting a dictionary of GitHub items or list of items.
        """
        staged_docs: List[Dict[str, Any]] = []

        if isinstance(raw_payload, list):
            for item in raw_payload:
                if isinstance(item, dict):
                    doc = self.normalize_item(item)
                    if doc:
                        staged_docs.append(doc)
        elif isinstance(raw_payload, dict):
            # Check if payload contains wrapped collections
            prs = raw_payload.get("pull_requests") or raw_payload.get("prs") or []
            issues = raw_payload.get("issues") or []
            commits = raw_payload.get("commits") or []
            repos = raw_payload.get("repositories") or raw_payload.get("repos") or []

            for pr in prs:
                doc = self.normalize_pull_request(pr)
                if doc:
                    staged_docs.append(doc)

            for issue in issues:
                doc = self.normalize_issue(issue)
                if doc:
                    staged_docs.append(doc)

            for commit in commits:
                doc = self.normalize_commit(commit)
                if doc:
                    staged_docs.append(doc)

            for repo in repos:
                doc = self.normalize_repository(repo)
                if doc:
                    staged_docs.append(doc)

            # If it's a single item directly
            if not staged_docs:
                doc = self.normalize_item(raw_payload)
                if doc:
                    staged_docs.append(doc)

        return staged_docs

    def normalize_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Dispatches an individual GitHub item to its specialized normalizer."""
        if "pull_request" in item or "diff_url" in item or ("head" in item and "base" in item):
            return self.normalize_pull_request(item)
        elif "issue" in item or ("number" in item and "comments" in item and "pull_request" not in item):
            return self.normalize_issue(item)
        elif "commit" in item or "sha" in item:
            return self.normalize_commit(item)
        elif "full_name" in item or "stargazers_count" in item:
            return self.normalize_repository(item)
        return None

    def normalize_pull_request(self, pr: Dict[str, Any], repo_name: str = "") -> Optional[Dict[str, Any]]:
        """Transforms a GitHub Pull Request into a rich StagedDocument."""
        pr_number = pr.get("number") or pr.get("id")
        if not pr_number:
            return None

        title = pr.get("title", f"Pull Request #{pr_number}").strip()
        body = pr.get("body") or ""
        author = pr.get("user", {}).get("login") or pr.get("author", {}).get("login") or ""
        created_at = pr.get("created_at") or pr.get("updated_at") or ""
        state = pr.get("state", "open")
        html_url = pr.get("html_url", "")
        repo = repo_name or pr.get("base", {}).get("repo", {}).get("full_name", "")

        # Format clean markdown representation
        text_lines = [
            f"# Pull Request #{pr_number}: {title}",
            f"**Repository:** {repo}" if repo else "",
            f"**Author:** @{author}" if author else "",
            f"**Status:** {state.upper()}",
            f"**Created At:** {created_at}" if created_at else "",
            "",
            "## Description",
            body.strip() if body.strip() else "",
        ]

        # Append review comments if present
        comments = pr.get("review_comments_list") or pr.get("comments_list") or []
        if comments:
            text_lines.extend(["", "## Review Discussion"])
            for c in comments:
                c_author = c.get("user", {}).get("login", "")
                c_body = c.get("body", "").strip()
                c_time = c.get("created_at", "")
                if c_body:
                    author_tag = f"**@{c_author}**" if c_author else "**Reviewer**"
                    time_tag = f" ({c_time})" if c_time else ""
                    text_lines.append(f"- {author_tag}{time_tag}: {c_body}")

        full_text = "\n".join(line for line in text_lines if line is not None)
        doc_id = f"gh_pr_{repo.replace('/', '_')}_{pr_number}" if repo else f"gh_pr_{pr_number}"

        return create_staged_document(
            doc_id=doc_id,
            source=self.source_name,
            title=f"PR #{pr_number}: {title}",
            text=full_text,
            author=author,
            created_at=created_at,
            url=html_url,
            workspace_id=self.workspace_id,
            metadata={
                "type": "pull_request",
                "pr_number": pr_number,
                "repository": repo,
                "state": state,
                "author": author,
            },
        )

    def normalize_issue(self, issue: Dict[str, Any], repo_name: str = "") -> Optional[Dict[str, Any]]:
        """Transforms a GitHub Issue into a rich StagedDocument."""
        issue_number = issue.get("number") or issue.get("id")
        if not issue_number:
            return None

        title = issue.get("title", f"Issue #{issue_number}").strip()
        body = issue.get("body") or ""
        author = issue.get("user", {}).get("login") or ""
        created_at = issue.get("created_at") or issue.get("updated_at") or ""
        state = issue.get("state", "open")
        html_url = issue.get("html_url", "")
        repo = repo_name or issue.get("repository_url", "").split("/repos/")[-1]

        labels = [l.get("name") for l in issue.get("labels", []) if isinstance(l, dict) and l.get("name")]
        assignees = [a.get("login") for a in issue.get("assignees", []) if isinstance(a, dict) and a.get("login")]

        text_lines = [
            f"# Issue #{issue_number}: {title}",
            f"**Repository:** {repo}" if repo else "",
            f"**Author:** @{author}" if author else "",
            f"**Status:** {state.upper()}",
            f"**Labels:** {', '.join(labels)}" if labels else "",
            f"**Assignees:** {', '.join('@' + a for a in assignees)}" if assignees else "",
            "",
            "## Issue Details",
            body.strip() if body.strip() else "",
        ]

        comments = issue.get("comments_list") or []
        if comments:
            text_lines.extend(["", "## Discussion Comments"])
            for c in comments:
                c_author = c.get("user", {}).get("login", "")
                c_body = c.get("body", "").strip()
                if c_body:
                    author_tag = f"**@{c_author}**" if c_author else "**Commenter**"
                    text_lines.append(f"- {author_tag}: {c_body}")

        full_text = "\n".join(line for line in text_lines if line is not None)
        doc_id = f"gh_issue_{repo.replace('/', '_')}_{issue_number}" if repo else f"gh_issue_{issue_number}"

        return create_staged_document(
            doc_id=doc_id,
            source=self.source_name,
            title=f"Issue #{issue_number}: {title}",
            text=full_text,
            author=author,
            created_at=created_at,
            url=html_url,
            workspace_id=self.workspace_id,
            metadata={
                "type": "issue",
                "issue_number": issue_number,
                "repository": repo,
                "state": state,
                "labels": labels,
                "author": author,
            },
        )

    def normalize_commit(self, commit_obj: Dict[str, Any], repo_name: str = "") -> Optional[Dict[str, Any]]:
        """Transforms a GitHub Commit into a concise StagedDocument."""
        sha = commit_obj.get("sha", "")
        if not sha:
            return None

        commit_data = commit_obj.get("commit", {})
        message = commit_data.get("message") or commit_obj.get("message") or ""
        author_info = commit_data.get("author", {})
        author_name = author_info.get("name") or commit_obj.get("author", {}).get("login") or ""
        author_email = author_info.get("email", "")
        created_at = author_info.get("date") or commit_obj.get("created_at") or ""
        html_url = commit_obj.get("html_url", "")

        first_line = message.strip().split("\n")[0] if message else f"Commit {sha[:7]}"

        text_lines = [
            f"# Commit {sha[:8]}: {first_line}",
            f"**Repository:** {repo_name}" if repo_name else "",
            f"**Author:** {author_name} ({author_email})" if author_email and author_name else (f"**Author:** {author_name}" if author_name else ""),
            f"**Date:** {created_at}" if created_at else "",
            f"**Full SHA:** `{sha}`",
            "",
            "## Commit Message",
            message.strip() if message.strip() else "",
        ]

        full_text = "\n".join(line for line in text_lines if line is not None)
        doc_id = f"gh_commit_{sha[:12]}"

        return create_staged_document(
            doc_id=doc_id,
            source=self.source_name,
            title=f"Commit {sha[:7]}: {first_line}",
            text=full_text,
            author=author_name,
            created_at=created_at,
            url=html_url,
            workspace_id=self.workspace_id,
            metadata={
                "type": "commit",
                "sha": sha,
                "author": author_name,
                "email": author_email,
            },
        )

    def normalize_repository(self, repo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transforms a Repository metadata overview into a StagedDocument."""
        full_name = repo.get("full_name") or repo.get("name")
        if not full_name:
            return None

        desc = repo.get("description") or "_No description._"
        owner = repo.get("owner", {}).get("login", "")
        language = repo.get("language") or "Code"
        topics = repo.get("topics", [])
        created_at = repo.get("created_at")
        html_url = repo.get("html_url", "")

        text_lines = [
            f"# Repository: {full_name}",
            f"**Owner:** @{owner}",
            f"**Primary Language:** {language}",
            f"**Topics:** {', '.join(topics)}" if topics else "",
            "",
            "## Overview",
            desc,
        ]

        full_text = "\n".join(line for line in text_lines if line is not None)
        doc_id = f"gh_repo_{full_name.replace('/', '_')}"

        return create_staged_document(
            doc_id=doc_id,
            source=self.source_name,
            title=f"Repository: {full_name}",
            text=full_text,
            author=owner,
            created_at=created_at,
            url=html_url,
            workspace_id=self.workspace_id,
            metadata={
                "type": "repository",
                "full_name": full_name,
                "language": language,
            },
        )
