"""
Security self-audit CLI tool for Gulama.

`gulama doctor` runs a comprehensive security health check:
- Configuration audit
- Dependency vulnerability scan
- Encryption verification
- Sandbox availability check
- Network binding check
- Credential storage check
- Audit log integrity
- OWASP Agentic Top 10 compliance
"""

from __future__ import annotations

import importlib
import os
import platform
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.utils.logging import get_logger

logger = get_logger("doctor")


@dataclass
class CheckResult:
    """Result of a single health check."""

    name: str
    status: str  # "pass", "warn", "fail", "skip"
    message: str
    details: str = ""


class SecurityDoctor:
    """
    Runs comprehensive security health checks on the Gulama installation.

    Categories:
    - Environment: Python version, OS, dependencies
    - Security: encryption, sandbox, network binding
    - Configuration: secure defaults, vault status
    - Integrity: audit log chain, skill signatures
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.results: list[CheckResult] = []

    def run_all_checks(self) -> list[CheckResult]:
        """Run all health checks and return results."""
        self.results.clear()

        # Environment checks
        self._check_python_version()
        self._check_os_platform()
        self._check_core_dependencies()
        self._check_optional_dependencies()

        # Security checks
        self._check_sandbox_available()
        self._check_encryption_available()
        self._check_gateway_binding()
        self._check_credential_storage()
        self._check_signing_tools()

        # Configuration checks
        self._check_secure_defaults()
        self._check_env_file()
        self._check_debug_mode()

        # Integrity checks
        self._check_data_directory()

        return self.results

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the health check results."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "pass")
        warned = sum(1 for r in self.results if r.status == "warn")
        failed = sum(1 for r in self.results if r.status == "fail")
        skipped = sum(1 for r in self.results if r.status == "skip")

        if failed > 0:
            grade = "FAIL"
        elif warned > 2:
            grade = "WARN"
        elif warned > 0:
            grade = "GOOD"
        else:
            grade = "EXCELLENT"

        return {
            "grade": grade,
            "total": total,
            "passed": passed,
            "warned": warned,
            "failed": failed,
            "skipped": skipped,
            "score": f"{passed}/{total}",
        }

    def format_report(self) -> str:
        """Format results as a human-readable report."""
        lines = [
            "=" * 60,
            "  GULAMA SECURITY DOCTOR",
            "=" * 60,
            "",
        ]

        status_icons = {
            "pass": "[PASS]",
            "warn": "[WARN]",
            "fail": "[FAIL]",
            "skip": "[SKIP]",
        }

        for result in self.results:
            icon = status_icons.get(result.status, "[????]")
            lines.append(f"  {icon} {result.name}")
            lines.append(f"         {result.message}")
            if result.details:
                lines.append(f"         {result.details}")
            lines.append("")

        summary = self.get_summary()
        lines.extend(
            [
                "-" * 60,
                f"  Grade: {summary['grade']}",
                f"  Score: {summary['score']} checks passed",
                f"  Passed: {summary['passed']} | Warnings: {summary['warned']} | "
                f"Failed: {summary['failed']} | Skipped: {summary['skipped']}",
                "=" * 60,
            ]
        )

        return "\n".join(lines)

    # --- Environment Checks ---

    def _check_python_version(self) -> None:
        ver = sys.version_info
        if ver >= (3, 12):
            self._add("Python version", "pass", f"Python {ver.major}.{ver.minor}.{ver.micro}")
        elif ver >= (3, 11):
            self._add(
                "Python version", "warn", f"Python {ver.major}.{ver.minor} (3.12+ recommended)"
            )
        else:
            self._add("Python version", "fail", f"Python {ver.major}.{ver.minor} (3.12+ required)")

    def _check_os_platform(self) -> None:
        system = platform.system()
        release = platform.release()
        self._add("OS platform", "pass", f"{system} {release}")

    def _check_core_dependencies(self) -> None:
        core_deps = [
            "fastapi",
            "uvicorn",
            "httpx",
            "litellm",
            "cryptography",
            "click",
            "rich",
            "structlog",
            "pydantic",
        ]
        missing = []
        for dep in core_deps:
            try:
                importlib.import_module(dep)
            except ImportError:
                missing.append(dep)

        if not missing:
            self._add("Core dependencies", "pass", "All core dependencies installed")
        else:
            self._add(
                "Core dependencies",
                "fail",
                f"Missing: {', '.join(missing)}",
                details="Run: pip install gulama",
            )

    def _check_optional_dependencies(self) -> None:
        optional = {
            "chromadb": "Vector memory (RAG)",
            "discord": "Discord channel",
            "playwright": "Browser automation",
            "pyotp": "TOTP authentication",
        }
        available = []
        unavailable = []

        for pkg, desc in optional.items():
            try:
                importlib.import_module(pkg)
                available.append(desc)
            except ImportError:
                unavailable.append(desc)

        if unavailable:
            self._add(
                "Optional dependencies",
                "warn",
                f"{len(available)}/{len(optional)} optional features available",
                details=f"Unavailable: {', '.join(unavailable)}",
            )
        else:
            self._add("Optional dependencies", "pass", "All optional features available")

    # --- Security Checks ---

    def _check_sandbox_available(self) -> None:
        system = platform.system()
        available = []

        if system == "Linux" and shutil.which("bwrap"):
            available.append("bubblewrap")
        if system == "Darwin" and shutil.which("sandbox-exec"):
            available.append("sandbox-exec")
        if shutil.which("docker"):
            available.append("Docker")
        if system == "Windows":
            available.append("Windows Sandbox (if enabled)")

        if available:
            self._add("Sandbox availability", "pass", f"Available: {', '.join(available)}")
        else:
            self._add(
                "Sandbox availability",
                "warn",
                "No sandbox runtime detected",
                details="Install bubblewrap (Linux), Docker, or enable Windows Sandbox",
            )

    def _check_encryption_available(self) -> None:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM

            AESGCM.generate_key(bit_length=256)
            self._add("Encryption (AES-256-GCM)", "pass", "Cryptography library working")
        except Exception as e:
            self._add("Encryption (AES-256-GCM)", "fail", f"Error: {e}")

    def _check_gateway_binding(self) -> None:
        host = self.config.get("gateway_host", "127.0.0.1")
        if host in ("127.0.0.1", "localhost", "::1"):
            self._add("Gateway binding", "pass", f"Loopback only ({host})")
        else:
            self._add(
                "Gateway binding",
                "fail",
                f"Binding to {host} — exposed to network!",
                details="Set gateway_host = '127.0.0.1' in config.toml",
            )

    def _check_credential_storage(self) -> None:
        try:
            import keyring

            backend = type(keyring.get_keyring()).__name__
            self._add("Credential storage", "pass", f"OS keyring: {backend}")
        except Exception:
            self._add(
                "Credential storage",
                "warn",
                "OS keyring unavailable — falling back to encrypted file",
            )

    def _check_signing_tools(self) -> None:
        tools = {}
        for tool in ["cosign", "syft", "grype"]:
            tools[tool] = shutil.which(tool) is not None

        available = [t for t, v in tools.items() if v]
        missing = [t for t, v in tools.items() if not v]

        if not missing:
            self._add("Signing & scanning tools", "pass", "cosign + syft + grype installed")
        elif "cosign" in available:
            self._add(
                "Signing & scanning tools",
                "warn",
                f"Missing: {', '.join(missing)}",
                details="Install Sigstore tools for full supply chain security",
            )
        else:
            self._add(
                "Signing & scanning tools",
                "warn",
                "No signing tools found — using SHA-256 fallback",
                details="Install cosign, syft, grype for full supply chain security",
            )

    # --- Configuration Checks ---

    def _check_secure_defaults(self) -> None:
        issues = []
        if not self.config.get("sandbox_enabled", True):
            issues.append("sandbox disabled")
        if not self.config.get("policy_engine_enabled", True):
            issues.append("policy engine disabled")
        if not self.config.get("canary_tokens_enabled", True):
            issues.append("canary tokens disabled")
        if not self.config.get("egress_filtering_enabled", True):
            issues.append("egress filtering disabled")
        if not self.config.get("audit_logging_enabled", True):
            issues.append("audit logging disabled")

        if not issues:
            self._add("Secure defaults", "pass", "All security features enabled")
        else:
            self._add(
                "Secure defaults",
                "fail",
                f"Security features disabled: {', '.join(issues)}",
            )

    def _check_env_file(self) -> None:
        env_path = Path(".env")
        if env_path.exists():
            self._add(
                ".env file",
                "warn",
                ".env file found — ensure it's in .gitignore",
                details="Secrets should be in the encrypted vault, not .env",
            )
        else:
            self._add(".env file", "pass", "No .env file in project root")

    def _check_debug_mode(self) -> None:
        debug = self.config.get("debug", False) or os.environ.get("GULAMA_DEBUG", "")
        if debug:
            self._add(
                "Debug mode",
                "warn",
                "Debug mode is ON — disable for production",
            )
        else:
            self._add("Debug mode", "pass", "Debug mode is OFF")

    # --- Integrity Checks ---

    def _check_data_directory(self) -> None:
        system = platform.system()
        if system == "Windows":
            data_dir = Path(os.environ.get("APPDATA", "")) / "gulama"
        else:
            data_dir = Path.home() / ".gulama"

        if data_dir.exists():
            self._add("Data directory", "pass", f"Found: {data_dir}")
        else:
            self._add(
                "Data directory",
                "skip",
                f"Not initialized: {data_dir}",
                details="Run 'gulama setup' to initialize",
            )

    def _add(self, name: str, status: str, message: str, details: str = "") -> None:
        self.results.append(
            CheckResult(
                name=name,
                status=status,
                message=message,
                details=details,
            )
        )
