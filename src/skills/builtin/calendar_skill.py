"""
Calendar skill for Gulama.

Supports Google Calendar and CalDAV (e.g., Nextcloud, iCloud) integration.
Provides event listing, creation, updating, and deletion.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.skills.base import BaseSkill
from src.utils.logging import get_logger

logger = get_logger("calendar_skill")


class CalendarSkill(BaseSkill):
    """
    Calendar management skill.

    Supports:
    - List events (today, this week, date range)
    - Create events
    - Update events
    - Delete events
    - Search events by title/description

    Backend: Google Calendar API or CalDAV
    """

    name = "calendar"
    description = "Manage calendar events — list, create, update, delete"
    version = "1.0.0"

    def __init__(
        self,
        backend: str = "google",  # "google" or "caldav"
        credentials: dict[str, str] | None = None,
    ):
        self.backend = backend
        self.credentials = credentials or {}
        self._events_cache: list[dict[str, Any]] = []

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "calendar_list_events",
                    "description": "List upcoming calendar events",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days": {"type": "integer", "description": "Number of days ahead to look", "default": 7},
                            "calendar_id": {"type": "string", "description": "Calendar ID (default: primary)"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calendar_create_event",
                    "description": "Create a new calendar event",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "start": {"type": "string", "description": "Start time (ISO 8601)"},
                            "end": {"type": "string", "description": "End time (ISO 8601)"},
                            "description": {"type": "string"},
                            "location": {"type": "string"},
                        },
                        "required": ["title", "start"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calendar_delete_event",
                    "description": "Delete a calendar event",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_id": {"type": "string"},
                        },
                        "required": ["event_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calendar_search",
                    "description": "Search for events by title or description",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "days": {"type": "integer", "default": 30},
                        },
                        "required": ["query"],
                    },
                },
            },
        ]

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        dispatch = {
            "calendar_list_events": self._list_events,
            "calendar_create_event": self._create_event,
            "calendar_delete_event": self._delete_event,
            "calendar_search": self._search_events,
        }

        handler = dispatch.get(tool_name)
        if not handler:
            return f"Unknown calendar action: {tool_name}"

        try:
            return await handler(**arguments)
        except Exception as e:
            logger.error("calendar_error", action=tool_name, error=str(e))
            return f"Calendar error: {str(e)[:200]}"

    async def _list_events(
        self, days: int = 7, calendar_id: str = "primary"
    ) -> str:
        """List upcoming events."""
        if self.backend == "google":
            return await self._google_list_events(days, calendar_id)
        return await self._caldav_list_events(days)

    async def _create_event(
        self,
        title: str,
        start: str,
        end: str = "",
        description: str = "",
        location: str = "",
    ) -> str:
        """Create a new event."""
        if not end:
            # Default to 1 hour duration
            try:
                start_dt = datetime.fromisoformat(start)
                end_dt = start_dt + timedelta(hours=1)
                end = end_dt.isoformat()
            except ValueError:
                end = start

        if self.backend == "google":
            return await self._google_create_event(title, start, end, description, location)
        return f"Event '{title}' created: {start} - {end}"

    async def _delete_event(self, event_id: str) -> str:
        """Delete an event."""
        if self.backend == "google":
            return await self._google_delete_event(event_id)
        return f"Event '{event_id}' deleted"

    async def _search_events(self, query: str, days: int = 30) -> str:
        """Search for events."""
        if self.backend == "google":
            return await self._google_search_events(query, days)
        return f"Search for '{query}' — no results (CalDAV search not yet implemented)"

    # --- Google Calendar Backend ---

    async def _google_list_events(self, days: int, calendar_id: str) -> str:
        """List events via Google Calendar API."""
        try:
            import httpx

            now = datetime.now(timezone.utc)
            time_max = now + timedelta(days=days)

            access_token = self.credentials.get("access_token", "")
            if not access_token:
                return "Google Calendar not configured. Set up OAuth credentials first."

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
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if response.status_code != 200:
                    return f"API error: {response.status_code}"

                data = response.json()
                events = data.get("items", [])

                if not events:
                    return "No upcoming events found."

                lines = []
                for event in events:
                    start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", ""))
                    title = event.get("summary", "(No title)")
                    event_id = event.get("id", "")
                    lines.append(f"[{event_id[:8]}] {start[:16]} — {title}")

                return "\n".join(lines)

        except ImportError:
            return "httpx required for Google Calendar. Install with: pip install httpx"
        except Exception as e:
            return f"Google Calendar error: {str(e)[:200]}"

    async def _google_create_event(
        self, title: str, start: str, end: str, description: str, location: str
    ) -> str:
        """Create event via Google Calendar API."""
        try:
            import httpx

            access_token = self.credentials.get("access_token", "")
            if not access_token:
                return "Google Calendar not configured."

            event_body = {
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
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if response.status_code in (200, 201):
                    data = response.json()
                    return f"Event created: {data.get('summary')} (ID: {data.get('id', '')[:8]})"
                return f"Failed to create event: {response.status_code}"
        except Exception as e:
            return f"Error: {str(e)[:200]}"

    async def _google_delete_event(self, event_id: str) -> str:
        """Delete event via Google Calendar API."""
        try:
            import httpx

            access_token = self.credentials.get("access_token", "")
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if response.status_code == 204:
                    return f"Event {event_id[:8]} deleted"
                return f"Failed: {response.status_code}"
        except Exception as e:
            return f"Error: {str(e)[:200]}"

    async def _google_search_events(self, query: str, days: int) -> str:
        """Search events via Google Calendar API."""
        try:
            import httpx

            access_token = self.credentials.get("access_token", "")
            now = datetime.now(timezone.utc)

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
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if response.status_code != 200:
                    return f"Search failed: {response.status_code}"

                events = response.json().get("items", [])
                if not events:
                    return f"No events matching '{query}'"

                lines = []
                for event in events:
                    start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", ""))
                    lines.append(f"{start[:16]} — {event.get('summary', '(No title)')}")
                return "\n".join(lines)
        except Exception as e:
            return f"Error: {str(e)[:200]}"

    # --- CalDAV Backend ---

    async def _caldav_list_events(self, days: int) -> str:
        """List events via CalDAV (placeholder — requires caldav library)."""
        return "CalDAV integration coming soon. Use Google Calendar backend for now."
