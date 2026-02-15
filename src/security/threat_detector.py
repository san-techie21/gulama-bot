"""
Threat detection and anomaly detection for Gulama.

Monitors user behavior, tool usage patterns, and system events
to detect potential security threats in real time.

Detection methods:
- Statistical anomaly detection (baseline deviation)
- Rate-based abuse detection
- Pattern matching for known attack signatures
- Behavioral analysis (unusual tool combinations, timing, escalation)
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from src.utils.logging import get_logger

logger = get_logger("threat_detector")


class ThreatLevel(StrEnum):
    """Threat severity levels."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatCategory(StrEnum):
    """Categories of detected threats."""

    BRUTE_FORCE = "brute_force"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    INJECTION_ATTEMPT = "injection_attempt"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    RATE_ABUSE = "rate_abuse"
    TOOL_ABUSE = "tool_abuse"
    CREDENTIAL_STUFFING = "credential_stuffing"
    SESSION_HIJACK = "session_hijack"
    SUPPLY_CHAIN = "supply_chain"


@dataclass
class ThreatEvent:
    """A detected threat event."""

    id: str
    timestamp: float
    category: ThreatCategory
    level: ThreatLevel
    description: str
    source_user: str = ""
    source_ip: str = ""
    source_channel: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    mitigated: bool = False
    mitigation_action: str = ""


@dataclass
class UserBaseline:
    """Behavioral baseline for a user."""

    user_id: str
    avg_requests_per_hour: float = 0.0
    common_tools: set[str] = field(default_factory=set)
    common_hours: set[int] = field(default_factory=set)  # 0-23
    total_requests: int = 0
    last_updated: float = 0.0


class ThreatDetector:
    """
    Real-time threat detection engine.

    Monitors:
    - Authentication attempts (brute force, credential stuffing)
    - Tool usage patterns (abuse, unusual combinations)
    - Data access patterns (exfiltration indicators)
    - Request rates (DoS, rate abuse)
    - Behavioral anomalies (deviation from baseline)
    """

    def __init__(
        self,
        *,
        max_failed_auth: int = 5,
        auth_window_seconds: int = 300,
        max_requests_per_minute: int = 60,
        anomaly_threshold: float = 3.0,
    ):
        self.max_failed_auth = max_failed_auth
        self.auth_window_seconds = auth_window_seconds
        self.max_requests_per_minute = max_requests_per_minute
        self.anomaly_threshold = anomaly_threshold

        # Tracking state
        self._failed_auths: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=100))
        self._request_times: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=1000))
        self._tool_usage: dict[str, deque[tuple[float, str]]] = defaultdict(
            lambda: deque(maxlen=500)
        )
        self._baselines: dict[str, UserBaseline] = {}
        self._threat_events: deque[ThreatEvent] = deque(maxlen=10000)
        self._blocked_sources: dict[str, float] = {}  # source -> block_until
        self._event_counter = 0

        # Known dangerous tool sequences
        self._dangerous_sequences = [
            ["shell_exec", "file_write", "network_request"],  # potential C2
            ["file_read", "network_request"],  # potential exfiltration
            ["shell_exec", "shell_exec", "shell_exec", "shell_exec"],  # shell storm
        ]

    def check_auth_attempt(
        self, source: str, success: bool, user_id: str = ""
    ) -> ThreatEvent | None:
        """Check an authentication attempt for brute force patterns."""
        now = time.time()

        if success:
            # Clear failed attempts on success
            self._failed_auths[source].clear()
            return None

        # Record failed attempt
        self._failed_auths[source].append(now)

        # Count recent failures within window
        cutoff = now - self.auth_window_seconds
        recent = [t for t in self._failed_auths[source] if t > cutoff]

        if len(recent) >= self.max_failed_auth:
            event = self._create_event(
                category=ThreatCategory.BRUTE_FORCE,
                level=ThreatLevel.HIGH,
                description=(
                    f"Brute force detected: {len(recent)} failed auth attempts "
                    f"from {source} in {self.auth_window_seconds}s"
                ),
                source_user=user_id,
                source_ip=source,
                details={"attempts": len(recent), "window_seconds": self.auth_window_seconds},
            )
            # Auto-block source
            self._blocked_sources[source] = now + 900  # 15 min block
            event.mitigated = True
            event.mitigation_action = "source_blocked_15m"
            return event

        return None

    def check_request_rate(self, user_id: str, channel: str = "") -> ThreatEvent | None:
        """Check if a user is exceeding request rate limits."""
        now = time.time()
        self._request_times[user_id].append(now)

        # Count requests in last minute
        cutoff = now - 60
        recent = [t for t in self._request_times[user_id] if t > cutoff]

        if len(recent) > self.max_requests_per_minute:
            return self._create_event(
                category=ThreatCategory.RATE_ABUSE,
                level=ThreatLevel.MEDIUM,
                description=(
                    f"Rate limit exceeded: {len(recent)} requests/min "
                    f"from user {user_id} (limit: {self.max_requests_per_minute})"
                ),
                source_user=user_id,
                source_channel=channel,
                details={"requests_per_minute": len(recent)},
            )

        return None

    def check_tool_usage(
        self, user_id: str, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> ThreatEvent | None:
        """Check tool usage for suspicious patterns."""
        now = time.time()
        self._tool_usage[user_id].append((now, tool_name))

        # Check for dangerous tool sequences
        recent_tools = [name for ts, name in self._tool_usage[user_id] if now - ts < 60]

        for sequence in self._dangerous_sequences:
            if self._contains_subsequence(recent_tools, sequence):
                return self._create_event(
                    category=ThreatCategory.TOOL_ABUSE,
                    level=ThreatLevel.HIGH,
                    description=(
                        f"Suspicious tool sequence detected for user {user_id}: "
                        f"{' -> '.join(sequence)}"
                    ),
                    source_user=user_id,
                    details={"sequence": sequence, "recent_tools": recent_tools[-10:]},
                )

        # Check for privilege escalation patterns
        if arguments:
            escalation_indicators = [
                "sudo",
                "admin",
                "root",
                "chmod 777",
                "setuid",
                "--privileged",
                "GRANT ALL",
            ]
            args_str = str(arguments).lower()
            for indicator in escalation_indicators:
                if indicator.lower() in args_str:
                    return self._create_event(
                        category=ThreatCategory.PRIVILEGE_ESCALATION,
                        level=ThreatLevel.HIGH,
                        description=(
                            f"Privilege escalation attempt: '{indicator}' "
                            f"in {tool_name} by user {user_id}"
                        ),
                        source_user=user_id,
                        details={"tool": tool_name, "indicator": indicator},
                    )

        # Check behavioral anomaly (deviation from baseline)
        baseline = self._baselines.get(user_id)
        if baseline and baseline.total_requests > 50:
            if tool_name not in baseline.common_tools:
                # Using an unusual tool — flag if many unusual tools in a row
                unusual_count = sum(
                    1
                    for _, t in list(self._tool_usage[user_id])[-5:]
                    if t not in baseline.common_tools
                )
                if unusual_count >= 3:
                    return self._create_event(
                        category=ThreatCategory.ANOMALOUS_BEHAVIOR,
                        level=ThreatLevel.MEDIUM,
                        description=(
                            f"Behavioral anomaly: user {user_id} using "
                            f"{unusual_count} unusual tools in sequence"
                        ),
                        source_user=user_id,
                        details={"unusual_count": unusual_count, "tool": tool_name},
                    )

        # Update baseline
        self._update_baseline(user_id, tool_name)

        return None

    def check_data_access(
        self, user_id: str, data_type: str, volume: int = 0
    ) -> ThreatEvent | None:
        """Check for data exfiltration patterns."""
        # Large data access
        if volume > 100_000:  # > 100KB
            return self._create_event(
                category=ThreatCategory.DATA_EXFILTRATION,
                level=ThreatLevel.MEDIUM,
                description=(
                    f"Large data access: user {user_id} accessed {volume} bytes of {data_type}"
                ),
                source_user=user_id,
                details={"data_type": data_type, "volume": volume},
            )

        return None

    def is_blocked(self, source: str) -> bool:
        """Check if a source is currently blocked."""
        block_until = self._blocked_sources.get(source, 0)
        if time.time() < block_until:
            return True
        # Expired block — remove
        self._blocked_sources.pop(source, None)
        return False

    def unblock(self, source: str) -> None:
        """Manually unblock a source."""
        self._blocked_sources.pop(source, None)

    def get_recent_threats(
        self, limit: int = 50, min_level: ThreatLevel | None = None
    ) -> list[dict[str, Any]]:
        """Get recent threat events."""
        level_order = {
            ThreatLevel.INFO: 0,
            ThreatLevel.LOW: 1,
            ThreatLevel.MEDIUM: 2,
            ThreatLevel.HIGH: 3,
            ThreatLevel.CRITICAL: 4,
        }

        events = list(self._threat_events)

        if min_level:
            min_val = level_order.get(min_level, 0)
            events = [e for e in events if level_order.get(e.level, 0) >= min_val]

        events.sort(key=lambda e: e.timestamp, reverse=True)

        return [
            {
                "id": e.id,
                "timestamp": e.timestamp,
                "category": e.category.value,
                "level": e.level.value,
                "description": e.description,
                "source_user": e.source_user,
                "source_ip": e.source_ip,
                "mitigated": e.mitigated,
                "mitigation_action": e.mitigation_action,
            }
            for e in events[:limit]
        ]

    def get_threat_summary(self) -> dict[str, Any]:
        """Get a summary of threat detection status."""
        now = time.time()
        last_24h = [e for e in self._threat_events if now - e.timestamp < 86400]

        by_level: dict[str, int] = defaultdict(int)
        by_category: dict[str, int] = defaultdict(int)
        for e in last_24h:
            by_level[e.level.value] += 1
            by_category[e.category.value] += 1

        return {
            "total_events_24h": len(last_24h),
            "by_level": dict(by_level),
            "by_category": dict(by_category),
            "blocked_sources": len(self._blocked_sources),
            "tracked_users": len(self._baselines),
            "status": "healthy"
            if not any(
                e.level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL) and not e.mitigated
                for e in last_24h
            )
            else "alert",
        }

    def _create_event(self, **kwargs: Any) -> ThreatEvent:
        """Create and record a threat event."""
        self._event_counter += 1
        event = ThreatEvent(
            id=f"threat_{self._event_counter:06d}",
            timestamp=time.time(),
            **kwargs,
        )
        self._threat_events.append(event)
        logger.warning(
            "threat_detected",
            event_id=event.id,
            category=event.category.value,
            level=event.level.value,
            description=event.description,
        )
        return event

    def _update_baseline(self, user_id: str, tool_name: str) -> None:
        """Update behavioral baseline for a user."""
        now = time.time()
        current_hour = int((now % 86400) / 3600)

        if user_id not in self._baselines:
            self._baselines[user_id] = UserBaseline(user_id=user_id)

        baseline = self._baselines[user_id]
        baseline.common_tools.add(tool_name)
        baseline.common_hours.add(current_hour)
        baseline.total_requests += 1
        baseline.last_updated = now

    @staticmethod
    def _contains_subsequence(sequence: list[str], pattern: list[str]) -> bool:
        """Check if a sequence contains a subsequence pattern."""
        if len(pattern) > len(sequence):
            return False
        pi = 0
        for item in sequence:
            if item == pattern[pi]:
                pi += 1
                if pi == len(pattern):
                    return True
        return False
