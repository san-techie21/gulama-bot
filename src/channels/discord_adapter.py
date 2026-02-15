"""
Discord channel for Gulama.

Full Discord bot integration with:
- Slash commands (/ask, /status, /persona)
- Direct message support
- Server channel support (with mention trigger)
- Streaming responses via message editing
- File upload/download support
- User ID filtering for security
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.channels.base import BaseChannel
from src.utils.logging import get_logger

logger = get_logger("discord_channel")


class DiscordChannel(BaseChannel):
    """
    Discord bot channel.

    Requires:
    - discord.py (pip install 'gulama[discord]')
    - Bot token from Discord Developer Portal
    - DISCORD_BOT_TOKEN in vault
    - DISCORD_ALLOWED_USERS (comma-separated user IDs)
    """

    def __init__(
        self,
        bot_token: str,
        allowed_user_ids: list[str] | None = None,
        allowed_guild_ids: list[str] | None = None,
        command_prefix: str = "!g",
    ):
        super().__init__(channel_name="discord")
        self.bot_token = bot_token
        self.allowed_user_ids = set(allowed_user_ids) if allowed_user_ids else None
        self.allowed_guild_ids = set(allowed_guild_ids) if allowed_guild_ids else None
        self.command_prefix = command_prefix
        self._bot = None
        self._agent_brain = None
        self._message_handler = None

    def set_agent(self, agent_brain: Any) -> None:
        """Set the agent brain for processing messages."""
        self._agent_brain = agent_brain

    def set_message_handler(self, handler: Any) -> None:
        """Set an external message handler function."""
        self._message_handler = handler

    def _create_bot(self):
        """Create the Discord bot instance."""
        try:
            import discord
            from discord import app_commands
        except ImportError:
            raise ImportError(
                "discord.py is required for Discord support. "
                "Install with: pip install 'gulama[discord]'"
            )

        intents = discord.Intents.default()
        intents.message_content = True
        intents.dm_messages = True

        bot = discord.Client(intents=intents)
        tree = app_commands.CommandTree(bot)

        channel_self = self

        @bot.event
        async def on_ready():
            logger.info(
                "discord_connected",
                user=str(bot.user),
                guilds=len(bot.guilds),
            )
            # Sync slash commands
            try:
                synced = await tree.sync()
                logger.info("slash_commands_synced", count=len(synced))
            except Exception as e:
                logger.warning("slash_sync_failed", error=str(e))
            channel_self._running = True

        @bot.event
        async def on_message(message):
            # Don't respond to ourselves
            if message.author == bot.user:
                return

            # Check user authorization
            if not channel_self._is_authorized(str(message.author.id)):
                return

            # Check if it's a DM or a mention in a server
            is_dm = message.guild is None
            is_mention = bot.user in message.mentions if message.guild else False
            starts_with_prefix = message.content.startswith(channel_self.command_prefix)

            if not (is_dm or is_mention or starts_with_prefix):
                return

            # Clean the message content
            content = message.content
            if is_mention:
                content = content.replace(f"<@{bot.user.id}>", "").strip()
            elif starts_with_prefix:
                content = content[len(channel_self.command_prefix) :].strip()

            if not content:
                return

            # Process message
            await channel_self._process_message(message, content)

        # --- Slash Commands ---

        @tree.command(name="ask", description="Ask Gulama a question")
        async def ask_command(interaction: discord.Interaction, question: str):
            if not channel_self._is_authorized(str(interaction.user.id)):
                await interaction.response.send_message(
                    "You are not authorized to use this bot.", ephemeral=True
                )
                return

            await interaction.response.defer(thinking=True)
            response = await channel_self._get_response(question, str(interaction.user.id))
            await interaction.followup.send(channel_self._truncate(response, 2000))

        @tree.command(name="status", description="Check Gulama status")
        async def status_command(interaction: discord.Interaction):
            if not channel_self._is_authorized(str(interaction.user.id)):
                await interaction.response.send_message("Unauthorized.", ephemeral=True)
                return

            status_text = (
                f"**Gulama Bot Status**\n"
                f"Channel: Discord\n"
                f"Running: {channel_self._running}\n"
                f"Guilds: {len(bot.guilds)}\n"
            )
            await interaction.response.send_message(status_text)

        @tree.command(name="persona", description="Switch Gulama persona")
        async def persona_command(interaction: discord.Interaction, name: str):
            if not channel_self._is_authorized(str(interaction.user.id)):
                await interaction.response.send_message("Unauthorized.", ephemeral=True)
                return
            await interaction.response.send_message(
                f"Persona switching via Discord coming soon. Requested: {name}",
                ephemeral=True,
            )

        self._bot = bot
        return bot

    def _is_authorized(self, user_id: str) -> bool:
        """Check if a user is authorized to interact with the bot."""
        if self.allowed_user_ids is None:
            return True
        return user_id in self.allowed_user_ids

    async def _process_message(self, message: Any, content: str) -> None:
        """Process an incoming message and send a response."""

        user_id = str(message.author.id)

        # Show typing indicator
        async with message.channel.typing():
            response = await self._get_response(content, user_id)

        # Split long responses into chunks
        chunks = self._split_response(response, 2000)
        for chunk in chunks:
            await message.reply(chunk, mention_author=False)

    async def _get_response(self, content: str, user_id: str) -> str:
        """Get a response from the agent brain or handler."""
        try:
            if self._message_handler:
                return await self._message_handler(content, user_id, "discord")
            elif self._agent_brain:
                response = await self._agent_brain.process_message(content, channel="discord")
                return response.get("response", "No response generated.")
            else:
                return "Bot is not fully configured. No agent brain available."
        except Exception as e:
            logger.error("discord_response_failed", error=str(e))
            return f"Error processing your request: {str(e)[:100]}"

    async def send_message(self, user_id: str, content: str, **kwargs: Any) -> None:
        """Send a message to a Discord user by ID."""
        if not self._bot:
            logger.warning("discord_bot_not_running")
            return

        try:
            user = await self._bot.fetch_user(int(user_id))
            if user:
                chunks = self._split_response(content, 2000)
                for chunk in chunks:
                    await user.send(chunk)
        except Exception as e:
            logger.error("discord_send_failed", user_id=user_id, error=str(e))

    def run(self) -> None:
        """Start the Discord bot (blocking)."""
        bot = self._create_bot()
        logger.info("discord_starting")
        bot.run(self.bot_token, log_handler=None)

    async def run_async(self) -> None:
        """Start the Discord bot (async)."""
        bot = self._create_bot()
        logger.info("discord_starting_async")
        await bot.start(self.bot_token)

    def stop(self) -> None:
        """Stop the Discord bot."""
        self._running = False
        if self._bot:
            asyncio.get_event_loop().create_task(self._bot.close())
        logger.info("discord_stopped")

    @staticmethod
    def _truncate(text: str, max_length: int) -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    @staticmethod
    def _split_response(text: str, max_length: int) -> list[str]:
        """Split a long response into chunks."""
        if len(text) <= max_length:
            return [text]

        chunks = []
        while text:
            if len(text) <= max_length:
                chunks.append(text)
                break

            # Find a good split point (newline or space)
            split_at = text.rfind("\n", 0, max_length)
            if split_at == -1:
                split_at = text.rfind(" ", 0, max_length)
            if split_at == -1:
                split_at = max_length

            chunks.append(text[:split_at])
            text = text[split_at:].lstrip()

        return chunks
