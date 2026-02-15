"""
CLI channel — interactive terminal chat with Gulama.

Features:
- Rich terminal UI with markdown rendering
- Streaming responses
- Command shortcuts (/help, /exit, /cost, /clear, /history)
- Conversation persistence
"""

from __future__ import annotations

import asyncio
from typing import Any

from rich.console import Console
from rich.panel import Panel

from src.channels.base import BaseChannel
from src.constants import PROJECT_DISPLAY_NAME, PROJECT_VERSION
from src.utils.logging import get_logger

logger = get_logger("cli_channel")

console = Console()

# CLI-local commands (handled before sending to agent)
CLI_COMMANDS = {
    "/help": "Show available commands",
    "/exit": "Exit the chat",
    "/quit": "Exit the chat",
    "/cost": "Show today's cost usage",
    "/clear": "Clear the screen",
    "/history": "Show recent messages",
    "/status": "Show agent status",
    "/version": "Show version info",
}


class CLIChannel(BaseChannel):
    """Interactive terminal chat channel."""

    def __init__(self) -> None:
        super().__init__(channel_name="cli")
        self.conversation_id: str | None = None

    def run(self) -> None:
        """Start the interactive CLI chat loop."""
        self._running = True

        console.print(
            Panel(
                f"[bold green]{PROJECT_DISPLAY_NAME} v{PROJECT_VERSION}[/]\n"
                "[dim]Type your message and press Enter. Type /help for commands.[/]",
                border_style="green",
            )
        )

        try:
            asyncio.run(self._chat_loop())
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/]")
        finally:
            self._running = False

    async def _chat_loop(self) -> None:
        """Main chat loop."""
        from src.agent.brain import AgentBrain
        from src.gateway.config import load_config

        config = load_config()
        brain = AgentBrain(config=config)

        while self._running:
            try:
                # Get user input
                user_input = console.input("\n[bold cyan]You:[/] ").strip()

                if not user_input:
                    continue

                # Handle CLI commands
                if user_input.startswith("/"):
                    should_continue = await self._handle_command(user_input, config)
                    if not should_continue:
                        break
                    continue

                # Send to agent brain with streaming
                console.print("[bold green]Gulama:[/] ", end="")

                full_response = ""
                async for chunk in brain.stream_message(
                    message=user_input,
                    conversation_id=self.conversation_id,
                    channel="cli",
                ):
                    if chunk["type"] == "chunk":
                        print(chunk["content"], end="", flush=True)
                        full_response += chunk["content"]
                    elif chunk["type"] == "complete":
                        self.conversation_id = chunk.get("conversation_id")
                        tokens = chunk.get("tokens_used", 0)
                        cost = chunk.get("cost_usd", 0.0)
                        if not full_response:
                            # Non-streaming fallback
                            print(chunk["content"], end="")
                        print()  # Newline after response
                        if tokens > 0:
                            console.print(f"[dim]({tokens} tokens, ${cost:.4f})[/]")
                    elif chunk["type"] == "error":
                        console.print(f"\n[red]Error: {chunk['content']}[/]")

            except EOFError:
                break
            except KeyboardInterrupt:
                console.print("\n[dim]Use /exit to quit.[/]")

    async def _handle_command(self, command: str, config: Any) -> bool:
        """Handle a CLI command. Returns False if should exit."""
        cmd = command.lower().split()[0]

        if cmd in ("/exit", "/quit"):
            console.print("[dim]Goodbye![/]")
            return False

        elif cmd == "/help":
            table_str = "\n".join(f"  [cyan]{k}[/]  {v}" for k, v in CLI_COMMANDS.items())
            console.print(f"\n[bold]Available commands:[/]\n{table_str}\n")

        elif cmd == "/cost":
            try:
                from src.memory.store import MemoryStore

                store = MemoryStore()
                store.open()
                cost = store.get_today_cost()
                store.close()
                budget = config.cost.daily_budget_usd
                pct = (cost / budget * 100) if budget > 0 else 0
                console.print(
                    f"  Today's cost: [cyan]${cost:.4f}[/] / "
                    f"${budget:.2f} ([{'green' if pct < 80 else 'red'}]{pct:.1f}%[/])"
                )
            except Exception as e:
                console.print(f"  [red]Error: {e}[/]")

        elif cmd == "/clear":
            console.clear()

        elif cmd == "/history":
            if self.conversation_id:
                try:
                    from src.memory.store import MemoryStore

                    store = MemoryStore()
                    store.open()
                    messages = store.get_messages(self.conversation_id, limit=10)
                    store.close()
                    for msg in messages:
                        role = msg["role"]
                        content = msg["content"][:100]
                        color = "cyan" if role == "user" else "green"
                        console.print(f"  [{color}]{role}:[/] {content}")
                except Exception as e:
                    console.print(f"  [red]Error: {e}[/]")
            else:
                console.print("  [dim]No conversation yet.[/]")

        elif cmd == "/status":
            console.print(f"  Provider: [cyan]{config.llm.provider}[/]")
            console.print(f"  Model: [cyan]{config.llm.model}[/]")
            console.print(f"  Autonomy: [cyan]{config.autonomy.default_level}[/]")
            console.print(f"  Sandbox: [cyan]{config.security.sandbox_enabled}[/]")

        elif cmd == "/version":
            console.print(f"  {PROJECT_DISPLAY_NAME} v{PROJECT_VERSION}")

        else:
            console.print(f"  [yellow]Unknown command: {cmd}. Type /help for commands.[/]")

        return True

    async def send_message(self, user_id: str, content: str, **kwargs: Any) -> None:
        """Send a message (print to console)."""
        console.print(f"[bold green]Gulama:[/] {content}")

    def stop(self) -> None:
        """Stop the CLI channel."""
        self._running = False
