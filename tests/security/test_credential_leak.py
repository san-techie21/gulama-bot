"""
Tests for credential leak prevention.

Verifies that the egress filter and DLP engine correctly
detect and block credential exfiltration attempts.
"""

from __future__ import annotations

import pytest

from src.security.egress_filter import EgressFilter


class TestCredentialLeakPrevention:
    """Verify credentials cannot be exfiltrated."""

    def setup_method(self):
        self.filter = EgressFilter()

    def test_api_key_in_body_blocked(self):
        """API keys in request body should be blocked."""
        result = self.filter.check_request(
            url="https://evil.com/steal",
            method="POST",
            body="key=sk-ant-api03-abcdefghijklmnopqrstuvwxyz123456",
        )
        assert not result.allowed

    def test_aws_credentials_blocked(self):
        """AWS access keys in body should be blocked."""
        result = self.filter.check_data(
            "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        )
        assert not result.allowed

    def test_github_token_blocked(self):
        """GitHub tokens should be blocked."""
        result = self.filter.check_request(
            url="https://attacker.com/log",
            method="POST",
            body="token=ghp_ABC123DEF456GHI789JKL012MNO345PQR678",
        )
        assert not result.allowed

    def test_clean_url_allowed(self):
        """Clean URLs should pass."""
        result = self.filter.check_request(
            url="https://api.example.com/data",
            method="GET",
        )
        assert result.allowed

    def test_safe_text_passes(self):
        """Normal text without credentials should pass."""
        result = self.filter.check_data(
            "The weather today is sunny with a high of 75F"
        )
        assert result.allowed

    def test_ssh_private_key_blocked(self):
        """SSH private keys should be detected."""
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn\n-----END RSA PRIVATE KEY-----"
        result = self.filter.check_data(text)
        assert not result.allowed

    def test_blocked_exfil_domains(self):
        """Known paste/file-sharing domains should be blocked."""
        result = self.filter.check_request(url="https://pastebin.com/raw/abc123")
        assert not result.allowed

    def test_canary_token_in_body_blocked(self):
        """Canary tokens in outbound data should be blocked."""
        self.filter.register_canary("canary_secret_abc")
        result = self.filter.check_request(
            url="https://evil.com/exfil",
            body="data contains canary_secret_abc value",
        )
        assert not result.allowed
