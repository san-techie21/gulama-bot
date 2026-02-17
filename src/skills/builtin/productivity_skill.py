"""
Productivity integrations skill for Gulama.

Multi-service skill covering:
- Trello: Boards, lists, cards
- Linear: Issues, projects
- Jira: Issues, projects (basic)
- Todoist: Tasks, projects
- Obsidian: Local vault read/write (via file system)

Each service uses its respective REST API with token auth.
"""

from __future__ import annotations

import os
from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("productivity_skill")


class ProductivitySkill(BaseSkill):
    """Multi-service productivity integration — Trello, Linear, Jira, Todoist, Obsidian."""

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="productivity",
            description="Productivity integrations — Trello, Linear, Jira, Todoist, Obsidian vault",
            version="1.0.0",
            author="gulama",
            required_actions=[
                ActionType.NETWORK_REQUEST,
                ActionType.FILE_READ,
                ActionType.FILE_WRITE,
            ],
            is_builtin=True,
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "productivity",
                "description": (
                    "Productivity tool integrations. Supports: "
                    "Trello (boards/cards), Linear (issues), Jira (issues), "
                    "Todoist (tasks), Obsidian (local vault notes)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "enum": ["trello", "linear", "jira", "todoist", "obsidian"],
                            "description": "Which service to interact with",
                        },
                        "action": {
                            "type": "string",
                            "enum": [
                                "list",
                                "create",
                                "update",
                                "get",
                                "search",
                                "read_note",
                                "write_note",
                                "list_notes",
                            ],
                        },
                        "board_id": {"type": "string"},
                        "list_id": {"type": "string"},
                        "project_id": {"type": "string"},
                        "issue_key": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "status": {"type": "string"},
                        "priority": {"type": "string"},
                        "query": {"type": "string"},
                        "note_path": {
                            "type": "string",
                            "description": "Relative path in Obsidian vault",
                        },
                        "content": {"type": "string"},
                        "vault_path": {
                            "type": "string",
                            "description": "Path to Obsidian vault directory",
                        },
                    },
                    "required": ["service", "action"],
                },
            },
        }

    async def execute(self, **kwargs: Any) -> SkillResult:
        service = kwargs.get("service", "")
        action = kwargs.get("action", "")

        dispatch = {
            "trello": self._trello,
            "linear": self._linear,
            "jira": self._jira,
            "todoist": self._todoist,
            "obsidian": self._obsidian,
        }

        handler = dispatch.get(service)
        if not handler:
            return SkillResult(
                success=False,
                output="",
                error=f"Unknown service: {service}. Supported: trello, linear, jira, todoist, obsidian",
            )

        try:
            return await handler(
                action=action, **{k: v for k, v in kwargs.items() if k not in ("service", "action")}
            )
        except Exception as e:
            logger.error("productivity_error", service=service, action=action, error=str(e))
            return SkillResult(success=False, output="", error=f"{service} error: {str(e)[:400]}")

    # ── Trello ─────────────────────────────────────────────────

    async def _trello(self, action: str = "", **kwargs: Any) -> SkillResult:
        api_key = os.getenv("TRELLO_API_KEY", "")
        token = os.getenv("TRELLO_TOKEN", "")
        if not api_key or not token:
            return SkillResult(
                success=False, output="", error="TRELLO_API_KEY and TRELLO_TOKEN required."
            )

        import httpx

        base = "https://api.trello.com/1"
        params = {"key": api_key, "token": token}

        async with httpx.AsyncClient(timeout=20) as client:
            if action == "list":
                # List boards
                resp = await client.get(f"{base}/members/me/boards", params=params)
                resp.raise_for_status()
                boards = resp.json()
                lines = [
                    f"- {b['name']} (ID: {b['id'][:8]}...) {'[closed]' if b.get('closed') else ''}"
                    for b in boards
                ]
                return SkillResult(success=True, output="\n".join(lines) or "No boards.")

            elif action == "create":
                title = kwargs.get("title", "")
                desc = kwargs.get("description", "")
                list_id = kwargs.get("list_id", "")
                if not list_id or not title:
                    return SkillResult(
                        success=False,
                        output="",
                        error="list_id and title required for card creation.",
                    )
                resp = await client.post(
                    f"{base}/cards",
                    params={**params, "idList": list_id, "name": title, "desc": desc},
                )
                resp.raise_for_status()
                card = resp.json()
                return SkillResult(
                    success=True, output=f"Card created: {card['name']} ({card['shortUrl']})"
                )

            elif action == "get":
                board_id = kwargs.get("board_id", "")
                if not board_id:
                    return SkillResult(success=False, output="", error="board_id required.")
                resp = await client.get(
                    f"{base}/boards/{board_id}/lists", params={**params, "cards": "open"}
                )
                resp.raise_for_status()
                lists = resp.json()
                lines = []
                for lst in lists:
                    lines.append(f"\n[{lst['name']}]")
                    for card in lst.get("cards", []):
                        lines.append(f"  - {card['name']}")
                return SkillResult(success=True, output="\n".join(lines) or "Empty board.")

        return SkillResult(success=False, output="", error=f"Unknown Trello action: {action}")

    # ── Linear ─────────────────────────────────────────────────

    async def _linear(self, action: str = "", **kwargs: Any) -> SkillResult:
        token = os.getenv("LINEAR_API_KEY", "")
        if not token:
            return SkillResult(success=False, output="", error="LINEAR_API_KEY required.")

        import httpx

        headers = {"Authorization": token, "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=20) as client:
            if action == "list":
                query = '{"query":"{ issues(first: 20, orderBy: updatedAt) { nodes { identifier title state { name } priority assignee { name } } } }"}'
                resp = await client.post(
                    "https://api.linear.app/graphql", content=query, headers=headers
                )
                resp.raise_for_status()
                issues = resp.json().get("data", {}).get("issues", {}).get("nodes", [])
                lines = []
                for i in issues:
                    state = i.get("state", {}).get("name", "")
                    assignee = (
                        i.get("assignee", {}).get("name", "Unassigned")
                        if i.get("assignee")
                        else "Unassigned"
                    )
                    lines.append(f"- {i['identifier']}: {i['title']} [{state}] ({assignee})")
                return SkillResult(success=True, output="\n".join(lines) or "No issues found.")

            elif action == "create":
                title = kwargs.get("title", "")
                desc = kwargs.get("description", "")
                if not title:
                    return SkillResult(success=False, output="", error="title required.")
                mutation = {
                    "query": "mutation($input: IssueCreateInput!) { issueCreate(input: $input) { success issue { identifier title url } } }",
                    "variables": {"input": {"title": title, "description": desc}},
                }
                resp = await client.post(
                    "https://api.linear.app/graphql", json=mutation, headers=headers
                )
                resp.raise_for_status()
                result = resp.json().get("data", {}).get("issueCreate", {})
                issue = result.get("issue", {})
                return SkillResult(
                    success=True,
                    output=f"Issue created: {issue.get('identifier', '')} — {issue.get('title', '')} ({issue.get('url', '')})",
                )

        return SkillResult(success=False, output="", error=f"Unknown Linear action: {action}")

    # ── Jira ──────────────────────────────────────────────────

    async def _jira(self, action: str = "", **kwargs: Any) -> SkillResult:
        base_url = os.getenv("JIRA_BASE_URL", "")
        email = os.getenv("JIRA_EMAIL", "")
        token = os.getenv("JIRA_API_TOKEN", "")
        if not base_url or not email or not token:
            return SkillResult(
                success=False,
                output="",
                error="JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN required.",
            )

        import httpx

        auth = (email, token)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=20, auth=auth) as client:
            if action == "list":
                project = kwargs.get("project_id", "")
                jql = f"project={project} ORDER BY updated DESC" if project else "ORDER BY updated DESC"
                resp = await client.get(
                    f"{base_url.rstrip('/')}/rest/api/3/search",
                    params={"jql": jql, "maxResults": 20},
                    headers=headers,
                )
                resp.raise_for_status()
                issues = resp.json().get("issues", [])
                lines = []
                for i in issues:
                    key = i.get("key", "")
                    fields = i.get("fields", {})
                    summary = fields.get("summary", "")
                    status = fields.get("status", {}).get("name", "")
                    assignee = (fields.get("assignee") or {}).get("displayName", "Unassigned")
                    lines.append(f"- {key}: {summary} [{status}] ({assignee})")
                return SkillResult(success=True, output="\n".join(lines) or "No issues found.")

            elif action == "get":
                issue_key = kwargs.get("issue_key", "")
                if not issue_key:
                    return SkillResult(success=False, output="", error="issue_key required.")
                resp = await client.get(
                    f"{base_url.rstrip('/')}/rest/api/3/issue/{issue_key}",
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                fields = data.get("fields", {})
                return SkillResult(
                    success=True,
                    output=(
                        f"Key: {data.get('key', '')}\n"
                        f"Summary: {fields.get('summary', '')}\n"
                        f"Status: {fields.get('status', {}).get('name', '')}\n"
                        f"Assignee: {(fields.get('assignee') or {}).get('displayName', 'Unassigned')}\n"
                        f"Description: {(fields.get('description') or '')[:500]}"
                    ),
                )

            elif action == "create":
                title = kwargs.get("title", "")
                desc = kwargs.get("description", "")
                project_id = kwargs.get("project_id", "")
                if not title or not project_id:
                    return SkillResult(
                        success=False, output="", error="title and project_id required."
                    )
                body = {
                    "fields": {
                        "project": {"key": project_id},
                        "summary": title,
                        "description": {
                            "type": "doc",
                            "version": 1,
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"text": desc or title, "type": "text"}],
                                }
                            ],
                        },
                        "issuetype": {"name": "Task"},
                    }
                }
                resp = await client.post(
                    f"{base_url.rstrip('/')}/rest/api/3/issue",
                    headers=headers,
                    json=body,
                )
                resp.raise_for_status()
                issue = resp.json()
                return SkillResult(
                    success=True,
                    output=f"Issue created: {issue.get('key', '')} — {title}",
                )

        return SkillResult(success=False, output="", error=f"Unknown Jira action: {action}")

    # ── Todoist ────────────────────────────────────────────────

    async def _todoist(self, action: str = "", **kwargs: Any) -> SkillResult:
        token = os.getenv("TODOIST_API_TOKEN", "")
        if not token:
            return SkillResult(success=False, output="", error="TODOIST_API_TOKEN required.")

        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        base = "https://api.todoist.com/rest/v2"

        async with httpx.AsyncClient(timeout=15) as client:
            if action == "list":
                resp = await client.get(f"{base}/tasks", headers=headers)
                resp.raise_for_status()
                tasks = resp.json()
                lines = []
                for t in tasks[:30]:
                    priority_map = {4: "P1", 3: "P2", 2: "P3", 1: "P4"}
                    p = priority_map.get(t.get("priority", 1), "P4")
                    due = t.get("due", {})
                    due_str = f" (due: {due.get('date', '')})" if due else ""
                    lines.append(f"- [{p}] {t['content']}{due_str}")
                return SkillResult(success=True, output="\n".join(lines) or "No tasks.")

            elif action == "create":
                title = kwargs.get("title", "")
                desc = kwargs.get("description", "")
                priority = kwargs.get("priority", "")
                if not title:
                    return SkillResult(success=False, output="", error="title required.")
                body: dict[str, Any] = {"content": title}
                if desc:
                    body["description"] = desc
                if priority:
                    priority_map = {"p1": 4, "p2": 3, "p3": 2, "p4": 1}
                    body["priority"] = priority_map.get(priority.lower(), 1)
                resp = await client.post(f"{base}/tasks", headers=headers, json=body)
                resp.raise_for_status()
                task = resp.json()
                return SkillResult(
                    success=True, output=f"Task created: {task['content']} (ID: {task['id']})"
                )

        return SkillResult(success=False, output="", error=f"Unknown Todoist action: {action}")

    # ── Obsidian (local vault) ─────────────────────────────────

    async def _obsidian(self, action: str = "", **kwargs: Any) -> SkillResult:
        vault_path = kwargs.get("vault_path", "") or os.getenv("OBSIDIAN_VAULT_PATH", "")
        if not vault_path:
            return SkillResult(
                success=False,
                output="",
                error="vault_path or OBSIDIAN_VAULT_PATH env var required.",
            )

        from pathlib import Path

        vault = Path(vault_path)
        if not vault.is_dir():
            return SkillResult(success=False, output="", error=f"Vault not found at {vault_path}")

        if action == "list_notes":
            md_files = sorted(vault.rglob("*.md"))
            lines = [str(f.relative_to(vault)) for f in md_files[:50]]
            return SkillResult(
                success=True, output=f"Found {len(md_files)} notes:\n" + "\n".join(lines)
            )

        elif action == "read_note":
            note_path = kwargs.get("note_path", "")
            if not note_path:
                return SkillResult(success=False, output="", error="note_path required.")
            full = vault / note_path
            if not full.exists():
                return SkillResult(success=False, output="", error=f"Note not found: {note_path}")
            content = full.read_text(encoding="utf-8")
            return SkillResult(success=True, output=content[:5000])

        elif action == "write_note":
            note_path = kwargs.get("note_path", "")
            content = kwargs.get("content", "")
            if not note_path or not content:
                return SkillResult(
                    success=False, output="", error="note_path and content required."
                )
            full = vault / note_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
            return SkillResult(success=True, output=f"Note written: {note_path}")

        return SkillResult(success=False, output="", error=f"Unknown Obsidian action: {action}")
