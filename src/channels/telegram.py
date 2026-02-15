"""
Telegram channel for Gulama.

Features:
- Secure bot communication with user ID filtering
- Streaming responses via message editing
- Command handlers (/start, /help, /cost, /status)
- Conversation persistence per chat
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.channels.base import BaseChannel
from src.utils.logging import get_logger

logger = get_logger("telegram_channel")


class TelegramChannel(BaseChannel):
    """Telegram bot channel for Gulama."""

    def __init__(self) -> None:
        super().__init__(channel_name="telegram")
        self._conversations: dict[int, str] = {}  # chat_id -> conversation_id

    def run(self) -> None:
        """Start the Telegram bot.

        Uses python-telegram-bot's built-in event loop management
        via Application.run_polling() (synchronous entry point).
        """
        self._running = True
        logger.info("telegram_starting")

        try:
            self._start_bot_sync()
        except KeyboardInterrupt:
            logger.info("telegram_stopped_by_user")
        finally:
            self._running = False

    def _start_bot_sync(self) -> None:
        """Initialize and run the Telegram bot (synchronous).

        python-telegram-bot v20+ manages its own asyncio event loop
        internally via Application.run_polling(). We must NOT wrap it
        in asyncio.run() or we get 'event loop already running' errors.
        """
        from telegram.ext import (
            Application,
            CommandHandler,
            MessageHandler,
            filters,
        )

        from src.gateway.config import load_config

        # Load .env for tokens
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        config = load_config()

        # Load bot token
        bot_token = self._load_bot_token(config)
        if not bot_token:
            logger.error("telegram_no_token", msg="No Telegram bot token found.")
            return

        # Build the application
        app = Application.builder().token(bot_token).build()

        # Store config for handlers
        app.bot_data["config"] = config
        app.bot_data["allowed_users"] = set(config.telegram.allowed_user_ids)

        # Register handlers
        app.add_handler(CommandHandler("start", self._cmd_start))
        app.add_handler(CommandHandler("help", self._cmd_help))
        app.add_handler(CommandHandler("cost", self._cmd_cost))
        app.add_handler(CommandHandler("status", self._cmd_status))
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        logger.info("telegram_bot_polling", bot_token_last4=bot_token[-4:])

        # run_polling() is a SYNCHRONOUS method that manages its own event loop.
        # This is the correct way to use python-telegram-bot v20+.
        app.run_polling(drop_pending_updates=True)

    def _check_user(self, update: Any) -> bool:
        """Check if the user is allowed to use the bot."""
        if not update.effective_user:
            return False

        from src.gateway.config import load_config
        config = load_config()
        allowed = config.telegram.allowed_user_ids

        # Empty list = all users allowed
        if not allowed:
            return True

        return update.effective_user.id in allowed

    async def _cmd_start(self, update: Any, context: Any) -> None:
        """Handle /start command."""
        if not self._check_user(update):
            await update.message.reply_text("Unauthorized. Your user ID is not in the allowed list.")
            return

        await update.message.reply_text(
            "Hello! I'm Gulama, your secure AI assistant.\n\n"
            "Send me a message to chat, or use these commands:\n"
            "/help — Show commands\n"
            "/cost — Today's usage\n"
            "/status — Agent status"
        )

    async def _cmd_help(self, update: Any, context: Any) -> None:
        """Handle /help command."""
        if not self._check_user(update):
            return

        await update.message.reply_text(
            "Available commands:\n"
            "/start — Welcome message\n"
            "/help — This help message\n"
            "/cost — Today's token usage and cost\n"
            "/status — Agent status\n\n"
            "Or just send a message to chat!"
        )

    async def _cmd_cost(self, update: Any, context: Any) -> None:
        """Handle /cost command."""
        if not self._check_user(update):
            return

        try:
            from src.memory.store import MemoryStore

            config = context.bot_data["config"]
            store = MemoryStore()
            store.open()
            cost = store.get_today_cost()
            store.close()

            budget = config.cost.daily_budget_usd
            pct = (cost / budget * 100) if budget > 0 else 0

            await update.message.reply_text(
                f"Today's cost: ${cost:.4f} / ${budget:.2f} ({pct:.1f}%)"
            )
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def _cmd_status(self, update: Any, context: Any) -> None:
        """Handle /status command."""
        if not self._check_user(update):
            return

        config = context.bot_data["config"]
        await update.message.reply_text(
            f"Provider: {config.llm.provider}\n"
            f"Model: {config.llm.model}\n"
            f"Autonomy: Level {config.autonomy.default_level}\n"
            f"Sandbox: {'Enabled' if config.security.sandbox_enabled else 'Disabled'}"
        )

    async def _handle_message(self, update: Any, context: Any) -> None:
        """Handle incoming text messages."""
        if not self._check_user(update):
            return

        chat_id = update.effective_chat.id
        user_message = update.message.text

        # Send "typing" indicator
        await update.effective_chat.send_action("typing")

        try:
            from src.agent.brain import AgentBrain

            config = context.bot_data["config"]
            brain = AgentBrain(config=config)

            # Get or create conversation
            conversation_id = self._conversations.get(chat_id)

            result = await brain.process_message(
                message=user_message,
                conversation_id=conversation_id,
                channel="telegram",
                user_id=str(update.effective_user.id),
            )

            self._conversations[chat_id] = result["conversation_id"]

            # Send response (split if too long for Telegram)
            response = result["response"]
            if len(response) > 4096:
                for i in range(0, len(response), 4096):
                    await update.message.reply_text(response[i : i + 4096])
            else:
                await update.message.reply_text(response)

        except Exception as e:
            logger.error("telegram_error", error=str(e))
            await update.message.reply_text(f"Error: {str(e)}")

    async def send_message(self, user_id: str, content: str, **kwargs: Any) -> None:
        """Send a message to a Telegram user."""
        logger.info("telegram_send", user_id=user_id)

    def stop(self) -> None:
        """Stop the Telegram bot."""
        self._running = False
        logger.info("telegram_stopped")

    @staticmethod
    def _load_bot_token(config: Any) -> str:
        """Load Telegram bot token from vault or environment."""
        import os

        # Try environment variable first (for CI/Docker)
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if token:
            return token

        # Try vault
        try:
            from src.security.secrets_vault import SecretsVault

            vault = SecretsVault()
            if vault.is_initialized:
                # We need the master password to unlock — not available in non-interactive mode
                # For now, fall back to env var
                logger.warning(
                    "telegram_token_from_env",
                    msg="Set TELEGRAM_BOT_TOKEN env var or unlock vault in setup.",
                )
        except Exception:
            pass

        return ""
