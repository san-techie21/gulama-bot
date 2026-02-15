"""
SBOM scanner for Gulama skills.

Generates and scans Software Bill of Materials (SBOM) for skills
to detect known vulnerabilities in dependencies.

Uses:
- Syft for SBOM generation
- Grype for vulnerability scanning
- Custom checks for known-bad patterns
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.utils.logging import get_logger

logger = get_logger("scanner")


@dataclass
class Vulnerability:
    """A detected vulnerability."""
    id: str
    severity: str  # critical, high, medium, low, negligible
    package: str
    version: str
    fixed_in: str = ""
    description: str = ""


@dataclass
class ScanResult:
    """Result of a security scan."""
    skill_name: str
    scan_type: str  # "sbom", "grype", "static", "full"
    passed: bool
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SkillScanner:
    """
    Security scanner for Gulama skills.

    Performs:
    1. SBOM generation (if Syft is available)
    2. Vulnerability scanning (if Grype is available)
    3. Dependency analysis
    4. Permission validation
    """

    def __init__(self, max_critical: int = 0, max_high: int = 0):
        self.max_critical = max_critical
        self.max_high = max_high
        self._syft_available = self._check_tool("syft")
        self._grype_available = self._check_tool("grype")

    @staticmethod
    def _check_tool(name: str) -> bool:
        """Check if a CLI tool is available."""
        try:
            subprocess.run(
                [name, "version"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    async def scan_skill(self, skill_path: Path) -> ScanResult:
        """Run a full security scan on a skill."""
        skill_name = skill_path.name
        result = ScanResult(
            skill_name=skill_name,
            scan_type="full",
            passed=True,
        )

        # 1. Check manifest
        manifest_result = self._check_manifest(skill_path)
        result.warnings.extend(manifest_result)

        # 2. Dependency analysis
        dep_vulns = await self._scan_dependencies(skill_path)
        result.vulnerabilities.extend(dep_vulns)

        # 3. SBOM + Grype scan
        if self._syft_available and self._grype_available:
            grype_vulns = await self._grype_scan(skill_path)
            result.vulnerabilities.extend(grype_vulns)

        # 4. Static pattern analysis
        static_warnings = self._static_scan(skill_path)
        result.warnings.extend(static_warnings)

        # Determine pass/fail
        critical_count = sum(1 for v in result.vulnerabilities if v.severity == "critical")
        high_count = sum(1 for v in result.vulnerabilities if v.severity == "high")

        if critical_count > self.max_critical or high_count > self.max_high:
            result.passed = False

        result.metadata = {
            "total_vulnerabilities": len(result.vulnerabilities),
            "critical": critical_count,
            "high": high_count,
            "syft_available": self._syft_available,
            "grype_available": self._grype_available,
        }

        logger.info(
            "scan_complete",
            skill=skill_name,
            passed=result.passed,
            vulnerabilities=len(result.vulnerabilities),
            warnings=len(result.warnings),
        )

        return result

    def _check_manifest(self, skill_path: Path) -> list[str]:
        """Validate skill manifest."""
        warnings = []
        manifest_path = skill_path / "skill.toml"

        if not manifest_path.exists():
            warnings.append("Missing skill.toml manifest")
            return warnings

        try:
            import tomli
            with open(manifest_path, "rb") as f:
                data = tomli.load(f)

            skill = data.get("skill", {})
            permissions = data.get("permissions", {})

            # Check required fields
            for field_name in ["name", "version", "description", "author"]:
                if field_name not in skill:
                    warnings.append(f"Missing required field: skill.{field_name}")

            # Check dangerous permissions
            if permissions.get("shell", False):
                warnings.append("Skill requests shell execution permission")
            if permissions.get("network") == ["*"]:
                warnings.append("Skill requests unrestricted network access")
            if permissions.get("filesystem") == ["*"]:
                warnings.append("Skill requests unrestricted filesystem access")

            # Check for signature
            if "signature" not in data:
                warnings.append("Missing signature section in manifest")

        except Exception as e:
            warnings.append(f"Failed to parse manifest: {e}")

        return warnings

    async def _scan_dependencies(self, skill_path: Path) -> list[Vulnerability]:
        """Scan Python dependencies for known vulnerabilities."""
        vulnerabilities = []

        # Check requirements.txt or skill.toml dependencies
        deps = self._extract_dependencies(skill_path)

        # Known vulnerable packages (basic check)
        known_vulns: dict[str, dict[str, str]] = {
            "pyyaml<6.0": {
                "id": "CVE-2020-14343",
                "severity": "critical",
                "description": "Arbitrary code execution via yaml.load",
            },
            "requests<2.25.0": {
                "id": "CVE-2023-32681",
                "severity": "medium",
                "description": "Information disclosure via proxy auth leak",
            },
            "urllib3<1.26.18": {
                "id": "CVE-2023-45803",
                "severity": "medium",
                "description": "Request body leak on redirect",
            },
        }

        for dep in deps:
            for pattern, vuln_info in known_vulns.items():
                if dep.lower().startswith(pattern.split("<")[0]):
                    vulnerabilities.append(Vulnerability(
                        id=vuln_info["id"],
                        severity=vuln_info["severity"],
                        package=dep,
                        version="",
                        description=vuln_info["description"],
                    ))

        return vulnerabilities

    async def _grype_scan(self, skill_path: Path) -> list[Vulnerability]:
        """Run Grype vulnerability scanner."""
        vulnerabilities = []

        try:
            # Generate SBOM with Syft
            syft_result = subprocess.run(
                ["syft", str(skill_path), "-o", "json"],
                capture_output=True,
                timeout=60,
                check=False,
            )

            if syft_result.returncode != 0:
                logger.warning("syft_failed", stderr=syft_result.stderr.decode()[:200])
                return []

            # Scan with Grype
            grype_result = subprocess.run(
                ["grype", "--input", "-", "-o", "json"],
                input=syft_result.stdout,
                capture_output=True,
                timeout=60,
                check=False,
            )

            if grype_result.returncode != 0:
                logger.warning("grype_failed", stderr=grype_result.stderr.decode()[:200])
                return []

            # Parse results
            data = json.loads(grype_result.stdout)
            for match in data.get("matches", []):
                vuln = match.get("vulnerability", {})
                artifact = match.get("artifact", {})
                vulnerabilities.append(Vulnerability(
                    id=vuln.get("id", "unknown"),
                    severity=vuln.get("severity", "unknown").lower(),
                    package=artifact.get("name", "unknown"),
                    version=artifact.get("version", ""),
                    fixed_in=vuln.get("fix", {}).get("versions", [""])[0] if vuln.get("fix") else "",
                    description=vuln.get("description", "")[:200],
                ))

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning("grype_scan_error", error=str(e))

        return vulnerabilities

    def _static_scan(self, skill_path: Path) -> list[str]:
        """Static analysis for suspicious code patterns."""
        warnings = []

        for py_file in skill_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                warnings.append(f"{py_file.name}: Non-UTF-8 encoding")
                continue

            dangerous_patterns = [
                ("eval(", "Arbitrary code execution via eval()"),
                ("exec(", "Arbitrary code execution via exec()"),
                ("__import__", "Dynamic import (potential code injection)"),
                ("compile(", "Dynamic code compilation"),
                ("os.system(", "System command execution"),
                ("subprocess.Popen(", "Process execution (should use sandbox)"),
                ("ctypes", "C type access (potential escape)"),
                ("pickle.loads(", "Unsafe deserialization"),
                ("marshal.loads(", "Unsafe deserialization"),
                ("webbrowser.open(", "Browser opening (potential phishing)"),
            ]

            for pattern, description in dangerous_patterns:
                if pattern in content:
                    warnings.append(f"{py_file.name}: {description}")

        return warnings

    @staticmethod
    def _extract_dependencies(skill_path: Path) -> list[str]:
        """Extract dependencies from a skill."""
        deps = []

        # From requirements.txt
        req_file = skill_path / "requirements.txt"
        if req_file.exists():
            for line in req_file.read_text().strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    deps.append(line)

        # From skill.toml
        manifest = skill_path / "skill.toml"
        if manifest.exists():
            try:
                import tomli
                with open(manifest, "rb") as f:
                    data = tomli.load(f)
                python_deps = data.get("dependencies", {}).get("python", [])
                deps.extend(python_deps)
            except Exception:
                pass

        return deps
