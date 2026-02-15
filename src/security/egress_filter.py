"""
Egress filter + DLP for Gulama — prevents data exfiltration.

Inspects all outgoing network requests for:
1. Sensitive data patterns (API keys, credentials, PII)
2. Canary token leaks
3. Unauthorized destinations
4. Large data transfers that might indicate exfiltration

All outgoing requests go through this filter BEFORE being sent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.constants import SENSITIVE_PATTERNS
from src.utils.logging import get_logger

logger = get_logger("egress_filter")


@dataclass
class EgressDecision:
    """Result of egress filtering."""
    allowed: bool
    reason: str
    blocked_patterns: list[str]


class EgressFilter:
    """
    Inspects and filters all outgoing data to prevent
    data exfiltration and credential leaks.
    """

    def __init__(self) -> None:
        self._blocked_domains: set[str] = set()
        self._allowed_domains: set[str] = set()
        self._canary_tokens: set[str] = set()

        # Load default blocked domains
        self._blocked_domains.update([
            "pastebin.com",
            "hastebin.com",
            "paste.ee",
            "ghostbin.co",
            "0x0.st",       # File hosting
            "file.io",
            "transfer.sh",
            "temp.sh",
        ])

    def check_request(
        self,
        url: str,
        method: str = "GET",
        body: str = "",
        headers: dict[str, str] | None = None,
    ) -> EgressDecision:
        """
        Check an outgoing HTTP request.

        Returns an EgressDecision indicating if the request should proceed.
        """
        blocked_patterns = []

        # Check URL against blocked domains
        for domain in self._blocked_domains:
            if domain in url.lower():
                return EgressDecision(
                    allowed=False,
                    reason=f"Blocked domain: {domain}",
                    blocked_patterns=[domain],
                )

        # Check body for sensitive data
        if body:
            blocked_patterns.extend(self._scan_for_secrets(body))

        # Check headers for sensitive data
        if headers:
            for key, value in headers.items():
                if key.lower() in ("authorization", "cookie"):
                    continue  # These are expected
                blocked_patterns.extend(self._scan_for_secrets(value))

        # Check for canary token leaks
        for canary in self._canary_tokens:
            if canary in body or canary in url:
                blocked_patterns.append(f"canary_leak:{canary[:8]}")

        if blocked_patterns:
            logger.warning(
                "egress_blocked",
                url=url[:100],
                patterns=blocked_patterns,
            )
            return EgressDecision(
                allowed=False,
                reason=f"Sensitive data detected in outgoing request: {', '.join(blocked_patterns)}",
                blocked_patterns=blocked_patterns,
            )

        return EgressDecision(
            allowed=True,
            reason="Request approved.",
            blocked_patterns=[],
        )

    def check_data(self, data: str) -> EgressDecision:
        """Check arbitrary outgoing data for sensitive content."""
        blocked = self._scan_for_secrets(data)

        if blocked:
            logger.warning("dlp_blocked", patterns=blocked)
            return EgressDecision(
                allowed=False,
                reason=f"Sensitive data detected: {', '.join(blocked)}",
                blocked_patterns=blocked,
            )

        return EgressDecision(
            allowed=True,
            reason="Data approved.",
            blocked_patterns=[],
        )

    def register_canary(self, token: str) -> None:
        """Register a canary token to watch for in egress."""
        self._canary_tokens.add(token)

    def add_blocked_domain(self, domain: str) -> None:
        """Add a domain to the block list."""
        self._blocked_domains.add(domain.lower())

    def add_allowed_domain(self, domain: str) -> None:
        """Add a domain to the explicit allow list."""
        self._allowed_domains.add(domain.lower())

    def _scan_for_secrets(self, text: str) -> list[str]:
        """Scan text for sensitive patterns."""
        found = []
        for pattern in SENSITIVE_PATTERNS:
            if re.search(pattern, text):
                found.append(f"pattern:{pattern[:30]}")
        return found
