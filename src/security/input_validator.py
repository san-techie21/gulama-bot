"""
Input validation and threat detection for Gulama.

Validates and sanitizes all user input before processing:
- Size limits
- Encoding validation
- Prompt injection detection
- Malicious content detection
- Path traversal prevention
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from src.utils.logging import get_logger

logger = get_logger("input_validator")

# Limits
MAX_MESSAGE_LENGTH = 50_000  # 50K chars (~12K tokens)
MAX_COMMAND_LENGTH = 10_000
MAX_PATH_LENGTH = 4096
MAX_URL_LENGTH = 2048


@dataclass
class ValidationResult:
    """Result of input validation."""

    valid: bool
    sanitized: str
    warnings: list[str]
    blocked_reason: str = ""


class InputValidator:
    """
    Validates and sanitizes all input to the Gulama agent.

    Catches:
    - Oversized inputs
    - Path traversal attacks
    - Encoding attacks (null bytes, control characters)
    - Prompt injection patterns
    - Malicious URLs
    """

    def validate_message(self, message: str) -> ValidationResult:
        """Validate a user chat message."""
        warnings = []

        # Size check
        if len(message) > MAX_MESSAGE_LENGTH:
            return ValidationResult(
                valid=False,
                sanitized="",
                warnings=[],
                blocked_reason=f"Message too long ({len(message)} chars, max {MAX_MESSAGE_LENGTH})",
            )

        # Remove null bytes and control characters
        sanitized = self._remove_control_chars(message)
        if sanitized != message:
            warnings.append("Control characters removed from input")

        # Check for prompt injection patterns (warn but don't block)
        injection_patterns = self._detect_injection_patterns(sanitized)
        if injection_patterns:
            warnings.extend(f"Potential prompt injection: {p}" for p in injection_patterns)

        return ValidationResult(
            valid=True,
            sanitized=sanitized,
            warnings=warnings,
        )

    def validate_path(self, path: str) -> ValidationResult:
        """Validate a file path — prevent path traversal."""
        warnings = []

        if len(path) > MAX_PATH_LENGTH:
            return ValidationResult(
                valid=False,
                sanitized="",
                warnings=[],
                blocked_reason="Path too long",
            )

        # Remove null bytes
        path = path.replace("\x00", "")

        # Check for path traversal BEFORE normalizing (normpath resolves ".." away)
        if ".." in path:
            return ValidationResult(
                valid=False,
                sanitized="",
                warnings=[],
                blocked_reason="Path traversal detected (..)",
            )

        # Normalize path
        normalized = os.path.normpath(path)

        # Check for sensitive paths
        from src.constants import SENSITIVE_PATHS

        for sensitive in SENSITIVE_PATHS:
            if sensitive in normalized.lower():
                return ValidationResult(
                    valid=False,
                    sanitized="",
                    warnings=[],
                    blocked_reason=f"Access to sensitive path: {sensitive}",
                )

        return ValidationResult(
            valid=True,
            sanitized=normalized,
            warnings=warnings,
        )

    def validate_command(self, command: str) -> ValidationResult:
        """Validate a shell command."""
        warnings = []

        if len(command) > MAX_COMMAND_LENGTH:
            return ValidationResult(
                valid=False,
                sanitized="",
                warnings=[],
                blocked_reason="Command too long",
            )

        # Remove null bytes
        sanitized = command.replace("\x00", "")

        # Check for command injection via special characters
        injection_chars = [";", "&&", "||", "`", "$(", "${"]
        for char in injection_chars:
            if char in sanitized:
                warnings.append(f"Shell metacharacter detected: {char}")

        # Check for pipe to shell (code injection)
        if re.search(r"\|\s*(bash|sh|zsh|powershell|cmd)", sanitized, re.IGNORECASE):
            warnings.append("Pipe to shell detected")

        return ValidationResult(
            valid=True,
            sanitized=sanitized,
            warnings=warnings,
        )

    def validate_url(self, url: str) -> ValidationResult:
        """Validate a URL."""
        warnings = []

        if len(url) > MAX_URL_LENGTH:
            return ValidationResult(
                valid=False,
                sanitized="",
                warnings=[],
                blocked_reason="URL too long",
            )

        # Must be http or https
        if not url.startswith(("http://", "https://")):
            return ValidationResult(
                valid=False,
                sanitized="",
                warnings=[],
                blocked_reason="Only http:// and https:// URLs are allowed",
            )

        # Block internal/metadata URLs
        blocked_hosts = [
            "169.254.169.254",  # AWS metadata
            "metadata.google.internal",
            "100.100.100.200",  # Azure metadata
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "[::1]",
        ]
        for host in blocked_hosts:
            if host in url.lower():
                return ValidationResult(
                    valid=False,
                    sanitized="",
                    warnings=[],
                    blocked_reason=f"Access to {host} is blocked (SSRF prevention)",
                )

        # Check for credentials in URL
        if "@" in url.split("//", 1)[-1].split("/", 1)[0]:
            warnings.append("URL contains embedded credentials")

        return ValidationResult(
            valid=True,
            sanitized=url,
            warnings=warnings,
        )

    @staticmethod
    def _remove_control_chars(text: str) -> str:
        """Remove control characters except newline and tab."""
        return "".join(
            c for c in text if c in ("\n", "\t", "\r") or (ord(c) >= 32 and ord(c) != 127)
        )

    @staticmethod
    def _detect_injection_patterns(text: str) -> list[str]:
        """Detect common prompt injection patterns."""
        patterns = {
            "instruction_override": r"ignore\s+(all\s+)?(previous|above)\s+(instructions?|prompts?|rules?)",
            "instruction_override_alt": r"ignore\s+(previous|above|all)\s+(instructions?|prompts?|rules?)",
            "role_hijack": r"you\s+are\s+now\s+",
            "system_injection": r"system\s*:\s*",
            "xml_injection": r"</?(system|prompt|instructions?|context)>",
            "priority_override": r"(IMPORTANT|CRITICAL|URGENT).*override",
            "memory_wipe": r"forget\s+(everything|all|previous)",
            "rule_bypass": r"do\s+not\s+follow\s+(the|your)\s+(rules|instructions|guidelines)",
            "prompt_extraction": r"reveal\s+(your|the)\s+(system|initial)\s+prompt",
            "delimiter_injection": r"\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>",
            "disregard_override": r"disregard\s+(all|previous|safety|your)\s+",
            "new_instructions": r"(new|###)\s*(instructions?|directive)",
            "llm_delimiter": r"\|system\|>|<\|im_start\|>",
            "role_impersonation": r"^(Assistant|Human|System)\s*:\s+",
            "bracket_system": r"\[(SYSTEM|SYS|ADMIN)\]",
        }

        detected = []
        for name, pattern in patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(name)

        return detected
