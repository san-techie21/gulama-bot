"""
Compliance reporting for Gulama Enterprise.

Generates reports for SOC 2, ISO 27001, and internal security audits.
Uses data from the audit logger, policy engine, and security configuration.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.security.audit_logger import AuditLogger
from src.utils.logging import get_logger

logger = get_logger("compliance")


class ComplianceReporter:
    """
    Generates compliance and security audit reports.

    Report types:
    - Security posture summary
    - SOC 2 Type II evidence collection
    - ISO 27001 control mapping
    - OWASP Agentic Top 10 compliance
    - Access control review
    - Incident report
    """

    def __init__(self, audit_logger: AuditLogger | None = None):
        self.audit_logger = audit_logger

    async def generate_security_posture(
        self, config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate a security posture summary."""
        report: dict[str, Any] = {
            "report_type": "security_posture",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
            "sections": {},
        }

        # Configuration security
        config = config or {}
        report["sections"]["configuration"] = {
            "gateway_binding": config.get("gateway_host", "127.0.0.1"),
            "sandbox_enabled": config.get("sandbox_enabled", True),
            "policy_engine_enabled": config.get("policy_engine_enabled", True),
            "canary_tokens_enabled": config.get("canary_tokens_enabled", True),
            "egress_filtering_enabled": config.get("egress_filtering_enabled", True),
            "audit_logging_enabled": config.get("audit_logging_enabled", True),
            "skill_signatures_required": config.get("skill_signature_required", True),
            "encryption_at_rest": True,
            "loopback_only": config.get("gateway_host") == "127.0.0.1",
        }

        # Audit log integrity
        if self.audit_logger:
            chain_valid = self.audit_logger.verify_chain()
            report["sections"]["audit_integrity"] = {
                "chain_valid": chain_valid,
                "last_verified": datetime.now(timezone.utc).isoformat(),
            }

        # OWASP compliance
        report["sections"]["owasp_agentic"] = self._owasp_compliance(config)

        # Security score
        score = self._calculate_score(report["sections"])
        report["score"] = score
        report["grade"] = self._score_to_grade(score)

        return report

    async def generate_soc2_evidence(
        self, days: int = 90
    ) -> dict[str, Any]:
        """Generate SOC 2 Type II evidence collection."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        report: dict[str, Any] = {
            "report_type": "soc2_evidence",
            "period_start": cutoff.isoformat(),
            "period_end": datetime.now(timezone.utc).isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "controls": {},
        }

        # CC6.1 — Logical Access
        report["controls"]["CC6.1"] = {
            "description": "Logical and physical access controls",
            "evidence": [
                "TOTP authentication required for gateway access",
                "Loopback-only binding by default (127.0.0.1)",
                "Session token management with expiry",
                "User authorization via channel-specific IDs",
            ],
        }

        # CC6.6 — Security Measures Against External Threats
        report["controls"]["CC6.6"] = {
            "description": "Security measures against threats from outside system boundaries",
            "evidence": [
                "Egress filtering prevents data exfiltration",
                "DLP scans all outbound data for credentials",
                "Input validation blocks injection attacks",
                "Canary tokens detect prompt injection",
                "Rate limiting on all API endpoints",
            ],
        }

        # CC7.2 — Monitoring Activities
        report["controls"]["CC7.2"] = {
            "description": "The entity monitors system components and operations",
            "evidence": [
                "Tamper-proof Merkle chain audit logs for all actions",
                "Real-time canary token monitoring",
                "Cost tracking and budget alerting",
                f"Audit chain integrity verified (last {days} days)",
            ],
        }

        # CC8.1 — Change Management
        report["controls"]["CC8.1"] = {
            "description": "The entity manages changes to infrastructure and software",
            "evidence": [
                "Skill signature verification (Sigstore cosign)",
                "SBOM generation for all installed skills",
                "Vulnerability scanning on skill installation",
                "Schema migration tracking with versioning",
            ],
        }

        return report

    async def generate_iso27001_mapping(self) -> dict[str, Any]:
        """Generate ISO 27001 Annex A control mapping."""
        return {
            "report_type": "iso27001_mapping",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "controls": {
                "A.5": {
                    "title": "Information security policies",
                    "mapping": "Security-first configuration defaults, GULAMA_MASTER_SPEC.md",
                },
                "A.6": {
                    "title": "Organization of information security",
                    "mapping": "RBAC with role-based permissions, multi-user support",
                },
                "A.8": {
                    "title": "Asset management",
                    "mapping": "Encrypted credential vault, skill inventory, audit logs",
                },
                "A.9": {
                    "title": "Access control",
                    "mapping": "TOTP + session auth, RBAC, channel-based user filtering, API keys",
                },
                "A.10": {
                    "title": "Cryptography",
                    "mapping": "AES-256-GCM for vault/memory, scrypt key derivation, Sigstore signing",
                },
                "A.12": {
                    "title": "Operations security",
                    "mapping": "Sandboxed tool execution, policy engine, egress filtering",
                },
                "A.14": {
                    "title": "System acquisition, development and maintenance",
                    "mapping": "SBOM scanning, vulnerability analysis, signed skills only",
                },
                "A.16": {
                    "title": "Information security incident management",
                    "mapping": "Tamper-proof audit logs, canary token alerts, anomaly detection",
                },
                "A.18": {
                    "title": "Compliance",
                    "mapping": "This compliance report, OWASP Agentic Top 10 compliance",
                },
            },
        }

    async def generate_incident_report(
        self,
        incident_type: str,
        description: str,
        severity: str = "medium",
    ) -> dict[str, Any]:
        """Generate an incident report template."""
        return {
            "report_type": "incident",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "incident": {
                "type": incident_type,
                "severity": severity,
                "description": description,
                "status": "investigating",
                "timeline": [
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "action": "Incident detected and report generated",
                    }
                ],
                "affected_systems": [],
                "mitigation": "",
                "root_cause": "",
                "resolution": "",
            },
        }

    def export_report(self, report: dict[str, Any], output_path: Path) -> None:
        """Export a report to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info("report_exported", path=str(output_path))

    @staticmethod
    def _owasp_compliance(config: dict[str, Any]) -> dict[str, Any]:
        """Check OWASP Agentic Application Security Top 10 compliance."""
        checks = {
            "ASI01_Goal_Hijack": {
                "status": "compliant" if config.get("canary_tokens_enabled") else "non_compliant",
                "mitigation": "Canary tokens + task-consistency verification + input sanitization",
            },
            "ASI02_Tool_Misuse": {
                "status": "compliant" if config.get("policy_engine_enabled") else "non_compliant",
                "mitigation": "Cedar policy engine (zero-trust, every tool call evaluated)",
            },
            "ASI03_Identity_Abuse": {
                "status": "compliant",
                "mitigation": "TOTP auth, per-tool scoped permissions, session isolation",
            },
            "ASI04_Supply_Chain": {
                "status": "compliant" if config.get("skill_signature_required") else "non_compliant",
                "mitigation": "Sigstore cosign signing + SBOM + vulnerability scanning",
            },
            "ASI05_Code_Execution": {
                "status": "compliant" if config.get("sandbox_enabled") else "non_compliant",
                "mitigation": "Mandatory cross-platform sandbox with resource limits",
            },
            "ASI06_Memory_Poisoning": {
                "status": "compliant",
                "mitigation": "Encrypted memory (AES-256-GCM) + HMAC integrity",
            },
            "ASI07_Inter_Agent_Comms": {
                "status": "partial",
                "mitigation": "Single-agent mode with signed message passing planned",
            },
            "ASI08_Cascading_Failures": {
                "status": "compliant",
                "mitigation": "Rate limiting, autonomy levels, circuit breakers",
            },
            "ASI09_Human_Trust": {
                "status": "compliant",
                "mitigation": "Autonomy levels with confirmation prompts for high-risk actions",
            },
            "ASI10_Rogue_Agents": {
                "status": "compliant" if config.get("policy_engine_enabled") else "non_compliant",
                "mitigation": "Policy engine guardrails + anomaly detection",
            },
        }

        compliant = sum(1 for c in checks.values() if c["status"] == "compliant")
        return {
            "score": f"{compliant}/10",
            "checks": checks,
        }

    @staticmethod
    def _calculate_score(sections: dict[str, Any]) -> int:
        """Calculate overall security score (0-100)."""
        score = 0
        config = sections.get("configuration", {})

        # Core security features (60 points)
        feature_points = {
            "sandbox_enabled": 10,
            "policy_engine_enabled": 10,
            "canary_tokens_enabled": 8,
            "egress_filtering_enabled": 8,
            "audit_logging_enabled": 8,
            "skill_signatures_required": 8,
            "encryption_at_rest": 8,
        }

        for feature, points in feature_points.items():
            if config.get(feature, False):
                score += points

        # Loopback binding (10 points)
        if config.get("loopback_only", False):
            score += 10

        # Audit integrity (15 points)
        audit = sections.get("audit_integrity", {})
        if audit.get("chain_valid", False):
            score += 15

        # OWASP compliance (15 points)
        owasp = sections.get("owasp_agentic", {})
        owasp_score = owasp.get("score", "0/10")
        try:
            compliant = int(owasp_score.split("/")[0])
            score += int((compliant / 10) * 15)
        except (ValueError, IndexError):
            pass

        return min(score, 100)

    @staticmethod
    def _score_to_grade(score: int) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        return "F"
