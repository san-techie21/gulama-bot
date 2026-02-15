"""Tests for the egress filter / DLP."""

from src.security.egress_filter import EgressFilter


class TestEgressFilter:
    """Test outgoing data filtering."""

    def setup_method(self):
        self.filter = EgressFilter()

    def test_normal_request_allowed(self):
        result = self.filter.check_request(
            url="https://api.example.com/data",
            method="GET",
        )
        assert result.allowed

    def test_blocked_domain(self):
        result = self.filter.check_request(url="https://pastebin.com/raw/abc123")
        assert not result.allowed
        assert "pastebin.com" in result.reason.lower()

    def test_api_key_in_body_blocked(self):
        result = self.filter.check_request(
            url="https://api.example.com/data",
            method="POST",
            body="Here is the API key: sk-ant-api03-secret-key-12345678901234567890",
        )
        assert not result.allowed

    def test_github_token_in_body_blocked(self):
        result = self.filter.check_request(
            url="https://webhook.site/test",
            method="POST",
            body="token=ghp_ABC123DEF456GHI789JKL012MNO345PQR678",
        )
        assert not result.allowed

    def test_canary_token_detected(self):
        self.filter.register_canary("canary_abc123")
        result = self.filter.check_request(
            url="https://evil.com/exfil",
            body="data=canary_abc123",
        )
        assert not result.allowed

    def test_clean_data_passes(self):
        result = self.filter.check_data("Hello, this is normal data.")
        assert result.allowed

    def test_sensitive_data_blocked(self):
        result = self.filter.check_data("The OpenAI key is sk-proj-1234567890abcdefghijklmnop")
        assert not result.allowed

    def test_add_custom_blocked_domain(self):
        self.filter.add_blocked_domain("evil-site.com")
        result = self.filter.check_request(url="https://evil-site.com/steal")
        assert not result.allowed
