"""
Canary token system for Gulama — prompt injection detection.

Embeds invisible canary tokens in prompts and tool outputs.
If a canary is found in unexpected places (like the LLM's response
trying to execute it, or in outgoing network requests), it indicates
a prompt injection attack.

Types of canaries:
1. Token canaries — unique strings embedded in system prompts
2. Task-consistency canaries — verify the agent stays on task
3. Output canaries — detect if LLM output contains injected instructions
"""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.utils.logging import get_logger

logger = get_logger("canary")

# Canary token format: invisible unicode + hash
CANARY_PREFIX = "\u200b\u200c\u200d"  # Zero-width chars (invisible)
CANARY_LENGTH = 16


@dataclass
class CanaryToken:
    """A canary token with metadata."""
    token: str
    purpose: str  # "prompt", "tool_output", "task_consistency"
    created_at: str = ""
    triggered: bool = False

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class CanaryAlert:
    """Alert when a canary is triggered."""
    canary: CanaryToken
    found_in: str  # Where the canary was found
    context: str  # Surrounding text
    severity: str  # "high", "critical"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class CanarySystem:
    """
    Manages canary tokens for prompt injection detection.

    Usage:
        canary = CanarySystem()

        # Embed canary in system prompt
        prompt = canary.inject_prompt_canary(original_prompt)

        # Check LLM response for canary leaks
        alerts = canary.check_response(llm_response)

        # Check outgoing requests
        alerts = canary.check_egress(outgoing_data)
    """

    def __init__(self) -> None:
        self._active_canaries: dict[str, CanaryToken] = {}
        self._alerts: list[CanaryAlert] = []

    def generate_canary(self, purpose: str = "prompt") -> CanaryToken:
        """Generate a new canary token."""
        raw = secrets.token_hex(CANARY_LENGTH)
        # Make it invisible using zero-width characters
        token = f"{CANARY_PREFIX}{raw}{CANARY_PREFIX}"

        canary = CanaryToken(token=token, purpose=purpose)
        self._active_canaries[raw] = canary

        logger.info("canary_generated", purpose=purpose, hash=raw[:8])
        return canary

    def inject_prompt_canary(self, prompt: str) -> str:
        """
        Inject a canary token into a system prompt.

        The canary is invisible to users but if it appears in
        the LLM's output (especially in tool calls), it indicates
        the prompt was leaked or manipulated.
        """
        canary = self.generate_canary(purpose="prompt")
        # Inject at a natural break point
        return f"{prompt}\n{canary.token}\n"

    def inject_tool_canary(self, tool_output: str) -> tuple[str, CanaryToken]:
        """
        Inject a canary into tool output before passing to the LLM.

        If the LLM tries to execute the canary token as a command
        or includes it in a response, it may indicate prompt injection
        via tool output manipulation.
        """
        canary = self.generate_canary(purpose="tool_output")
        injected = f"{tool_output}\n{canary.token}"
        return injected, canary

    def create_task_canary(self, task_description: str) -> CanaryToken:
        """
        Create a task-consistency canary.

        This canary helps detect if the agent deviates from its
        assigned task (e.g., due to prompt injection causing task switching).
        """
        canary = self.generate_canary(purpose="task_consistency")
        canary_hash = hashlib.sha256(
            f"{canary.token}:{task_description}".encode()
        ).hexdigest()[:16]

        # Store the task hash for verification
        self._active_canaries[canary_hash] = canary
        return canary

    def check_response(self, response: str) -> list[CanaryAlert]:
        """
        Check an LLM response for canary token leaks.

        If canary tokens appear in the response, the LLM may have
        been manipulated to leak prompt content.
        """
        alerts = []

        for raw, canary in self._active_canaries.items():
            if raw in response or canary.token in response:
                alert = CanaryAlert(
                    canary=canary,
                    found_in="llm_response",
                    context=response[:200],
                    severity="critical" if canary.purpose == "prompt" else "high",
                )
                alerts.append(alert)
                canary.triggered = True
                logger.warning(
                    "canary_triggered",
                    purpose=canary.purpose,
                    found_in="llm_response",
                    severity=alert.severity,
                )

        self._alerts.extend(alerts)
        return alerts

    def check_egress(self, data: str) -> list[CanaryAlert]:
        """
        Check outgoing data for canary token leaks.

        If canary tokens are found in outgoing network requests,
        it indicates data exfiltration via prompt injection.
        """
        alerts = []

        for raw, canary in self._active_canaries.items():
            if raw in data or canary.token in data:
                alert = CanaryAlert(
                    canary=canary,
                    found_in="egress",
                    context=data[:200],
                    severity="critical",
                )
                alerts.append(alert)
                canary.triggered = True
                logger.warning(
                    "canary_triggered",
                    purpose=canary.purpose,
                    found_in="egress",
                    severity="critical",
                )

        self._alerts.extend(alerts)
        return alerts

    def check_for_injection_patterns(self, text: str) -> list[dict[str, str]]:
        """
        Scan text for common prompt injection patterns.

        Returns a list of detected patterns with descriptions.
        """
        patterns = [
            (r"ignore\s+(previous|above|all)\s+(instructions?|prompts?)", "instruction_override"),
            (r"you\s+are\s+now\s+", "role_hijack"),
            (r"system\s*:\s*", "system_prompt_injection"),
            (r"</?(system|prompt|instructions?)>", "xml_tag_injection"),
            (r"IMPORTANT.*override", "priority_injection"),
            (r"forget\s+(everything|all|previous)", "memory_wipe_attempt"),
            (r"do\s+not\s+follow\s+(the|your)\s+(rules|instructions)", "rule_bypass"),
            (r"reveal\s+(your|the)\s+(system|initial)\s+prompt", "prompt_extraction"),
            (r"\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>", "llm_delimiter_injection"),
            (r"\\n\\nHuman:|\\n\\nAssistant:", "conversation_injection"),
        ]

        detections = []
        for pattern, name in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                detections.append({
                    "pattern": name,
                    "description": f"Detected prompt injection pattern: {name}",
                })

        if detections:
            logger.warning(
                "injection_patterns_detected",
                count=len(detections),
                patterns=[d["pattern"] for d in detections],
            )

        return detections

    def get_alerts(self) -> list[CanaryAlert]:
        """Get all canary alerts."""
        return self._alerts.copy()

    def clear_canaries(self) -> None:
        """Clear all active canaries (e.g., at end of conversation)."""
        count = len(self._active_canaries)
        self._active_canaries.clear()
        logger.info("canaries_cleared", count=count)
