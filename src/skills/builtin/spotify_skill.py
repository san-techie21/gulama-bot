"""
Spotify integration skill for Gulama.

Actions:
- now_playing: Get currently playing track
- search: Search for tracks, albums, artists, playlists
- play: Start playback (track, album, playlist URI)
- pause: Pause playback
- next: Skip to next track
- previous: Go to previous track
- queue: Add a track to queue
- playlists: List user's playlists
- volume: Set playback volume

Requires: SPOTIFY_ACCESS_TOKEN environment variable.
(OAuth flow must be handled externally or via web UI.)
"""

from __future__ import annotations

import os
from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("spotify_skill")

SPOTIFY_API = "https://api.spotify.com/v1"


class SpotifySkill(BaseSkill):
    """Spotify playback and music search integration."""

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="spotify",
            description="Spotify — search music, control playback, manage playlists",
            version="1.0.0",
            author="gulama",
            required_actions=[ActionType.NETWORK_REQUEST],
            is_builtin=True,
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "spotify",
                "description": "Control Spotify — search music, play/pause, manage playlists and queue.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "now_playing",
                                "search",
                                "play",
                                "pause",
                                "next",
                                "previous",
                                "queue",
                                "playlists",
                                "volume",
                            ],
                        },
                        "query": {"type": "string", "description": "Search query"},
                        "uri": {"type": "string", "description": "Spotify URI to play or queue"},
                        "search_type": {
                            "type": "string",
                            "enum": ["track", "album", "artist", "playlist"],
                            "description": "Type to search for (default: track)",
                        },
                        "volume_percent": {"type": "integer", "description": "Volume level 0-100"},
                    },
                    "required": ["action"],
                },
            },
        }

    def _get_token(self) -> str:
        return os.getenv("SPOTIFY_ACCESS_TOKEN", "")

    async def execute(self, **kwargs: Any) -> SkillResult:
        action = kwargs.get("action", "")
        token = self._get_token()
        if not token:
            return SkillResult(
                success=False,
                output="",
                error=(
                    "Spotify is not configured yet. To enable Spotify integration, "
                    "set the SPOTIFY_ACCESS_TOKEN environment variable in your .env file. "
                    "You can get a token from https://developer.spotify.com/console/. "
                    "Run 'gulama setup' for guided configuration."
                ),
            )

        dispatch = {
            "now_playing": self._now_playing,
            "search": self._search,
            "play": self._play,
            "pause": self._pause,
            "next": self._next,
            "previous": self._previous,
            "queue": self._queue,
            "playlists": self._playlists,
            "volume": self._volume,
        }

        handler = dispatch.get(action)
        if not handler:
            return SkillResult(success=False, output="", error=f"Unknown action: {action}")

        try:
            return await handler(token=token, **{k: v for k, v in kwargs.items() if k != "action"})
        except Exception as e:
            logger.error("spotify_error", action=action, error=str(e))
            return SkillResult(success=False, output="", error=f"Spotify error: {str(e)[:400]}")

    async def _api(self, token: str, method: str, path: str, json_data: dict | None = None) -> dict:
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.request(
                method, f"{SPOTIFY_API}{path}", headers=headers, json=json_data
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {}

    async def _now_playing(self, token: str, **_: Any) -> SkillResult:
        try:
            data = await self._api(token, "GET", "/me/player/currently-playing")
        except Exception:
            return SkillResult(success=True, output="Nothing is currently playing.")
        if not data or not data.get("item"):
            return SkillResult(success=True, output="Nothing is currently playing.")
        item = data["item"]
        artists = ", ".join(a["name"] for a in item.get("artists", []))
        return SkillResult(
            success=True,
            output=f"Now playing: {item['name']} by {artists}\nAlbum: {item.get('album', {}).get('name', 'Unknown')}",
        )

    async def _search(
        self, token: str, query: str = "", search_type: str = "track", **_: Any
    ) -> SkillResult:
        if not query:
            return SkillResult(success=False, output="", error="query is required for search")
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{SPOTIFY_API}/search",
                params={"q": query, "type": search_type, "limit": 10},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        key = f"{search_type}s"
        items = data.get(key, {}).get("items", [])
        lines = []
        for item in items:
            if search_type == "track":
                artists = ", ".join(a["name"] for a in item.get("artists", []))
                lines.append(f"- {item['name']} by {artists} (URI: {item['uri']})")
            elif search_type == "album":
                artists = ", ".join(a["name"] for a in item.get("artists", []))
                lines.append(
                    f"- {item['name']} by {artists} ({item.get('total_tracks', 0)} tracks)"
                )
            elif search_type == "artist":
                lines.append(
                    f"- {item['name']} ({item.get('followers', {}).get('total', 0)} followers)"
                )
            elif search_type == "playlist":
                lines.append(f"- {item['name']} ({item.get('tracks', {}).get('total', 0)} tracks)")
        return SkillResult(success=True, output="\n".join(lines) or "No results found.")

    async def _play(self, token: str, uri: str = "", **_: Any) -> SkillResult:
        body: dict[str, Any] = {}
        if uri:
            if "track" in uri:
                body["uris"] = [uri]
            else:
                body["context_uri"] = uri
        await self._api(token, "PUT", "/me/player/play", body if body else None)
        return SkillResult(
            success=True, output="Playback started." + (f" Playing: {uri}" if uri else "")
        )

    async def _pause(self, token: str, **_: Any) -> SkillResult:
        await self._api(token, "PUT", "/me/player/pause")
        return SkillResult(success=True, output="Playback paused.")

    async def _next(self, token: str, **_: Any) -> SkillResult:
        await self._api(token, "POST", "/me/player/next")
        return SkillResult(success=True, output="Skipped to next track.")

    async def _previous(self, token: str, **_: Any) -> SkillResult:
        await self._api(token, "POST", "/me/player/previous")
        return SkillResult(success=True, output="Went to previous track.")

    async def _queue(self, token: str, uri: str = "", **_: Any) -> SkillResult:
        if not uri:
            return SkillResult(success=False, output="", error="uri is required to add to queue")
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{SPOTIFY_API}/me/player/queue", params={"uri": uri}, headers=headers
            )
            resp.raise_for_status()
        return SkillResult(success=True, output=f"Added to queue: {uri}")

    async def _playlists(self, token: str, **_: Any) -> SkillResult:
        data = await self._api(token, "GET", "/me/playlists?limit=20")
        lines = []
        for p in data.get("items", []):
            lines.append(
                f"- {p['name']} ({p.get('tracks', {}).get('total', 0)} tracks, URI: {p['uri']})"
            )
        return SkillResult(success=True, output="\n".join(lines) or "No playlists found.")

    async def _volume(self, token: str, volume_percent: int = 50, **_: Any) -> SkillResult:
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.put(
                f"{SPOTIFY_API}/me/player/volume",
                params={"volume_percent": max(0, min(100, volume_percent))},
                headers=headers,
            )
            resp.raise_for_status()
        return SkillResult(success=True, output=f"Volume set to {volume_percent}%.")
