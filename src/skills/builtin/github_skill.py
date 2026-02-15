"""
GitHub integration skill for Gulama.

Actions:
- list_repos: List user's repositories
- create_issue: Create an issue
- list_issues: List issues in a repo
- create_pr: Create a pull request
- get_pr: Get PR details
- search_code: Search code across repos
- list_notifications: Get unread notifications
- star_repo: Star a repository

Requires: GITHUB_TOKEN environment variable or vault secret.
"""

from __future__ import annotations

import os
from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("github_skill")

GITHUB_API = "https://api.github.com"


class GitHubSkill(BaseSkill):
    """GitHub API integration — repos, issues, PRs, code search."""

    def __init__(self) -> None:
        self._token: str | None = None

    def _get_token(self) -> str:
        if self._token:
            return self._token
        self._token = os.getenv("GITHUB_TOKEN", "")
        if not self._token:
            try:
                from src.security.secrets_vault import SecretsVault
                vault = SecretsVault()
                if vault.is_initialized:
                    self._token = vault.get("GITHUB_TOKEN") or ""
            except Exception:
                pass
        return self._token or ""

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="github",
            description="GitHub integration — manage repos, issues, PRs, search code, notifications",
            version="1.0.0",
            author="gulama",
            required_actions=[ActionType.NETWORK_REQUEST],
            is_builtin=True,
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "github",
                "description": (
                    "Interact with GitHub — manage repositories, issues, pull requests, "
                    "search code, and view notifications."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "list_repos", "create_issue", "list_issues",
                                "create_pr", "get_pr", "search_code",
                                "list_notifications", "star_repo",
                            ],
                            "description": "The GitHub action to perform",
                        },
                        "owner": {"type": "string", "description": "Repository owner/org"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "title": {"type": "string", "description": "Issue/PR title"},
                        "body": {"type": "string", "description": "Issue/PR body"},
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Labels for issue",
                        },
                        "head": {"type": "string", "description": "PR head branch"},
                        "base": {"type": "string", "description": "PR base branch (default: main)"},
                        "query": {"type": "string", "description": "Search query for code search"},
                        "number": {"type": "integer", "description": "Issue/PR number"},
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed", "all"],
                            "description": "Filter by state (default: open)",
                        },
                    },
                    "required": ["action"],
                },
            },
        }

    async def execute(self, **kwargs: Any) -> SkillResult:
        action = kwargs.get("action", "")
        token = self._get_token()
        if not token:
            return SkillResult(
                success=False, output="",
                error="GITHUB_TOKEN not configured. Set it via environment variable or 'gulama vault set GITHUB_TOKEN'",
            )

        dispatch = {
            "list_repos": self._list_repos,
            "create_issue": self._create_issue,
            "list_issues": self._list_issues,
            "create_pr": self._create_pr,
            "get_pr": self._get_pr,
            "search_code": self._search_code,
            "list_notifications": self._list_notifications,
            "star_repo": self._star_repo,
        }

        handler = dispatch.get(action)
        if not handler:
            return SkillResult(success=False, output="", error=f"Unknown action: {action}")

        try:
            return await handler(token=token, **{k: v for k, v in kwargs.items() if k != "action"})
        except Exception as e:
            logger.error("github_error", action=action, error=str(e))
            return SkillResult(success=False, output="", error=f"GitHub error: {str(e)[:400]}")

    async def _api(self, token: str, method: str, path: str, json_data: dict | None = None) -> dict | list:
        import httpx
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                resp = await client.get(f"{GITHUB_API}{path}", headers=headers)
            elif method == "POST":
                resp = await client.post(f"{GITHUB_API}{path}", headers=headers, json=json_data)
            elif method == "PUT":
                resp = await client.put(f"{GITHUB_API}{path}", headers=headers, json=json_data)
            else:
                resp = await client.request(method, f"{GITHUB_API}{path}", headers=headers, json=json_data)
            resp.raise_for_status()
            return resp.json() if resp.content else {}

    async def _list_repos(self, token: str, **_: Any) -> SkillResult:
        repos = await self._api(token, "GET", "/user/repos?sort=updated&per_page=30")
        lines = []
        for r in repos:
            stars = r.get("stargazers_count", 0)
            lang = r.get("language", "Unknown")
            desc = (r.get("description") or "")[:80]
            lines.append(f"- {r['full_name']} ({lang}, {stars} stars) — {desc}")
        return SkillResult(success=True, output="\n".join(lines) or "No repositories found.")

    async def _create_issue(self, token: str, owner: str = "", repo: str = "", title: str = "",
                            body: str = "", labels: list | None = None, **_: Any) -> SkillResult:
        if not all([owner, repo, title]):
            return SkillResult(success=False, output="", error="owner, repo, and title are required")
        data: dict[str, Any] = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        result = await self._api(token, "POST", f"/repos/{owner}/{repo}/issues", data)
        return SkillResult(
            success=True,
            output=f"Issue #{result['number']} created: {result['html_url']}",
            metadata={"issue_number": result["number"], "url": result["html_url"]},
        )

    async def _list_issues(self, token: str, owner: str = "", repo: str = "",
                           state: str = "open", **_: Any) -> SkillResult:
        if not all([owner, repo]):
            return SkillResult(success=False, output="", error="owner and repo are required")
        issues = await self._api(token, "GET", f"/repos/{owner}/{repo}/issues?state={state}&per_page=20")
        lines = []
        for i in issues:
            if "pull_request" not in i:
                labels = ", ".join(l["name"] for l in i.get("labels", []))
                lines.append(f"#{i['number']} [{i['state']}] {i['title']}" + (f" ({labels})" if labels else ""))
        return SkillResult(success=True, output="\n".join(lines) or "No issues found.")

    async def _create_pr(self, token: str, owner: str = "", repo: str = "", title: str = "",
                         body: str = "", head: str = "", base: str = "main", **_: Any) -> SkillResult:
        if not all([owner, repo, title, head]):
            return SkillResult(success=False, output="", error="owner, repo, title, and head are required")
        result = await self._api(
            token, "POST", f"/repos/{owner}/{repo}/pulls",
            {"title": title, "body": body, "head": head, "base": base},
        )
        return SkillResult(
            success=True,
            output=f"PR #{result['number']} created: {result['html_url']}",
            metadata={"pr_number": result["number"], "url": result["html_url"]},
        )

    async def _get_pr(self, token: str, owner: str = "", repo: str = "",
                      number: int = 0, **_: Any) -> SkillResult:
        if not all([owner, repo, number]):
            return SkillResult(success=False, output="", error="owner, repo, and number are required")
        pr = await self._api(token, "GET", f"/repos/{owner}/{repo}/pulls/{number}")
        return SkillResult(
            success=True,
            output=(
                f"PR #{pr['number']}: {pr['title']}\n"
                f"State: {pr['state']} | Merged: {pr.get('merged', False)}\n"
                f"Author: {pr['user']['login']}\n"
                f"Branch: {pr['head']['ref']} → {pr['base']['ref']}\n"
                f"URL: {pr['html_url']}\n\n"
                f"{(pr.get('body') or '')[:500]}"
            ),
        )

    async def _search_code(self, token: str, query: str = "", **_: Any) -> SkillResult:
        if not query:
            return SkillResult(success=False, output="", error="query is required for code search")
        import httpx
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{GITHUB_API}/search/code",
                params={"q": query, "per_page": 10},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        lines = [f"Found {data.get('total_count', 0)} results:"]
        for item in data.get("items", [])[:10]:
            lines.append(f"- {item['repository']['full_name']}/{item['path']}")
        return SkillResult(success=True, output="\n".join(lines))

    async def _list_notifications(self, token: str, **_: Any) -> SkillResult:
        notifs = await self._api(token, "GET", "/notifications?per_page=20")
        lines = []
        for n in notifs:
            repo = n.get("repository", {}).get("full_name", "")
            subject = n.get("subject", {})
            lines.append(f"- [{subject.get('type', '')}] {repo}: {subject.get('title', '')}")
        return SkillResult(success=True, output="\n".join(lines) or "No unread notifications.")

    async def _star_repo(self, token: str, owner: str = "", repo: str = "", **_: Any) -> SkillResult:
        if not all([owner, repo]):
            return SkillResult(success=False, output="", error="owner and repo are required")
        await self._api(token, "PUT", f"/user/starred/{owner}/{repo}")
        return SkillResult(success=True, output=f"Starred {owner}/{repo}")
