"""Tests for the compliance reporting system."""

from __future__ import annotations

import pytest

from src.security.compliance import ComplianceReporter


class TestComplianceReporter:
    """Tests for ComplianceReporter."""

    def setup_method(self):
        self.reporter = ComplianceReporter()

    @pytest.mark.asyncio
    async def test_security_posture_default(self):
        """Security posture report with defaults should return a score."""
        report = await self.reporter.generate_security_posture()
        assert report["report_type"] == "security_posture"
        assert "score" in report
        assert "grade" in report
        assert isinstance(report["score"], int)

    @pytest.mark.asyncio
    async def test_security_posture_all_enabled(self):
        """Full security config should give high score."""
        config = {
            "sandbox_enabled": True,
            "policy_engine_enabled": True,
            "canary_tokens_enabled": True,
            "egress_filtering_enabled": True,
            "audit_logging_enabled": True,
            "skill_signature_required": True,
            "gateway_host": "127.0.0.1",
        }
        report = await self.reporter.generate_security_posture(config)
        assert report["score"] >= 60  # At least 60 from core features
        assert report["grade"] in ("A", "B", "C")

    @pytest.mark.asyncio
    async def test_security_posture_all_disabled(self):
        """Disabled security should give low score."""
        config = {
            "sandbox_enabled": False,
            "policy_engine_enabled": False,
            "canary_tokens_enabled": False,
            "egress_filtering_enabled": False,
            "audit_logging_enabled": False,
            "skill_signature_required": False,
            "gateway_host": "0.0.0.0",
        }
        report = await self.reporter.generate_security_posture(config)
        assert report["score"] < 50
        assert report["grade"] in ("D", "F")

    @pytest.mark.asyncio
    async def test_soc2_evidence(self):
        """SOC 2 evidence should contain required controls."""
        report = await self.reporter.generate_soc2_evidence(days=30)
        assert report["report_type"] == "soc2_evidence"
        assert "CC6.1" in report["controls"]
        assert "CC6.6" in report["controls"]
        assert "CC7.2" in report["controls"]
        assert "CC8.1" in report["controls"]

    @pytest.mark.asyncio
    async def test_iso27001_mapping(self):
        """ISO 27001 mapping should cover key Annex A controls."""
        report = await self.reporter.generate_iso27001_mapping()
        assert report["report_type"] == "iso27001_mapping"
        controls = report["controls"]
        assert "A.5" in controls
        assert "A.9" in controls
        assert "A.10" in controls
        assert "A.16" in controls

    @pytest.mark.asyncio
    async def test_incident_report(self):
        """Incident report generation should work."""
        report = await self.reporter.generate_incident_report(
            incident_type="prompt_injection",
            description="Canary token leaked in tool call output",
            severity="high",
        )
        assert report["report_type"] == "incident"
        assert report["incident"]["type"] == "prompt_injection"
        assert report["incident"]["severity"] == "high"
        assert report["incident"]["status"] == "investigating"
        assert len(report["incident"]["timeline"]) == 1

    def test_owasp_compliance_all_enabled(self):
        """OWASP compliance with all features should be high."""
        config = {
            "canary_tokens_enabled": True,
            "policy_engine_enabled": True,
            "skill_signature_required": True,
            "sandbox_enabled": True,
        }
        result = ComplianceReporter._owasp_compliance(config)
        compliant = int(result["score"].split("/")[0])
        assert compliant >= 7

    def test_owasp_compliance_disabled(self):
        """OWASP compliance with features disabled should be lower."""
        config = {
            "canary_tokens_enabled": False,
            "policy_engine_enabled": False,
            "skill_signature_required": False,
            "sandbox_enabled": False,
        }
        result = ComplianceReporter._owasp_compliance(config)
        compliant = int(result["score"].split("/")[0])
        assert compliant < 7

    def test_score_to_grade(self):
        """Score to grade mapping should work."""
        assert ComplianceReporter._score_to_grade(95) == "A"
        assert ComplianceReporter._score_to_grade(85) == "B"
        assert ComplianceReporter._score_to_grade(75) == "C"
        assert ComplianceReporter._score_to_grade(65) == "D"
        assert ComplianceReporter._score_to_grade(50) == "F"

    def test_export_report(self, tmp_path):
        """Exporting a report to JSON should work."""
        report = {"report_type": "test", "data": "hello"}
        output = tmp_path / "report.json"
        self.reporter.export_report(report, output)
        assert output.exists()
        import json
        with open(output) as f:
            loaded = json.load(f)
        assert loaded["report_type"] == "test"
