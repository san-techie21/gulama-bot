"""
CLI commands for Gulama — Click-based interface.

Commands:
    gulama start     — Start the Gulama agent
    gulama stop      — Stop a running instance
    gulama status    — Show current status
    gulama setup     — Interactive first-time setup wizard
    gulama chat      — Interactive CLI chat with the agent
    gulama doctor    — Security health check
    gulama config    — Show / edit configuration
    gulama vault     — Manage secrets vault
    gulama version   — Show version info
"""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.constants import (
    DATA_DIR,
    DEFAULT_HOST,
    DEFAULT_PORT,
    PROJECT_DISPLAY_NAME,
    PROJECT_VERSION,
)

console = Console()


@click.group()
@click.version_option(PROJECT_VERSION, prog_name=PROJECT_DISPLAY_NAME)
def cli() -> None:
    """Gulama — Secure, open-source personal AI agent."""
    pass


# ──────────────────────── gulama start ────────────────────────


@cli.command()
@click.option("--host", default=DEFAULT_HOST, help="Host to bind (default: 127.0.0.1)")
@click.option("--port", default=DEFAULT_PORT, type=int, help="Port to listen on")
@click.option(
    "--bind-public",
    is_flag=True,
    default=False,
    help="Allow binding to 0.0.0.0 (DANGEROUS)",
)
@click.option(
    "--i-know-what-im-doing",
    is_flag=True,
    default=False,
    help="Required for dangerous operations",
)
@click.option("--no-browser", is_flag=True, default=False, help="Don't open browser on start")
@click.option(
    "--channel",
    type=click.Choice(["gateway", "telegram", "discord", "slack", "matrix", "cli"]),
    default="gateway",
)
@click.option(
    "--voice-wake", is_flag=True, default=False, help="Enable always-on voice wake word detection"
)
def start(
    host: str,
    port: int,
    bind_public: bool,
    i_know_what_im_doing: bool,
    no_browser: bool,
    channel: str,
    voice_wake: bool = False,
) -> None:
    """Start the Gulama agent."""
    from src.utils.logging import setup_logging

    setup_logging(json_format=False)

    # Safety check: binding to 0.0.0.0
    if host == "0.0.0.0" or bind_public:
        if not (bind_public and i_know_what_im_doing):
            console.print(
                "[bold red]SECURITY ERROR:[/] Binding to 0.0.0.0 exposes Gulama to the network.\n"
                "Use --bind-public --i-know-what-im-doing to override.",
                style="red",
            )
            sys.exit(1)
        host = "0.0.0.0"
        console.print(
            "[bold yellow]WARNING:[/] Binding to 0.0.0.0 — Gulama is accessible from the network.",
            style="yellow",
        )

    # Check if vault is initialized (first-run check)
    from src.constants import VAULT_FILE

    if not VAULT_FILE.exists():
        console.print("[yellow]First run detected. Running setup wizard...[/]\n")
        _run_setup()
        return

    console.print(
        Panel(
            f"[bold green]{PROJECT_DISPLAY_NAME} v{PROJECT_VERSION}[/]\n"
            f"Listening on [cyan]{host}:{port}[/]\n"
            f"Channel: [cyan]{channel}[/]\n"
            f"Data dir: [dim]{DATA_DIR}[/]",
            title="Starting Gulama",
            border_style="green",
        )
    )

    # Optional: voice wake word listener
    if voice_wake:
        _start_voice_wake()

    if channel == "cli":
        _start_cli_chat()
    elif channel == "gateway":
        _start_gateway(host, port, no_browser)
    elif channel == "telegram":
        _start_telegram()
    elif channel == "discord":
        _start_discord()
    elif channel == "slack":
        _start_slack()
    elif channel == "matrix":
        _start_matrix()


def _start_gateway(host: str, port: int, no_browser: bool) -> None:
    """Start the FastAPI gateway server."""
    import uvicorn

    from src.gateway.app import create_app

    app = create_app()

    if not no_browser:
        import webbrowser

        webbrowser.open(f"http://{host}:{port}")

    uvicorn.run(app, host=host, port=port, log_level="info")


def _start_cli_chat() -> None:
    """Start interactive CLI chat mode."""
    from src.channels.cli import CLIChannel

    channel = CLIChannel()
    channel.run()


def _start_telegram() -> None:
    """Start the Telegram bot channel."""
    from src.channels.telegram import TelegramChannel

    channel = TelegramChannel()
    channel.run()


def _start_discord() -> None:
    """Start the Discord bot channel."""
    import os

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not token:
        console.print(
            "[red]DISCORD_BOT_TOKEN not set.[/]\n"
            "Set it in .env or run: gulama vault set DISCORD_BOT_TOKEN"
        )
        return

    allowed_users = os.getenv("DISCORD_ALLOWED_USERS", "")
    allowed_list = (
        [u.strip() for u in allowed_users.split(",") if u.strip()] if allowed_users else None
    )

    from src.agent.brain import AgentBrain
    from src.channels.discord_adapter import DiscordChannel
    from src.gateway.config import load_config

    config = load_config()
    brain = AgentBrain(config=config)

    channel = DiscordChannel(
        bot_token=token,
        allowed_user_ids=allowed_list,
    )
    channel.set_agent(brain)

    console.print("[green]Starting Discord bot...[/]")
    channel.run()


def _start_slack() -> None:
    """Start the Slack bot via gateway with webhook endpoints."""
    console.print(
        "[yellow]Slack uses webhooks — start with 'gulama start' (gateway mode) "
        "and configure Slack to point to your webhook URLs.[/]"
    )


def _start_matrix() -> None:
    """Start the Matrix bot channel."""
    import os

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    homeserver = os.getenv("MATRIX_HOMESERVER", "")
    user_id = os.getenv("MATRIX_USER_ID", "")
    access_token = os.getenv("MATRIX_ACCESS_TOKEN", "")

    if not user_id or not access_token:
        console.print(
            "[red]MATRIX_USER_ID and MATRIX_ACCESS_TOKEN not set.[/]\n"
            "Set them in .env or via 'gulama vault set MATRIX_ACCESS_TOKEN'"
        )
        return

    from src.channels.matrix import MatrixChannel

    channel = MatrixChannel(
        homeserver=homeserver,
        user_id=user_id,
        access_token=access_token,
    )

    console.print("[green]Starting Matrix bot...[/]")
    channel.run()


def _start_voice_wake() -> None:
    """Start always-on voice wake word listener in background."""
    try:
        from src.channels.voice_wake import AlwaysOnVoiceChannel

        voice_channel = AlwaysOnVoiceChannel(wake_word="hey google")
        voice_channel.start()
        console.print("[green]Voice wake word listener started (say 'Hey Gulama').[/]")
    except ImportError:
        console.print("[yellow]Voice wake requires: pip install pvporcupine pyaudio[/]")
    except Exception as e:
        console.print(f"[yellow]Voice wake failed: {e}[/]")


# ──────────────────────── gulama stop ────────────────────────


@cli.command()
def stop() -> None:
    """Stop the running Gulama instance."""
    import signal

    from src.constants import DATA_DIR

    pid_file = DATA_DIR / "gulama.pid"
    if not pid_file.exists():
        console.print("[yellow]No running Gulama instance found.[/]")
        return

    try:
        pid = int(pid_file.read_text().strip())
        import os

        os.kill(pid, signal.SIGTERM)
        pid_file.unlink(missing_ok=True)
        console.print(f"[green]Gulama (PID {pid}) stopped.[/]")
    except (ProcessLookupError, ValueError):
        pid_file.unlink(missing_ok=True)
        console.print("[yellow]Stale PID file removed. No running instance.[/]")


# ──────────────────────── gulama status ────────────────────────


@cli.command()
def status() -> None:
    """Show Gulama status and health information."""
    from src.constants import VAULT_FILE

    table = Table(title=f"{PROJECT_DISPLAY_NAME} Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    # Version
    table.add_row("Version", PROJECT_VERSION)

    # Data directory
    table.add_row("Data Directory", str(DATA_DIR))
    table.add_row("Data Dir Exists", "Yes" if DATA_DIR.exists() else "[red]No[/]")

    # Vault
    table.add_row(
        "Secrets Vault",
        "Initialized" if VAULT_FILE.exists() else "[yellow]Not initialized[/]",
    )

    # PID file
    pid_file = DATA_DIR / "gulama.pid"
    if pid_file.exists():
        pid = pid_file.read_text().strip()
        table.add_row("Running", f"[green]Yes (PID {pid})[/]")
    else:
        table.add_row("Running", "[dim]No[/]")

    # Platform info
    from src.utils.platform import detect_architecture, detect_best_sandbox, detect_os

    table.add_row("OS", detect_os().value)
    table.add_row("Architecture", detect_architecture())
    table.add_row("Sandbox Backend", detect_best_sandbox().value)

    console.print(table)


# ──────────────────────── gulama setup ────────────────────────


@cli.command()
@click.option("--force", is_flag=True, help="Force re-setup (will overwrite existing config)")
def setup(force: bool = False) -> None:
    """Interactive first-time setup wizard."""
    _run_setup(force=force)


def _run_setup(force: bool = False) -> None:
    """Run the setup wizard."""
    from src.cli.setup_wizard import SetupWizard

    wizard = SetupWizard(console=console, force=force)
    wizard.run()


# ──────────────────────── gulama chat ────────────────────────


@cli.command()
def chat() -> None:
    """Interactive CLI chat with Gulama."""
    _start_cli_chat()


# ──────────────────────── gulama doctor ────────────────────────


@cli.command()
@click.option("--json-output", is_flag=True, help="Output as JSON")
def doctor(json_output: bool) -> None:
    """Run comprehensive security health check."""
    from src.cli.doctor import SecurityDoctor

    # Load config if available
    config: dict = {}
    try:
        from src.gateway.config import load_config

        cfg = load_config()
        config = cfg.model_dump()
    except Exception:
        pass

    doc = SecurityDoctor(config=config)
    doc.run_all_checks()

    if json_output:
        import json as json_mod

        output = {
            "summary": doc.get_summary(),
            "results": [
                {"name": r.name, "status": r.status, "message": r.message, "details": r.details}
                for r in doc.results
            ],
        }
        console.print(json_mod.dumps(output, indent=2))
    else:
        # Rich formatted output
        console.print(
            Panel(
                "[bold]Comprehensive Security Health Check[/]",
                title="Gulama Doctor",
                border_style="blue",
            )
        )

        table = Table()
        table.add_column("Check", style="cyan")
        table.add_column("Result")
        table.add_column("Details", style="dim")

        status_styles = {
            "pass": "[green]PASS[/]",
            "warn": "[yellow]WARN[/]",
            "fail": "[red]FAIL[/]",
            "skip": "[dim]SKIP[/]",
        }

        for r in doc.results:
            status_str = status_styles.get(r.status, r.status)
            detail = r.message
            if r.details:
                detail += f" | {r.details}"
            table.add_row(r.name, status_str, detail)

        console.print(table)

        summary = doc.get_summary()
        grade_colors = {"EXCELLENT": "green", "GOOD": "green", "WARN": "yellow", "FAIL": "red"}
        color = grade_colors.get(summary["grade"], "white")
        console.print(
            f"\n  Grade: [{color}]{summary['grade']}[/{color}]"
            f"  |  Score: {summary['score']}"
            f"  |  Passed: {summary['passed']}"
            f"  |  Warnings: {summary['warned']}"
            f"  |  Failed: {summary['failed']}"
        )


# ──────────────────────── gulama vault ────────────────────────


@cli.group()
def vault() -> None:
    """Manage the secrets vault."""
    pass


@vault.command("list")
def vault_list() -> None:
    """List all secret keys (never values)."""
    from src.security.secrets_vault import SecretsVault

    v = SecretsVault()
    if not v.is_initialized:
        console.print("[yellow]Vault not initialized. Run 'gulama setup' first.[/]")
        return

    password = click.prompt("Master password", hide_input=True)
    try:
        v.unlock(password)
        keys = v.list_keys()
        if keys:
            for key in keys:
                console.print(f"  [cyan]{key}[/]")
        else:
            console.print("[dim]Vault is empty.[/]")
        v.lock()
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")


@vault.command("set")
@click.argument("key")
def vault_set(key: str) -> None:
    """Set a secret in the vault."""
    from src.security.secrets_vault import SecretsVault

    v = SecretsVault()
    if not v.is_initialized:
        console.print("[yellow]Vault not initialized. Run 'gulama setup' first.[/]")
        return

    password = click.prompt("Master password", hide_input=True)
    value = click.prompt(f"Value for {key}", hide_input=True)

    try:
        v.unlock(password)
        v.set(key, value)
        console.print(f"[green]Secret '{key}' stored.[/]")
        v.lock()
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")


@vault.command("delete")
@click.argument("key")
def vault_delete(key: str) -> None:
    """Delete a secret from the vault."""
    from src.security.secrets_vault import SecretsVault

    v = SecretsVault()
    if not v.is_initialized:
        console.print("[yellow]Vault not initialized.[/]")
        return

    password = click.prompt("Master password", hide_input=True)
    try:
        v.unlock(password)
        if v.delete(key):
            console.print(f"[green]Secret '{key}' deleted.[/]")
        else:
            console.print(f"[yellow]Secret '{key}' not found.[/]")
        v.lock()
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")


# ──────────────────────── gulama config ────────────────────────


@cli.command("config")
@click.option("--show", is_flag=True, help="Show current configuration")
def config_cmd(show: bool) -> None:
    """Show or edit configuration."""
    if show:
        from src.gateway.config import load_config

        cfg = load_config()
        console.print(Panel(str(cfg.model_dump()), title="Current Configuration"))
    else:
        from src.constants import CONFIG_FILE

        if CONFIG_FILE.exists():
            console.print(f"Config file: [cyan]{CONFIG_FILE}[/]")
        else:
            console.print(
                f"[yellow]No user config file. Using defaults.[/]\n"
                f"Create one at: [cyan]{CONFIG_FILE}[/]"
            )


# ──────────────────────── gulama version ────────────────────────


@cli.command()
def version() -> None:
    """Show detailed version information."""
    from src.utils.platform import detect_architecture, detect_best_sandbox, detect_os

    console.print(f"[bold]{PROJECT_DISPLAY_NAME}[/] v{PROJECT_VERSION}")
    console.print(f"  OS: {detect_os().value}")
    console.print(f"  Arch: {detect_architecture()}")
    console.print(f"  Sandbox: {detect_best_sandbox().value}")
    console.print(f"  Python: {sys.version}")
    console.print(f"  Data: {DATA_DIR}")


# ──────────────────────── Entry point ────────────────────────

if __name__ == "__main__":
    cli()
