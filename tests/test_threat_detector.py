"""Tests for the threat detection system."""

from __future__ import annotations

import time

import pytest

from src.security.threat_detector import (
    ThreatCategory,
    ThreatDetector,
    ThreatLevel,
)


class TestThreatDetector:
    """Tests for ThreatDetector."""

    def setup_method(self):
        self.detector = ThreatDetector(
            max_failed_auth=3,
            auth_window_seconds=60,
            max_requests_per_minute=10,
        )

    def test_successful_auth_no_threat(self):
        """Successful auth should not trigger a threat."""
        event = self.detector.check_auth_attempt("192.168.1.1", success=True)
        assert event is None

    def test_brute_force_detection(self):
        """Multiple failed auth attempts should trigger brute force detection."""
        for _ in range(2):
            event = self.detector.check_auth_attempt("192.168.1.1", success=False)
            assert event is None

        # Third failure should trigger
        event = self.detector.check_auth_attempt("192.168.1.1", success=False)
        assert event is not None
        assert event.category == ThreatCategory.BRUTE_FORCE
        assert event.level == ThreatLevel.HIGH

    def test_brute_force_blocks_source(self):
        """After brute force detection, the source should be blocked."""
        for _ in range(3):
            self.detector.check_auth_attempt("10.0.0.1", success=False)

        assert self.detector.is_blocked("10.0.0.1")

    def test_unblock_source(self):
        """Manual unblock should work."""
        for _ in range(3):
            self.detector.check_auth_attempt("10.0.0.2", success=False)

        assert self.detector.is_blocked("10.0.0.2")
        self.detector.unblock("10.0.0.2")
        assert not self.detector.is_blocked("10.0.0.2")

    def test_successful_auth_clears_failures(self):
        """Successful auth should clear failed attempt history."""
        self.detector.check_auth_attempt("192.168.1.2", success=False)
        self.detector.check_auth_attempt("192.168.1.2", success=False)
        self.detector.check_auth_attempt("192.168.1.2", success=True)
        # Should not trigger — failures cleared
        event = self.detector.check_auth_attempt("192.168.1.2", success=False)
        assert event is None

    def test_rate_limit_detection(self):
        """Exceeding rate limit should trigger detection."""
        for i in range(10):
            event = self.detector.check_request_rate("user1")
            assert event is None

        event = self.detector.check_request_rate("user1")
        assert event is not None
        assert event.category == ThreatCategory.RATE_ABUSE

    def test_different_users_independent_rate(self):
        """Rate limits should be per-user."""
        for _ in range(10):
            self.detector.check_request_rate("userA")

        event = self.detector.check_request_rate("userB")
        assert event is None

    def test_privilege_escalation_detection(self):
        """Tool usage with privilege escalation indicators should be detected."""
        event = self.detector.check_tool_usage(
            "user1", "shell_exec", {"command": "sudo rm -rf /"}
        )
        assert event is not None
        assert event.category == ThreatCategory.PRIVILEGE_ESCALATION

    def test_normal_tool_usage(self):
        """Normal tool usage should not trigger threats."""
        event = self.detector.check_tool_usage("user1", "web_search", {"query": "weather"})
        assert event is None

    def test_large_data_access_detection(self):
        """Large data access should trigger exfiltration warning."""
        event = self.detector.check_data_access("user1", "messages", volume=200_000)
        assert event is not None
        assert event.category == ThreatCategory.DATA_EXFILTRATION

    def test_normal_data_access(self):
        """Normal-sized data access should not trigger."""
        event = self.detector.check_data_access("user1", "messages", volume=500)
        assert event is None

    def test_get_recent_threats(self):
        """Should return recent threat events."""
        for _ in range(3):
            self.detector.check_auth_attempt("bad_ip", success=False)

        threats = self.detector.get_recent_threats(limit=10)
        assert len(threats) >= 1
        assert threats[0]["category"] == "brute_force"

    def test_threat_summary(self):
        """Threat summary should report status."""
        summary = self.detector.get_threat_summary()
        assert "total_events_24h" in summary
        assert "status" in summary
        assert summary["status"] == "healthy"

    def test_threat_summary_alert_on_high(self):
        """Summary should show alert when unmitigated high threats exist."""
        # Trigger a privilege escalation (high, not auto-mitigated)
        self.detector.check_tool_usage(
            "attacker", "shell_exec", {"command": "sudo bash"}
        )
        summary = self.detector.get_threat_summary()
        assert summary["status"] == "alert"

    def test_filter_threats_by_level(self):
        """Filtering by minimum level should work."""
        # Generate a medium threat
        for _ in range(11):
            self.detector.check_request_rate("spammer")

        # Generate a high threat
        for _ in range(3):
            self.detector.check_auth_attempt("bruter", success=False)

        high_only = self.detector.get_recent_threats(min_level=ThreatLevel.HIGH)
        for t in high_only:
            assert t["level"] in ("high", "critical")
