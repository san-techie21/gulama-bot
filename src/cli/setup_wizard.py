"""
Interactive setup wizard for first-time Gulama configuration.

Guides the user through:
1. Creating a master password for the secrets vault
2. Choosing an LLM provider and entering API key
3. Configuring autonomy level
4. Optional: setting up Telegram/Discord channels
5. Running security health check
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.constants import (
    CONFIG_FILE,
    DATA_DIR,
    PROJECT_DISPLAY_NAME,
    PROJECT_VERSION,
    VAULT_FILE,
)

# Supported LLM providers for the wizard
LLM_PROVIDERS = [
    ("anthropic", "Anthropic (Claude)", "claude-sonnet-4-5-20250929"),
    ("openai", "OpenAI (GPT)", "gpt-4o"),
    ("google", "Google (Gemini)", "gemini-2.0-flash"),
    ("deepseek", "DeepSeek", "deepseek-chat"),
    ("qwen", "Alibaba (Qwen)", "qwen-plus"),
    ("groq", "Groq", "llama-3.3-70b-versatile"),
    ("together", "Together AI", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
    ("ollama", "Ollama (local)", "llama3.1"),
    ("openai_compatible", "OpenAI-compatible endpoint", ""),
]

AUTONOMY_LEVELS = [
    (0, "Observer — Ask before every action"),
    (1, "Assistant — Auto-read, ask before writes"),
    (2, "Co-pilot — Auto safe actions, ask before shell/network (Recommended)"),
    (3, "Autopilot-cautious — Auto most things, ask before destructive"),
    (4, "Autopilot — Auto everything except financial/credential"),
]


class SetupWizard:
    """Interactive first-time setup wizard."""

    def __init__(self, console: Console | None = None, force: bool = False):
        self.console = console or Console()
        self.force = force

    def run(self) -> None:
        """Run the full setup wizard."""
        self.console.print(
            Panel(
                f"[bold]{PROJECT_DISPLAY_NAME} v{PROJECT_VERSION} — Setup Wizard[/]\n\n"
                "This wizard will configure Gulama for first use.\n"
                "All credentials are encrypted at rest with AES-256-GCM.\n"
                "[dim]No data ever leaves your machine without your permission.[/]",
                border_style="blue",
            )
        )

        if VAULT_FILE.exists() and not self.force:
            self.console.print("[yellow]Vault already exists. Use --force to re-initialize.[/]")
            return

        # Step 1: Create vault with master password
        master_password = self._step_vault()

        # Step 2: Choose LLM provider
        provider, model, api_key, api_base = self._step_llm()

        # Step 3: Store API key in vault
        self._store_secrets(master_password, provider, api_key)

        # Step 4: Choose autonomy level
        autonomy_level = self._step_autonomy()

        # Step 5: Generate config file
        self._generate_config(provider, model, api_base, autonomy_level)

        # Step 6: Optional channels
        self._step_channels(master_password)

        # Done
        self.console.print(
            Panel(
                "[bold green]Setup complete![/]\n\n"
                f"  Data directory: [cyan]{DATA_DIR}[/]\n"
                f"  Config file:    [cyan]{CONFIG_FILE}[/]\n"
                f"  Vault file:     [cyan]{VAULT_FILE}[/]\n\n"
                "Start Gulama with: [bold]gulama start[/]\n"
                "Or chat directly:  [bold]gulama chat[/]",
                title="Ready",
                border_style="green",
            )
        )

    def _step_vault(self) -> str:
        """Create the encrypted secrets vault."""
        self.console.print("\n[bold blue]Step 1/5:[/] Create Master Password\n")
        self.console.print(
            "This password encrypts all your API keys and secrets.\n"
            "[dim]Choose a strong password — it cannot be recovered if lost.[/]\n"
        )

        while True:
            password = click.prompt("  Master password", hide_input=True)
            if len(password) < 8:
                self.console.print("  [red]Password must be at least 8 characters.[/]")
                continue

            confirm = click.prompt("  Confirm password", hide_input=True)
            if password != confirm:
                self.console.print("  [red]Passwords don't match. Try again.[/]")
                continue
            break

        from src.security.secrets_vault import SecretsVault

        vault = SecretsVault()
        if VAULT_FILE.exists() and self.force:
            VAULT_FILE.unlink()

        vault.initialize(password)
        self.console.print("  [green]Vault created and encrypted.[/]\n")
        vault.lock()
        return password

    def _step_llm(self) -> tuple[str, str, str, str]:
        """Choose LLM provider and enter API key."""
        self.console.print("[bold blue]Step 2/5:[/] Choose LLM Provider\n")
        self.console.print(
            "Gulama works with ANY LLM — 100+ providers supported.\nChoose your primary provider:\n"
        )

        table = Table(show_header=False, box=None, padding=(0, 2))
        for i, (_code, name, default_model) in enumerate(LLM_PROVIDERS, 1):
            table.add_row(f"  [{i}]", f"[cyan]{name}[/]", f"[dim]{default_model}[/]")
        self.console.print(table)

        choice = click.prompt(
            "\n  Provider number",
            type=click.IntRange(1, len(LLM_PROVIDERS)),
            default=1,
        )

        provider_code, provider_name, default_model = LLM_PROVIDERS[choice - 1]

        # Custom model override
        model = default_model
        if click.confirm(f"  Use default model ({default_model})?", default=True):
            pass
        else:
            model = click.prompt("  Model name")

        # API key (not needed for local models)
        api_key = ""
        api_base = ""
        if provider_code == "ollama":
            self.console.print("  [dim]Ollama runs locally — no API key needed.[/]")
            api_base = click.prompt("  Ollama URL", default="http://localhost:11434")
        elif provider_code == "openai_compatible":
            api_base = click.prompt("  API endpoint URL")
            api_key = click.prompt("  API key", hide_input=True, default="")
        else:
            api_key = click.prompt(f"  {provider_name} API key", hide_input=True)

        self.console.print(f"  [green]LLM: {provider_name} / {model}[/]\n")
        return provider_code, model, api_key, api_base

    def _store_secrets(self, master_password: str, provider: str, api_key: str) -> None:
        """Store API keys in the vault."""
        if not api_key:
            return

        from src.security.secrets_vault import SecretsVault

        vault = SecretsVault()
        vault.unlock(master_password)
        vault.set("LLM_API_KEY", api_key)
        vault.lock()
        self.console.print("  [green]API key encrypted and stored in vault.[/]\n")

    def _step_autonomy(self) -> int:
        """Choose autonomy level."""
        self.console.print("[bold blue]Step 3/5:[/] Autonomy Level\n")
        self.console.print("How much freedom should Gulama have?\n")

        for level, desc in AUTONOMY_LEVELS:
            marker = " (default)" if level == 2 else ""
            self.console.print(f"  [{level}] {desc}{marker}")

        level = click.prompt(
            "\n  Autonomy level",
            type=click.IntRange(0, 4),
            default=2,
        )

        self.console.print(f"  [green]Autonomy level set to {level}.[/]\n")
        return level

    def _generate_config(
        self,
        provider: str,
        model: str,
        api_base: str,
        autonomy_level: int,
    ) -> None:
        """Generate user config file."""
        self.console.print("[bold blue]Step 4/5:[/] Generating Configuration\n")

        config_content = f"""# Gulama Bot — User Configuration
# Generated by setup wizard
# Edit this file to customize Gulama's behavior.

[llm]
provider = "{provider}"
model = "{model}"
api_base = "{api_base}"
api_key_name = "LLM_API_KEY"

[autonomy]
default_level = {autonomy_level}

[security]
sandbox_enabled = true
policy_engine_enabled = true
canary_tokens_enabled = true
egress_filtering_enabled = true
audit_logging_enabled = true
skill_signature_required = true

[cost]
tracking_enabled = true
daily_budget_usd = 2.50
alert_threshold_percent = 80
"""

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(config_content, encoding="utf-8")
        self.console.print(f"  [green]Config written to {CONFIG_FILE}[/]\n")

    def _step_channels(self, master_password: str) -> None:
        """Optional: configure messaging channels."""
        self.console.print("[bold blue]Step 5/5:[/] Messaging Channels (Optional)\n")

        if click.confirm("  Set up Telegram bot?", default=False):
            token = click.prompt("  Telegram bot token", hide_input=True)
            from src.security.secrets_vault import SecretsVault

            vault = SecretsVault()
            vault.unlock(master_password)
            vault.set("TELEGRAM_BOT_TOKEN", token)
            vault.lock()
            self.console.print("  [green]Telegram token stored.[/]")

            # Update config
            import tomli
            import tomli_w

            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "rb") as f:
                    cfg = tomli.load(f)
            else:
                cfg = {}

            cfg.setdefault("channels", {}).setdefault("telegram", {})["enabled"] = True

            with open(CONFIG_FILE, "wb") as f:
                tomli_w.dump(cfg, f)
            self.console.print("  [green]Telegram channel enabled in config.[/]\n")
        else:
            self.console.print("  [dim]Skipped. You can set up channels later.[/]\n")
