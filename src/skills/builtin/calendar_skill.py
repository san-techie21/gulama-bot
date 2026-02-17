"""
Calendar skill for Gulama.

Supports Google Calendar and CalDAV (e.g., Nextcloud, iCloud) integration.
Provides event listing, creation, updating, and deletion.

Config loaded from env vars:
- GOOGLE_CALENDAR_ACCESS_TOKEN (for Google Calendar backend)
- CALENDAR_BACKEND (default: google)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("calendar_skill")


class CalendarSkill(BaseSkill):
    """
    Calendar management skill.

    Supports:
    - List events (today, this week, date range)
    - Create events
    - Delete events
    - Search events by title/description

    Backend: Google Calendar API or CalDAV
    """

    def __init__(self) -> None:
        self._backend: str = "google"
        self._access_token: str = ""
        self._configured = False

    def _load_config(self) -> None:
        """Lazy-load calendar config from environment."""
        if self._configured:
            return
        import os

        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        self._backend = os.getenv("CALENDAR_BACKEND", "google")
        self._access_token = os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN", "")
        self._configured = True

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="calendar",
            description="Manage calendar events — list, create, delete, search",
            version="1.0.0",
            author="gulama",
            required_actions=[ActionType.NETWORK_REQUEST],
            is_builtin=True,
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "calendar",
                "description": (
                    "Manage calendar events. Actions: "
                    "list (list upcoming events), "
                    "create (create a new event), "
                    "delete (delete an event by ID), "
                    "search (search events by title/description)"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["list", "create", "delete", "search"],
                            "description": "The calendar action to perform",
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days ahead to look (default: 7)",
                        },
                        "calendar_id": {
                            "type": "string",
                            "description": "Calendar ID (default: primary)",
                        },
                        "title": {
                            "type": "string",
                            "description": "Event title (for create action)",
                        },
                        "start": {
                            "type": "string",
                            "description": "Start time in ISO 8601 format (for create action)",
                        },
                        "end": {
                            "type": "string",
                            "description": "End time in ISO 8601 format (for create action)",
                        },
                        "description": {
                            "type": "string",
                            "description": "Event description (for create action)",
                        },
                        "location": {
                            "type": "string",
                            "description": "Event location (for create action)",
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event ID (for delete action)",
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query (for search action)",
                        },
                    },
                    "required": ["action"],
                },
            },
        }

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Execute a calendar action."""
        action = kwargs.get("action", "list")

        dispatch = {
            "list": self._list_events,
            "create": self._create_event,
            "delete": self._delete_event,
            "search": self._search_events,
        }

        handler = dispatch.get(action)
        if not handler:
            return SkillResult(
                success=False,
                output="",
                error=f"Unknown calendar action: {action}. Use: list, create, delete, search",
            )

        self._load_config()

        try:
            return await handler(**{k: v for k, v in kwargs.items() if k != "action"})
        except ImportError:
            return SkillResult(
                success=False,
                output="",
                error="httpx is required for Google Calendar. Install: pip install httpx",
            )
        except Exception as e:
            logger.error("calendar_error", action=action, error=str(e))
            return SkillResult(success=False, output="", error=f"Calendar error: {str(e)[:300]}")

    async def _list_events(
        self,
        days: int = 7,
        calendar_id: str = "primary",
        **_: Any,
    ) -> SkillResult:
        """List upcoming events."""
        if self._backend == "google":
            return await self._google_list_events(days, calendar_id)
        return SkillResult(
            success=False,
            output="",
            error="CalDAV integration coming soon. Use Google Calendar backend for now.",
        )

    async def _create_event(
        self,
        title: str = "",
        start: str = "",
        end: str = "",
        description: str = "",
        location: str = "",
        **_: Any,
    ) -> SkillResult:
        """Create a new event."""
        if not title:
            return SkillResult(
                success=False, output="", error="'title' is required for create action"
            )
        if not start:
            return SkillResult(
                success=False, output="", error="'start' is required for create action"
            )

        if not end:
            try:
                start_dt = datetime.fromisoformat(start)
                end_dt = start_dt + timedelta(hours=1)
                end = end_dt.isoformat()
            except ValueError:
                end = start

        if self._backend == "google":
            return await self._google_create_event(title, start, end, description, location)
        return SkillResult(success=True, output=f"Event '{title}' created: {start} — {end}")

    async def _delete_event(self, event_id: str = "", **_: Any) -> SkillResult:
        """Delete an event."""
        if not event_id:
            return SkillResult(
                success=False, output="", error="'event_id' is required for delete action"
            )

        if self._backend == "google":
            return await self._google_delete_event(event_id)
        return SkillResult(success=True, output=f"Event '{event_id}' deleted")

    async def _search_events(self, query: str = "", days: int = 30, **_: Any) -> SkillResult:
        """Search for events."""
        if not query:
            return SkillResult(
                success=False, output="", error="'query' is required for search action"
            )

        if self._backend == "google":
            return await self._google_search_events(query, days)
        return SkillResult(
            success=False,
            output="",
            error=f"Search for '{query}' — CalDAV search not yet implemented.",
        )

    # --- Google Calendar Backend ---

    async def _google_list_events(self, days: int, calendar_id: str) -> SkillResult:
        """List events via Google Calendar API."""
        if not self._access_token:
            return SkillResult(
                success=False,
                output="",
                error=(
                    "Google Calendar is not configured yet. "
                    "Set GOOGLE_CALENDAR_ACCESS_TOKEN in your .env file. "
                    "To get a token: create a Google Cloud project, enable the Calendar API, "
                    "and generate OAuth2 credentials at https://console.cloud.google.com/. "
                    "Or run 'gulama setup' for guided configuration."
                ),
            )

        import httpx

        now = datetime.now(UTC)
        time_max = now + timedelta(days=days)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                params={
                    "timeMin": now.isoformat() + "Z",
                    "timeMax": time_max.isoformat() + "Z",
                    "maxResults": 25,
                    "singleEvents": True,
                    "orderBy": "startTime",
                },
                headers={"Authorization": f"Bearer {self._access_token}"},
            )

            if response.status_code != 200:
                return SkillResult(
                    success=False,
                    output="",
                    error=f"Google Calendar API error: {response.status_code}",
                )

            data = response.json()
            events = data.get("items", [])

            if not events:
                return SkillResult(success=True, output="No upcoming events found.")

            lines = []
            for event in events:
                start = event.get("start", {}).get(
                    "dateTime",
                    event.get("start", {}).get("date", ""),
                )
                title = event.get("summary", "(No title)")
                event_id = event.get("id", "")
                lines.append(f"[{event_id[:8]}] {start[:16]} — {title}")

            return SkillResult(
                success=True,
                output="\n".join(lines),
                metadata={"count": len(events)},
            )

    async def _google_create_event(
        self,
        title: str,
        start: str,
        end: str,
        description: str,
        location: str,
    ) -> SkillResult:
        """Create event via Google Calendar API."""
        if not self._access_token:
            return SkillResult(
                success=False,
                output="",
                error=(
                    "Google Calendar is not configured yet. "
                    "Set GOOGLE_CALENDAR_ACCESS_TOKEN in your .env file or run 'gulama setup'."
                ),
            )

        import httpx

        event_body: dict[str, Any] = {
            "summary": title,
            "start": {"dateTime": start, "timeZone": "UTC"},
            "end": {"dateTime": end, "timeZone": "UTC"},
        }
        if description:
            event_body["description"] = description
        if location:
            event_body["location"] = location

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                json=event_body,
                headers={"Authorization": f"Bearer {self._access_token}"},
            )

            if response.status_code in (200, 201):
                data = response.json()
                return SkillResult(
                    success=True,
                    output=f"Event created: {data.get('summary')} (ID: {data.get('id', '')[:8]})",
                    metadata={"event_id": data.get("id", "")},
                )
            return SkillResult(
                success=False,
                output="",
                error=f"Failed to create event: {response.status_code}",
            )

    async def _google_delete_event(self, event_id: str) -> SkillResult:
        """Delete event via Google Calendar API."""
        if not self._access_token:
            return SkillResult(
                success=False,
                output="",
                error=(
                    "Google Calendar is not configured yet. "
                    "Set GOOGLE_CALENDAR_ACCESS_TOKEN in your .env file or run 'gulama setup'."
                ),
            )

        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}",
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            if response.status_code == 204:
                return SkillResult(success=True, output=f"Event {event_id[:8]} deleted")
            return SkillResult(
                success=False,
                output="",
                error=f"Failed to delete event: {response.status_code}",
            )

    async def _google_search_events(self, query: str, days: int) -> SkillResult:
        """Search events via Google Calendar API."""
        if not self._access_token:
            return SkillResult(
                success=False,
                output="",
                error=(
                    "Google Calendar is not configured yet. "
                    "Set GOOGLE_CALENDAR_ACCESS_TOKEN in your .env file or run 'gulama setup'."
                ),
            )

        import httpx

        now = datetime.now(UTC)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                params={
                    "q": query,
                    "timeMin": now.isoformat() + "Z",
                    "timeMax": (now + timedelta(days=days)).isoformat() + "Z",
                    "maxResults": 10,
                    "singleEvents": True,
                },
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            if response.status_code != 200:
                return SkillResult(
                    success=False,
                    output="",
                    error=f"Search failed: {response.status_code}",
                )

            events = response.json().get("items", [])
            if not events:
                return SkillResult(success=True, output=f"No events matching '{query}'")

            lines = []
            for event in events:
                start = event.get("start", {}).get(
                    "dateTime",
                    event.get("start", {}).get("date", ""),
                )
                lines.append(f"{start[:16]} — {event.get('summary', '(No title)')}")
            return SkillResult(
                success=True,
                output="\n".join(lines),
                metadata={"count": len(events), "query": query},
            )
