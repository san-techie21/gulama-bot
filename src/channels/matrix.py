"""
Matrix channel adapter for Gulama.

Supports end-to-end encrypted messaging via Matrix protocol.
Uses matrix-nio library for Matrix homeserver communication.

Requires: pip install matrix-nio[e2e]
Environment: MATRIX_HOMESERVER, MATRIX_USER_ID, MATRIX_ACCESS_TOKEN
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.channels.base import BaseChannel
from src.utils.logging import get_logger

logger = get_logger("matrix_channel")


class MatrixChannel(BaseChannel):
    """Matrix messenger channel with E2E encryption support."""

    def __init__(
        self,
        homeserver: str = "",
        user_id: str = "",
        access_token: str = "",
        allowed_rooms: list[str] | None = None,
    ) -> None:
        super().__init__(channel_name="matrix")
        self.homeserver = homeserver
        self.user_id = user_id
        self.access_token = access_token
        self.allowed_rooms = set(allowed_rooms) if allowed_rooms else None
        self._client: Any = None

    async def send_message(self, user_id: str, content: str, **kwargs: Any) -> None:
        """Send a message to a Matrix room."""
        room_id = kwargs.get("room_id", "")
        if not self._client or not room_id:
            logger.warning("matrix_send_failed", reason="No client or room_id")
            return
        await self._client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": content},
        )

    async def _setup_client(self) -> None:
        """Initialize the Matrix client."""
        from nio import AsyncClient, MatrixRoom, RoomMessageText

        self._client = AsyncClient(self.homeserver, self.user_id)
        self._client.access_token = self.access_token

        @self._client.event_callback
        async def on_message(room: MatrixRoom, event: RoomMessageText) -> None:
            # Ignore own messages
            if event.sender == self.user_id:
                return

            # Room whitelist check
            if self.allowed_rooms and room.room_id not in self.allowed_rooms:
                return

            logger.info(
                "matrix_message",
                room=room.room_id,
                sender=event.sender,
                length=len(event.body),
            )

            try:
                result = await self.process_message(
                    message=event.body,
                    user_id=event.sender,
                    channel_data={"room_id": room.room_id},
                )
                response_text = result.get("response", "I couldn't process that.")

                await self._client.room_send(
                    room_id=room.room_id,
                    message_type="m.room.message",
                    content={
                        "msgtype": "m.text",
                        "body": response_text,
                    },
                )
            except Exception as e:
                logger.error("matrix_response_error", error=str(e))
                await self._client.room_send(
                    room_id=room.room_id,
                    message_type="m.room.message",
                    content={
                        "msgtype": "m.text",
                        "body": f"Error: {str(e)[:200]}",
                    },
                )

    def run(self) -> None:
        """Start the Matrix bot."""
        import os

        self.homeserver = self.homeserver or os.getenv("MATRIX_HOMESERVER", "https://matrix.org")
        self.user_id = self.user_id or os.getenv("MATRIX_USER_ID", "")
        self.access_token = self.access_token or os.getenv("MATRIX_ACCESS_TOKEN", "")

        if not self.user_id or not self.access_token:
            logger.error("matrix_missing_credentials")
            return

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self._setup_client())
            logger.info("matrix_bot_started", user=self.user_id)
            loop.run_until_complete(self._client.sync_forever(timeout=30000))
        except KeyboardInterrupt:
            logger.info("matrix_bot_stopped")
        finally:
            loop.run_until_complete(self._client.close())
            loop.close()
