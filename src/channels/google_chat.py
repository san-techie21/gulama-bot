"""
Google Chat channel adapter for Gulama.

Uses Google Chat API for bot messaging.
Supports direct messages and room mentions.

Requires: Google service account with Chat API enabled.
Environment: GOOGLE_CHAT_SERVICE_ACCOUNT_FILE
"""

from __future__ import annotations

from typing import Any

from src.channels.base import BaseChannel
from src.utils.logging import get_logger

logger = get_logger("google_chat_channel")


class GoogleChatChannel(BaseChannel):
    """Google Chat (Workspace) channel."""

    def __init__(self, allowed_spaces: list[str] | None = None) -> None:
        super().__init__()
        self.allowed_spaces = set(allowed_spaces) if allowed_spaces else None

    async def handle_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Handle an incoming Google Chat event (webhook payload).

        Events:
        - ADDED_TO_SPACE: Bot added to room
        - MESSAGE: User sent a message
        - REMOVED_FROM_SPACE: Bot removed
        """
        event_type = event.get("type", "")

        if event_type == "ADDED_TO_SPACE":
            return {"text": "Hello! I'm Gulama, your secure AI assistant. How can I help?"}

        if event_type == "REMOVED_FROM_SPACE":
            return {}

        if event_type != "MESSAGE":
            return {}

        message = event.get("message", {})
        text = message.get("argumentText", "") or message.get("text", "")
        text = text.strip()

        sender = message.get("sender", {})
        user_id = sender.get("name", "unknown")
        display_name = sender.get("displayName", "unknown")
        space = message.get("space", {}).get("name", "")

        # Space whitelist
        if self.allowed_spaces and space not in self.allowed_spaces:
            return {"text": "I'm not authorized in this space."}

        if not text:
            return {"text": "Please send a message for me to respond to."}

        logger.info("google_chat_message", user=display_name, length=len(text))

        try:
            result = await self.process_message(
                message=text,
                user_id=user_id,
                channel_data={"space": space, "display_name": display_name},
            )
            return {"text": result.get("response", "I couldn't process that.")}
        except Exception as e:
            logger.error("google_chat_error", error=str(e))
            return {"text": f"Error: {str(e)[:200]}"}

    def run(self) -> None:
        """
        Google Chat uses webhooks. Start gateway and configure:
        POST /api/v1/channels/google-chat/webhook
        """
        logger.info(
            "google_chat_info",
            message="Google Chat uses webhooks. Start gateway and configure webhook URL.",
        )
