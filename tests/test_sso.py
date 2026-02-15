"""Tests for the SSO / API key authentication system."""

from __future__ import annotations

import time

from src.security.sso import APIKeyAuth, SSOConfig, SSOManager


class TestAPIKeyAuth:
    """Tests for API key authentication."""

    def setup_method(self):
        self.auth = APIKeyAuth()

    def test_generate_key(self):
        """Generating an API key should return a gulama_sk_ prefixed key."""
        key = self.auth.generate_key("user1", name="test-key")
        assert key.startswith("gulama_sk_")
        assert len(key) > 20

    def test_validate_key(self):
        """Validating a valid key should return metadata."""
        key = self.auth.generate_key("user1")
        meta = self.auth.validate_key(key)
        assert meta is not None
        assert meta["user_id"] == "user1"
        assert meta["last_used"] is not None

    def test_validate_invalid_key(self):
        """Validating an invalid key should return None."""
        result = self.auth.validate_key("gulama_sk_invalidkey")
        assert result is None

    def test_validate_expired_key(self):
        """Expired keys should not validate."""
        key = self.auth.generate_key("user1", expires_in_days=0)
        # Key expires immediately (0 days)
        time.sleep(0.1)
        result = self.auth.validate_key(key)
        assert result is None

    def test_revoke_key(self):
        """Revoking a key should prevent validation."""
        key = self.auth.generate_key("user1")
        assert self.auth.validate_key(key) is not None
        assert self.auth.revoke_key(key) is True
        assert self.auth.validate_key(key) is None

    def test_revoke_nonexistent_key(self):
        """Revoking a non-existent key should return False."""
        assert self.auth.revoke_key("gulama_sk_nope") is False

    def test_list_keys(self):
        """Listing keys for a user should work."""
        self.auth.generate_key("user1", name="key1")
        self.auth.generate_key("user1", name="key2")
        self.auth.generate_key("user2", name="other")

        keys = self.auth.list_keys("user1")
        assert len(keys) == 2
        names = {k["name"] for k in keys}
        assert names == {"key1", "key2"}

    def test_key_hashing(self):
        """Key hashing should be deterministic."""
        hash1 = APIKeyAuth._hash_key("test_key")
        hash2 = APIKeyAuth._hash_key("test_key")
        assert hash1 == hash2

    def test_different_keys_different_hashes(self):
        """Different keys should produce different hashes."""
        hash1 = APIKeyAuth._hash_key("key_a")
        hash2 = APIKeyAuth._hash_key("key_b")
        assert hash1 != hash2


class TestSSOManager:
    """Tests for SSOManager."""

    def setup_method(self):
        self.sso = SSOManager()

    def test_configure_oidc(self):
        """Configuring an OIDC provider should work."""
        config = SSOConfig(
            provider="oidc",
            client_id="test_client",
            client_secret="test_secret",
            issuer_url="https://accounts.google.com",
        )
        self.sso.configure_oidc("google", config)
        provider = self.sso.get_provider("google")
        assert provider is not None

    def test_configure_saml(self):
        """Configuring a SAML provider should work."""
        config = SSOConfig(
            provider="saml",
            saml_metadata_url="https://idp.example.com/metadata",
            saml_entity_id="gulama-sp",
        )
        self.sso.configure_saml("enterprise", config)
        provider = self.sso.get_provider("enterprise")
        assert provider is not None

    def test_list_providers(self):
        """Listing providers should show all configured ones."""
        config = SSOConfig(provider="oidc", client_id="c", issuer_url="https://example.com")
        self.sso.configure_oidc("okta", config)

        providers = self.sso.list_providers()
        assert len(providers) == 1
        assert providers[0]["name"] == "okta"
        assert "OIDC" in providers[0]["type"]

    def test_api_keys_property(self):
        """API keys property should return the APIKeyAuth instance."""
        api_keys = self.sso.api_keys
        assert isinstance(api_keys, APIKeyAuth)

    def test_get_nonexistent_provider(self):
        """Getting a non-existent provider should return None."""
        assert self.sso.get_provider("nonexistent") is None


class TestSSOConfig:
    """Tests for SSOConfig."""

    def test_defaults(self):
        """SSOConfig should have sensible defaults."""
        config = SSOConfig(provider="oidc")
        assert config.redirect_uri == "http://127.0.0.1:18789/auth/callback"
        assert "openid" in config.scopes
        assert "profile" in config.scopes
        assert "email" in config.scopes
