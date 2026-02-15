"""Configuration management for Gulama — pydantic-settings + TOML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from src.constants import (
    CONFIG_FILE,
    DATA_DIR,
    DEFAULT_AUTONOMY_LEVEL,
    DEFAULT_DAILY_TOKEN_BUDGET,
    DEFAULT_HOST,
    DEFAULT_PORT,
    MAX_CONTEXT_TOKENS,
)


class GatewayConfig(BaseSettings):
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    websocket_origins: list[str] = ["http://localhost:*", "https://localhost:*"]
    max_connections: int = 10
    request_timeout_seconds: int = 60

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        if v == "0.0.0.0":
            raise ValueError(
                "Binding to 0.0.0.0 is FORBIDDEN by default. "
                "Use --bind-public --i-know-what-im-doing to override."
            )
        return v


class AuthConfig(BaseSettings):
    totp_enabled: bool = True
    session_timeout_seconds: int = 3600


class LLMConfig(BaseSettings):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-5-20250929"
    api_base: str = ""
    api_key_name: str = "LLM_API_KEY"
    max_tokens: int = 4096
    temperature: float = 0.7
    daily_token_budget: int = DEFAULT_DAILY_TOKEN_BUDGET


class LLMFallbackConfig(BaseSettings):
    provider: str = ""
    model: str = ""
    api_base: str = ""
    api_key_name: str = ""


class SecurityConfig(BaseSettings):
    sandbox_enabled: bool = True
    policy_engine_enabled: bool = True
    canary_tokens_enabled: bool = True
    egress_filtering_enabled: bool = True
    audit_logging_enabled: bool = True
    skill_signature_required: bool = True


class MemoryConfig(BaseSettings):
    encryption_algorithm: str = "aes-256-gcm"
    vector_store: str = "chromadb"
    max_context_tokens: int = MAX_CONTEXT_TOKENS
    summarize_after_messages: int = 50


class AutonomyConfig(BaseSettings):
    default_level: int = DEFAULT_AUTONOMY_LEVEL

    @field_validator("default_level")
    @classmethod
    def validate_level(cls, v: int) -> int:
        if not 0 <= v <= 5:
            raise ValueError("Autonomy level must be between 0 and 5")
        if v == 5:
            raise ValueError(
                "Autonomy level 5 (full autonomous) requires explicit opt-in "
                "via --i-know-what-im-doing flag"
            )
        return v


class CostConfig(BaseSettings):
    tracking_enabled: bool = True
    daily_budget_usd: float = 2.50
    alert_threshold_percent: int = 80


class TelegramChannelConfig(BaseSettings):
    enabled: bool = False
    bot_token_name: str = "TELEGRAM_BOT_TOKEN"
    allowed_user_ids: list[int] = []


class LoggingConfig(BaseSettings):
    level: str = "INFO"
    format: str = "json"
    file_enabled: bool = True
    max_file_size_mb: int = 50
    max_files: int = 5
    redact_secrets: bool = True  # CRITICAL: Always True in production


class GulamaConfig(BaseSettings):
    """Root configuration for Gulama. Loads from TOML + env vars."""

    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    llm_fallback: LLMFallbackConfig = Field(default_factory=LLMFallbackConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    autonomy: AutonomyConfig = Field(default_factory=AutonomyConfig)
    cost: CostConfig = Field(default_factory=CostConfig)
    telegram: TelegramChannelConfig = Field(default_factory=TelegramChannelConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    model_config = {"env_prefix": "GULAMA_"}


def load_config(config_path: Path | None = None) -> GulamaConfig:
    """
    Load configuration from TOML file with env var overrides.

    Priority (highest to lowest):
    1. Environment variables (GULAMA_*)
    2. User config file (~/.gulama/config.toml)
    3. Default config (config/default.toml)
    """
    import tomli

    merged: dict[str, Any] = {}

    # Load default config
    default_path = Path(__file__).parent.parent.parent / "config" / "default.toml"
    if default_path.exists():
        with open(default_path, "rb") as f:
            merged = tomli.load(f)

    # Load user config (overrides defaults)
    user_path = config_path or CONFIG_FILE
    if user_path.exists():
        with open(user_path, "rb") as f:
            user_config = tomli.load(f)
            merged = _deep_merge(merged, user_config)

    # Build config from merged dict
    config = GulamaConfig(
        gateway=GatewayConfig(**merged.get("gateway", {})),
        auth=AuthConfig(**merged.get("auth", {})),
        llm=LLMConfig(**merged.get("llm", {})),
        llm_fallback=LLMFallbackConfig(**merged.get("llm", {}).get("fallback", {})),
        security=SecurityConfig(**merged.get("security", {})),
        memory=MemoryConfig(**merged.get("memory", {})),
        autonomy=AutonomyConfig(**merged.get("autonomy", {})),
        cost=CostConfig(**merged.get("cost", {})),
        telegram=TelegramChannelConfig(**merged.get("channels", {}).get("telegram", {})),
        logging=LoggingConfig(**merged.get("logging", {})),
    )

    return config


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dicts. Override values take precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
