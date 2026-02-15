"""Tests for the security doctor CLI tool."""

from __future__ import annotations

import pytest

from src.cli.doctor import SecurityDoctor, CheckResult


class TestSecurityDoctor:
    """Tests for SecurityDoctor."""

    def test_run_all_checks(self):
        """Running all checks should return results."""
        doctor = SecurityDoctor()
        results = doctor.run_all_checks()
        assert len(results) > 0
        assert all(isinstance(r, CheckResult) for r in results)

    def test_python_version_check(self):
        """Python version check should pass on 3.12+."""
        doctor = SecurityDoctor()
        doctor.run_all_checks()
        py_result = next(r for r in doctor.results if r.name == "Python version")
        assert py_result.status in ("pass", "warn")

    def test_secure_defaults_all_enabled(self):
        """With all security features enabled, secure defaults should pass."""
        doctor = SecurityDoctor(config={
            "sandbox_enabled": True,
            "policy_engine_enabled": True,
            "canary_tokens_enabled": True,
            "egress_filtering_enabled": True,
            "audit_logging_enabled": True,
        })
        doctor.run_all_checks()
        defaults = next(r for r in doctor.results if r.name == "Secure defaults")
        assert defaults.status == "pass"

    def test_secure_defaults_disabled_features(self):
        """With security features disabled, secure defaults should fail."""
        doctor = SecurityDoctor(config={
            "sandbox_enabled": False,
            "policy_engine_enabled": False,
        })
        doctor.run_all_checks()
        defaults = next(r for r in doctor.results if r.name == "Secure defaults")
        assert defaults.status == "fail"

    def test_gateway_loopback(self):
        """Loopback gateway binding should pass."""
        doctor = SecurityDoctor(config={"gateway_host": "127.0.0.1"})
        doctor.run_all_checks()
        binding = next(r for r in doctor.results if r.name == "Gateway binding")
        assert binding.status == "pass"

    def test_gateway_exposed(self):
        """Exposed gateway binding should fail."""
        doctor = SecurityDoctor(config={"gateway_host": "0.0.0.0"})
        doctor.run_all_checks()
        binding = next(r for r in doctor.results if r.name == "Gateway binding")
        assert binding.status == "fail"

    def test_summary(self):
        """Summary should contain required keys."""
        doctor = SecurityDoctor()
        doctor.run_all_checks()
        summary = doctor.get_summary()
        assert "grade" in summary
        assert "total" in summary
        assert "passed" in summary
        assert "score" in summary

    def test_format_report(self):
        """Formatted report should be a string with results."""
        doctor = SecurityDoctor()
        doctor.run_all_checks()
        report = doctor.format_report()
        assert "GULAMA SECURITY DOCTOR" in report
        assert "[PASS]" in report or "[WARN]" in report
        assert "Grade:" in report

    def test_no_debug_mode_default(self):
        """Debug mode should be off by default."""
        doctor = SecurityDoctor()
        doctor.run_all_checks()
        debug = next(r for r in doctor.results if r.name == "Debug mode")
        assert debug.status == "pass"
