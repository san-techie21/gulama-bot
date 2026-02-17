"""
Microsoft Teams channel adapter for Gulama.

Uses the Bot Framework SDK for Teams integration.
Supports incoming webhook messages and outgoing responses.

Requires: pip install botbuilder-core botbuilder-schema
Environment: TEAMS_APP_ID, TEAMS_APP_PASSWORD
"""

from __future__ import annotations

from typing import Any

from src.channels.base import BaseChannel
from src.utils.logging import get_logger

logger = get_logger("teams_channel")


class TeamsChannel(BaseChannel):
    """Microsoft Teams channel via Bot Framework."""

    def __init__(
        self,
        app_id: str = "",
        app_password: str = "",
        allowed_user_ids: list[str] | None = None,
    ) -> None:
        super().__init__(channel_name="teams")
        self.app_id = app_id
        self.app_password = app_password
        self.allowed_user_ids = set(allowed_user_ids) if allowed_user_ids else None

    async def send_message(self, user_id: str, content: str, **kwargs: Any) -> None:
        """Send a message via Teams webhook response."""
        logger.info("teams_send", user=user_id, length=len(content))

    async def handle_activity(self, activity: dict[str, Any]) -> dict[str, Any]:
        """
        Handle an incoming Teams activity (webhook payload).

        This is called by the gateway when a Teams webhook message arrives.
        """
        activity_type = activity.get("type", "")
        if activity_type != "message":
            return {"type": "ignored"}

        text = activity.get("text", "").strip()
        sender = activity.get("from", {})
        user_id = sender.get("id", "unknown")
        user_name = sender.get("name", "unknown")
        conversation_id = activity.get("conversation", {}).get("id", "")

        # User whitelist
        if self.allowed_user_ids and user_id not in self.allowed_user_ids:
            logger.warning("teams_unauthorized", user=user_id)
            return {"type": "unauthorized"}

        # Strip bot mention from text
        entities = activity.get("entities", [])
        for entity in entities:
            if entity.get("type") == "mention":
                mentioned = entity.get("text", "")
                text = text.replace(mentioned, "").strip()

        if not text:
            return {"type": "empty"}

        logger.info("teams_message", user=user_name, length=len(text))

        try:
            result = await self.process_message(
                message=text,
                user_id=user_id,
                channel_data={
                    "conversation_id": conversation_id,
                    "user_name": user_name,
                },
            )
            return {
                "type": "message",
                "text": result.get("response", "I couldn't process that."),
                "conversation_id": conversation_id,
            }
        except Exception as e:
            logger.error("teams_error", error=str(e))
            return {"type": "error", "text": f"Error: {str(e)[:200]}"}

    def run(self) -> None:
        """
        Teams uses webhook-based communication.
        Start the gateway server and configure Teams to point to:
        POST /api/v1/channels/teams/webhook
        """
        logger.info(
            "teams_channel_info",
            message="Teams uses webhooks. Start gateway and point Teams to /api/v1/channels/teams/webhook",
        )
