"""
Google Workspace integration skill for Gulama.

Actions:
- docs_get: Get a Google Doc's content
- docs_create: Create a new Google Doc
- docs_append: Append text to a Google Doc
- sheets_read: Read data from a Google Sheet
- sheets_write: Write data to a Google Sheet
- drive_list: List files in Google Drive
- drive_search: Search Google Drive

Requires: Google service account credentials JSON at GOOGLE_SERVICE_ACCOUNT_FILE,
or GOOGLE_API_KEY for read-only access.
"""

from __future__ import annotations

import os
from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("google_docs_skill")


class GoogleDocsSkill(BaseSkill):
    """Google Workspace integration — Docs, Sheets, Drive."""

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="google_docs",
            description="Google Workspace — Docs, Sheets, Drive (read, create, edit, search)",
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
                "name": "google_docs",
                "description": "Google Workspace — read/create Docs, read/write Sheets, search Drive.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "docs_get",
                                "docs_create",
                                "docs_append",
                                "sheets_read",
                                "sheets_write",
                                "drive_list",
                                "drive_search",
                            ],
                        },
                        "document_id": {"type": "string", "description": "Google Doc or Sheet ID"},
                        "title": {"type": "string"},
                        "content": {
                            "type": "string",
                            "description": "Text content to create/append",
                        },
                        "sheet_range": {
                            "type": "string",
                            "description": "Sheet range (e.g., 'Sheet1!A1:D10')",
                        },
                        "values": {
                            "type": "array",
                            "description": "2D array of values to write to sheet",
                            "items": {"type": "array", "items": {"type": "string"}},
                        },
                        "query": {"type": "string", "description": "Search query for Drive"},
                    },
                    "required": ["action"],
                },
            },
        }

    def _get_credentials(self) -> Any:
        """Get Google API credentials."""
        cred_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
        if not cred_file:
            return None
        try:
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/documents",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
            return Credentials.from_service_account_file(cred_file, scopes=scopes)
        except Exception as e:
            logger.warning("google_credentials_error", error=str(e))
            return None

    async def execute(self, **kwargs: Any) -> SkillResult:
        action = kwargs.get("action", "")

        dispatch = {
            "docs_get": self._docs_get,
            "docs_create": self._docs_create,
            "docs_append": self._docs_append,
            "sheets_read": self._sheets_read,
            "sheets_write": self._sheets_write,
            "drive_list": self._drive_list,
            "drive_search": self._drive_search,
        }

        handler = dispatch.get(action)
        if not handler:
            return SkillResult(success=False, output="", error=f"Unknown action: {action}")

        creds = self._get_credentials()
        if not creds:
            api_key = os.getenv("GOOGLE_API_KEY", "")
            if not api_key:
                return SkillResult(
                    success=False,
                    output="",
                    error=(
                        "Google Workspace (Docs/Sheets/Drive) is not configured yet. "
                        "Set GOOGLE_SERVICE_ACCOUNT_FILE (path to service account JSON) "
                        "or GOOGLE_API_KEY (for read-only access) in your .env file. "
                        "Create credentials at https://console.cloud.google.com/ "
                        "(enable Docs, Sheets, and Drive APIs). "
                        "Or run 'gulama setup' for guided configuration."
                    ),
                )

        try:
            return await handler(creds=creds, **{k: v for k, v in kwargs.items() if k != "action"})
        except ImportError:
            return SkillResult(
                success=False,
                output="",
                error="Google API client required. Install: pip install google-api-python-client google-auth",
            )
        except Exception as e:
            logger.error("google_docs_error", action=action, error=str(e))
            return SkillResult(success=False, output="", error=f"Google error: {str(e)[:400]}")

    async def _docs_get(self, creds: Any = None, document_id: str = "", **_: Any) -> SkillResult:
        if not document_id:
            return SkillResult(success=False, output="", error="document_id is required")
        from googleapiclient.discovery import build

        service = build("docs", "v1", credentials=creds)
        doc = service.documents().get(documentId=document_id).execute()
        title = doc.get("title", "Untitled")
        content_parts = []
        for elem in doc.get("body", {}).get("content", []):
            para = elem.get("paragraph", {})
            for el in para.get("elements", []):
                text_run = el.get("textRun", {})
                content_parts.append(text_run.get("content", ""))
        text = "".join(content_parts)
        return SkillResult(success=True, output=f"Title: {title}\n\n{text[:5000]}")

    async def _docs_create(
        self, creds: Any = None, title: str = "", content: str = "", **_: Any
    ) -> SkillResult:
        from googleapiclient.discovery import build

        service = build("docs", "v1", credentials=creds)
        doc = service.documents().create(body={"title": title or "Untitled"}).execute()
        doc_id = doc["documentId"]
        if content:
            service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
            ).execute()
        return SkillResult(
            success=True,
            output=f"Document created: https://docs.google.com/document/d/{doc_id}",
            metadata={"document_id": doc_id},
        )

    async def _docs_append(
        self, creds: Any = None, document_id: str = "", content: str = "", **_: Any
    ) -> SkillResult:
        if not document_id or not content:
            return SkillResult(success=False, output="", error="document_id and content required")
        from googleapiclient.discovery import build

        service = build("docs", "v1", credentials=creds)
        doc = service.documents().get(documentId=document_id).execute()
        end_index = doc.get("body", {}).get("content", [{}])[-1].get("endIndex", 1) - 1
        service.documents().batchUpdate(
            documentId=document_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": max(1, end_index)},
                            "text": "\n" + content,
                        }
                    }
                ]
            },
        ).execute()
        return SkillResult(success=True, output="Content appended to document.")

    async def _sheets_read(
        self,
        creds: Any = None,
        document_id: str = "",
        sheet_range: str = "Sheet1!A1:Z100",
        **_: Any,
    ) -> SkillResult:
        if not document_id:
            return SkillResult(
                success=False, output="", error="document_id (spreadsheet ID) required"
            )
        from googleapiclient.discovery import build

        service = build("sheets", "v4", credentials=creds)
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=document_id, range=sheet_range)
            .execute()
        )
        values = result.get("values", [])
        if not values:
            return SkillResult(success=True, output="No data found.")
        lines = []
        for row in values[:50]:
            lines.append(" | ".join(str(c) for c in row))
        return SkillResult(success=True, output="\n".join(lines))

    async def _sheets_write(
        self,
        creds: Any = None,
        document_id: str = "",
        sheet_range: str = "",
        values: list | None = None,
        **_: Any,
    ) -> SkillResult:
        if not document_id or not sheet_range or not values:
            return SkillResult(
                success=False, output="", error="document_id, sheet_range, and values required"
            )
        from googleapiclient.discovery import build

        service = build("sheets", "v4", credentials=creds)
        service.spreadsheets().values().update(
            spreadsheetId=document_id,
            range=sheet_range,
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute()
        return SkillResult(success=True, output=f"Data written to {sheet_range}.")

    async def _drive_list(self, creds: Any = None, **_: Any) -> SkillResult:
        from googleapiclient.discovery import build

        service = build("drive", "v3", credentials=creds)
        results = (
            service.files()
            .list(pageSize=20, fields="files(id,name,mimeType,modifiedTime)")
            .execute()
        )
        files = results.get("files", [])
        lines = []
        for f in files:
            lines.append(
                f"- {f['name']} ({f.get('mimeType', '')}) modified: {f.get('modifiedTime', '')[:10]}"
            )
        return SkillResult(success=True, output="\n".join(lines) or "No files found.")

    async def _drive_search(self, creds: Any = None, query: str = "", **_: Any) -> SkillResult:
        if not query:
            return SkillResult(success=False, output="", error="query is required")
        from googleapiclient.discovery import build

        service = build("drive", "v3", credentials=creds)
        # Sanitize query to prevent injection in Drive search query syntax
        safe_query = query.replace("\\", "\\\\").replace("'", "\\'")
        results = (
            service.files()
            .list(
                q=f"name contains '{safe_query}'",
                pageSize=20,
                fields="files(id,name,mimeType,modifiedTime)",
            )
            .execute()
        )
        files = results.get("files", [])
        lines = [f"- {f['name']} (ID: {f['id'][:8]}...) {f.get('mimeType', '')}" for f in files]
        return SkillResult(success=True, output="\n".join(lines) or "No files found.")
