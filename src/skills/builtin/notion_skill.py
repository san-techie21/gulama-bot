"""
Notion integration skill for Gulama.

Actions:
- search: Search Notion pages and databases
- get_page: Get a page's content
- create_page: Create a new page
- update_page: Update page properties
- list_databases: List accessible databases
- query_database: Query a database with filters
- append_block: Append content blocks to a page

Requires: NOTION_TOKEN environment variable or vault secret.
"""

from __future__ import annotations

import os
from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("notion_skill")

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionSkill(BaseSkill):
    """Notion API integration — pages, databases, search."""

    def __init__(self) -> None:
        self._token: str | None = None

    def _get_token(self) -> str:
        if self._token:
            return self._token
        self._token = os.getenv("NOTION_TOKEN", "")
        return self._token or ""

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="notion",
            description="Notion integration — search, create, update pages and databases",
            version="1.0.0",
            author="gulama",
            required_actions=[ActionType.NETWORK_REQUEST],
            is_builtin=True,
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "notion",
                "description": (
                    "Interact with Notion — search pages, manage databases, "
                    "create and update content."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "search",
                                "get_page",
                                "create_page",
                                "update_page",
                                "list_databases",
                                "query_database",
                                "append_block",
                            ],
                        },
                        "query": {"type": "string", "description": "Search query"},
                        "page_id": {"type": "string", "description": "Notion page ID"},
                        "database_id": {"type": "string", "description": "Notion database ID"},
                        "parent_id": {
                            "type": "string",
                            "description": "Parent page/database ID for new pages",
                        },
                        "title": {"type": "string", "description": "Page title"},
                        "content": {
                            "type": "string",
                            "description": "Content to append (markdown-like)",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Properties to set on the page",
                        },
                        "filter": {
                            "type": "object",
                            "description": "Database query filter (Notion filter format)",
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
                success=False,
                output="",
                error="NOTION_TOKEN not configured. Set via env or 'gulama vault set NOTION_TOKEN'",
            )

        dispatch = {
            "search": self._search,
            "get_page": self._get_page,
            "create_page": self._create_page,
            "update_page": self._update_page,
            "list_databases": self._list_databases,
            "query_database": self._query_database,
            "append_block": self._append_block,
        }

        handler = dispatch.get(action)
        if not handler:
            return SkillResult(success=False, output="", error=f"Unknown action: {action}")

        try:
            return await handler(token=token, **{k: v for k, v in kwargs.items() if k != "action"})
        except Exception as e:
            logger.error("notion_error", action=action, error=str(e))
            return SkillResult(success=False, output="", error=f"Notion error: {str(e)[:400]}")

    async def _api(self, token: str, method: str, path: str, json_data: dict | None = None) -> dict:
        import httpx

        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method, f"{NOTION_API}{path}", headers=headers, json=json_data
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {}

    async def _search(self, token: str, query: str = "", **_: Any) -> SkillResult:
        data: dict[str, Any] = {}
        if query:
            data["query"] = query
        data["page_size"] = 10
        results = await self._api(token, "POST", "/search", data)
        lines = []
        for r in results.get("results", []):
            obj_type = r.get("object", "")
            title = ""
            if obj_type == "page":
                props = r.get("properties", {})
                for p in props.values():
                    if p.get("type") == "title":
                        title_items = p.get("title", [])
                        if title_items:
                            title = title_items[0].get("plain_text", "")
                        break
            elif obj_type == "database":
                title_items = r.get("title", [])
                if title_items:
                    title = title_items[0].get("plain_text", "")
            lines.append(f"- [{obj_type}] {title or 'Untitled'} (ID: {r['id'][:8]}...)")
        return SkillResult(success=True, output="\n".join(lines) or "No results found.")

    async def _get_page(self, token: str, page_id: str = "", **_: Any) -> SkillResult:
        if not page_id:
            return SkillResult(success=False, output="", error="page_id is required")
        page = await self._api(token, "GET", f"/pages/{page_id}")
        blocks = await self._api(token, "GET", f"/blocks/{page_id}/children?page_size=50")
        content_lines = []
        for block in blocks.get("results", []):
            block_type = block.get("type", "")
            block_data = block.get(block_type, {})
            texts = block_data.get("rich_text", [])
            text = " ".join(t.get("plain_text", "") for t in texts)
            if text:
                content_lines.append(text)
        props = page.get("properties", {})
        title = ""
        for p in props.values():
            if p.get("type") == "title":
                title_items = p.get("title", [])
                if title_items:
                    title = title_items[0].get("plain_text", "")
                break
        output = f"Title: {title}\nID: {page_id}\n\n" + "\n".join(content_lines)
        return SkillResult(success=True, output=output[:5000])

    async def _create_page(
        self, token: str, parent_id: str = "", title: str = "", content: str = "", **_: Any
    ) -> SkillResult:
        if not parent_id:
            return SkillResult(success=False, output="", error="parent_id is required")
        body: dict[str, Any] = {
            "parent": {"page_id": parent_id},
            "properties": {
                "title": {"title": [{"text": {"content": title or "Untitled"}}]},
            },
        }
        if content:
            body["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": content[:2000]}}],
                    },
                }
            ]
        result = await self._api(token, "POST", "/pages", body)
        return SkillResult(
            success=True,
            output=f"Page created: {result.get('url', result['id'])}",
            metadata={"page_id": result["id"]},
        )

    async def _update_page(
        self, token: str, page_id: str = "", properties: dict | None = None, **_: Any
    ) -> SkillResult:
        if not page_id:
            return SkillResult(success=False, output="", error="page_id is required")
        body: dict[str, Any] = {"properties": properties or {}}
        await self._api(token, "PATCH", f"/pages/{page_id}", body)
        return SkillResult(success=True, output=f"Page {page_id[:8]}... updated.")

    async def _list_databases(self, token: str, **_: Any) -> SkillResult:
        results = await self._api(
            token,
            "POST",
            "/search",
            {"filter": {"property": "object", "value": "database"}, "page_size": 20},
        )
        lines = []
        for db in results.get("results", []):
            title_items = db.get("title", [])
            title = title_items[0].get("plain_text", "Untitled") if title_items else "Untitled"
            lines.append(f"- {title} (ID: {db['id'][:8]}...)")
        return SkillResult(success=True, output="\n".join(lines) or "No databases found.")

    async def _query_database(
        self, token: str, database_id: str = "", filter: dict | None = None, **_: Any
    ) -> SkillResult:
        if not database_id:
            return SkillResult(success=False, output="", error="database_id is required")
        body: dict[str, Any] = {"page_size": 20}
        if filter:
            body["filter"] = filter
        results = await self._api(token, "POST", f"/databases/{database_id}/query", body)
        lines = []
        for page in results.get("results", []):
            props = page.get("properties", {})
            title = ""
            for p in props.values():
                if p.get("type") == "title":
                    title_items = p.get("title", [])
                    if title_items:
                        title = title_items[0].get("plain_text", "")
                    break
            lines.append(f"- {title or 'Untitled'} (ID: {page['id'][:8]}...)")
        return SkillResult(success=True, output="\n".join(lines) or "No results.")

    async def _append_block(
        self, token: str, page_id: str = "", content: str = "", **_: Any
    ) -> SkillResult:
        if not page_id or not content:
            return SkillResult(success=False, output="", error="page_id and content are required")
        body = {
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": content[:2000]}}],
                    },
                }
            ]
        }
        await self._api(token, "PATCH", f"/blocks/{page_id}/children", body)
        return SkillResult(success=True, output="Content appended to page.")
