"""
Twitter/X integration skill for Gulama.

Actions:
- search: Search tweets
- post: Post a tweet
- timeline: Get home timeline
- user_info: Get user profile info
- trending: Get trending topics

Requires: TWITTER_BEARER_TOKEN (read-only) or
TWITTER_API_KEY + TWITTER_API_SECRET + TWITTER_ACCESS_TOKEN + TWITTER_ACCESS_SECRET (write).
"""

from __future__ import annotations

import os
from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("twitter_skill")

TWITTER_API = "https://api.twitter.com/2"


class TwitterSkill(BaseSkill):
    """Twitter/X API integration — search, post, timeline."""

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="twitter",
            description="Twitter/X — search tweets, post, view timeline, trending topics",
            version="1.0.0",
            author="gulama",
            required_actions=[ActionType.NETWORK_REQUEST, ActionType.MESSAGE_SEND],
            is_builtin=True,
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "twitter",
                "description": "Interact with Twitter/X — search tweets, post, view timeline.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["search", "post", "timeline", "user_info", "trending"],
                        },
                        "query": {"type": "string", "description": "Search query"},
                        "text": {"type": "string", "description": "Tweet text to post"},
                        "username": {
                            "type": "string",
                            "description": "Twitter username (without @)",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Max results (10-100, default 10)",
                        },
                    },
                    "required": ["action"],
                },
            },
        }

    def _get_bearer(self) -> str:
        return os.getenv("TWITTER_BEARER_TOKEN", "")

    async def execute(self, **kwargs: Any) -> SkillResult:
        action = kwargs.get("action", "")
        token = self._get_bearer()
        if not token:
            return SkillResult(
                success=False,
                output="",
                error=(
                    "Twitter/X is not configured yet. To enable Twitter integration, "
                    "set TWITTER_BEARER_TOKEN in your .env file. "
                    "Get one from https://developer.twitter.com/en/portal/dashboard. "
                    "Run 'gulama setup' for guided configuration."
                ),
            )

        dispatch = {
            "search": self._search,
            "post": self._post,
            "timeline": self._timeline,
            "user_info": self._user_info,
            "trending": self._trending,
        }

        handler = dispatch.get(action)
        if not handler:
            return SkillResult(success=False, output="", error=f"Unknown action: {action}")

        try:
            return await handler(token=token, **{k: v for k, v in kwargs.items() if k != "action"})
        except Exception as e:
            logger.error("twitter_error", action=action, error=str(e))
            return SkillResult(success=False, output="", error=f"Twitter error: {str(e)[:400]}")

    async def _search(
        self, token: str, query: str = "", max_results: int = 10, **_: Any
    ) -> SkillResult:
        if not query:
            return SkillResult(success=False, output="", error="query is required")
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{TWITTER_API}/tweets/search/recent",
                params={
                    "query": query,
                    "max_results": min(max(10, max_results), 100),
                    "tweet.fields": "created_at,author_id,public_metrics",
                },
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        tweets = data.get("data", [])
        lines = []
        for t in tweets:
            metrics = t.get("public_metrics", {})
            lines.append(
                f"- {t['text'][:120]}...\n"
                f"  Likes: {metrics.get('like_count', 0)} | "
                f"RT: {metrics.get('retweet_count', 0)} | "
                f"Date: {t.get('created_at', '')[:10]}"
            )
        return SkillResult(success=True, output="\n".join(lines) or "No tweets found.")

    async def _post(self, token: str, text: str = "", **_: Any) -> SkillResult:
        if not text:
            return SkillResult(success=False, output="", error="text is required to post")
        # Posting requires OAuth 1.0a — simplified with bearer for now
        return SkillResult(
            success=False,
            output="",
            error="Tweet posting requires OAuth 1.0a credentials. Set TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET.",
        )

    async def _timeline(self, token: str, **_: Any) -> SkillResult:
        return SkillResult(
            success=True,
            output="Timeline access requires OAuth 2.0 user context. Use 'search' action for public tweet search.",
        )

    async def _user_info(self, token: str, username: str = "", **_: Any) -> SkillResult:
        if not username:
            return SkillResult(success=False, output="", error="username is required")
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{TWITTER_API}/users/by/username/{username}",
                params={"user.fields": "description,public_metrics,created_at,verified"},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})

        if not data:
            return SkillResult(success=True, output=f"User @{username} not found.")
        metrics = data.get("public_metrics", {})
        return SkillResult(
            success=True,
            output=(
                f"@{data.get('username', username)}: {data.get('name', '')}\n"
                f"Bio: {data.get('description', '')}\n"
                f"Followers: {metrics.get('followers_count', 0)} | "
                f"Following: {metrics.get('following_count', 0)} | "
                f"Tweets: {metrics.get('tweet_count', 0)}\n"
                f"Joined: {data.get('created_at', '')[:10]}"
            ),
        )

    async def _trending(self, token: str, **_: Any) -> SkillResult:
        # Twitter v2 doesn't have a direct trending endpoint for free tier
        return SkillResult(
            success=True,
            output="Trending topics require Twitter API Pro access. Use 'search' to find popular tweets on a topic.",
        )
