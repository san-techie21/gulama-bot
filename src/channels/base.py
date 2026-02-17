"""
Base channel interface for Gulama.

All messaging channels (CLI, Telegram, Discord, WhatsApp, Web)
implement this interface.
"""

from __future__ import annotations

import abc
from typing import Any


class BaseChannel(abc.ABC):
    """
    Abstract base class for all Gulama messaging channels.

    Each channel must implement:
    - run(): Start the channel event loop
    - send_message(): Send a message to the user
    - stop(): Gracefully stop the channel
    """

    def __init__(self, channel_name: str = "base"):
        self.channel_name = channel_name
        self._running = False

    @abc.abstractmethod
    def run(self) -> None:
        """Start the channel event loop (blocking)."""
        ...

    @abc.abstractmethod
    async def send_message(self, user_id: str, content: str, **kwargs: Any) -> None:
        """Send a message to a user."""
        ...

    def stop(self) -> None:
        """Gracefully stop the channel."""
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    async def process_message(
        self,
        message: str,
        user_id: str | None = None,
        channel_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process a user message through AgentBrain.

        This is a convenience method used by webhook-based channels
        (Matrix, Teams, Google Chat) that don't manage their own brain instance.
        """
        from src.agent.brain import AgentBrain
        from src.gateway.config import load_config

        config = load_config()
        brain = AgentBrain(config=config)

        result = await brain.process_message(
            message=message,
            channel=self.channel_name,
            user_id=user_id,
        )
        return result
