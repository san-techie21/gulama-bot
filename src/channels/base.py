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

    @abc.abstractmethod
    def stop(self) -> None:
        """Gracefully stop the channel."""
        ...

    @property
    def is_running(self) -> bool:
        return self._running
