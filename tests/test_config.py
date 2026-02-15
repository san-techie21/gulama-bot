"""Tests for the configuration system."""

import pytest

from src.gateway.config import (
    AutonomyConfig,
    GatewayConfig,
    GulamaConfig,
    LLMConfig,
    SecurityConfig,
)


class TestGatewayConfig:
    """Test gateway configuration validation."""

    def test_default_host_is_loopback(self):
        cfg = GatewayConfig()
        assert cfg.host == "127.0.0.1"

    def test_binding_0000_raises(self):
        with pytest.raises(ValueError, match="FORBIDDEN"):
            GatewayConfig(host="0.0.0.0")

    def test_custom_port(self):
        cfg = GatewayConfig(port=9999)
        assert cfg.port == 9999


class TestAutonomyConfig:
    """Test autonomy level validation."""

    def test_default_level(self):
        cfg = AutonomyConfig()
        assert cfg.default_level == 2

    def test_valid_levels(self):
        for level in range(5):
            cfg = AutonomyConfig(default_level=level)
            assert cfg.default_level == level

    def test_level_5_raises(self):
        with pytest.raises(ValueError, match="explicit opt-in"):
            AutonomyConfig(default_level=5)

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError):
            AutonomyConfig(default_level=6)

        with pytest.raises(ValueError):
            AutonomyConfig(default_level=-1)


class TestSecurityConfig:
    """Test security configuration defaults."""

    def test_all_security_enabled_by_default(self):
        cfg = SecurityConfig()
        assert cfg.sandbox_enabled is True
        assert cfg.policy_engine_enabled is True
        assert cfg.canary_tokens_enabled is True
        assert cfg.egress_filtering_enabled is True
        assert cfg.audit_logging_enabled is True
        assert cfg.skill_signature_required is True


class TestLLMConfig:
    """Test LLM configuration."""

    def test_default_provider(self):
        cfg = LLMConfig()
        assert cfg.provider == "anthropic"
        assert "claude" in cfg.model.lower() or "sonnet" in cfg.model.lower()

    def test_custom_provider(self):
        cfg = LLMConfig(provider="openai", model="gpt-4o")
        assert cfg.provider == "openai"
        assert cfg.model == "gpt-4o"


class TestGulamaConfig:
    """Test root configuration."""

    def test_default_config(self):
        cfg = GulamaConfig()
        assert cfg.gateway.host == "127.0.0.1"
        assert cfg.security.sandbox_enabled is True
        assert cfg.autonomy.default_level == 2
