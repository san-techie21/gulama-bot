"""
Policy engine for Gulama — deterministic authorization.

Implements a Cedar-inspired policy language for determining what
the agent is allowed to do. Every action goes through the policy
engine BEFORE execution.

Policy decision flow:
1. Agent wants to perform an action (e.g., read file, run shell command)
2. PolicyEngine.check() evaluates the action against all policies
3. Returns ALLOW, DENY, or ASK_USER
4. Only if ALLOW, the action proceeds (through the sandbox)

Default policy: DENY everything not explicitly allowed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from src.constants import SENSITIVE_PATHS
from src.utils.logging import get_logger

logger = get_logger("policy_engine")


class Decision(str, Enum):
    """Policy decision outcomes."""
    ALLOW = "allow"
    DENY = "deny"
    ASK_USER = "ask_user"


class ActionType(str, Enum):
    """Types of actions the agent can attempt."""
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    FILE_DELETE = "file:delete"
    SHELL_EXEC = "shell:exec"
    NETWORK_REQUEST = "network:request"
    NETWORK_DOWNLOAD = "network:download"
    SKILL_EXECUTE = "skill:execute"
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    CREDENTIAL_ACCESS = "credential:access"
    SYSTEM_INFO = "system:info"
    BROWSER_NAVIGATE = "browser:navigate"
    EMAIL_SEND = "email:send"
    MESSAGE_SEND = "message:send"


@dataclass
class PolicyContext:
    """Context for a policy evaluation request."""
    action: ActionType
    resource: str = ""          # Path, URL, command, etc.
    autonomy_level: int = 2
    channel: str = "cli"
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyResult:
    """Result of a policy evaluation."""
    decision: Decision
    reason: str
    policy_name: str = ""


class PolicyEngine:
    """
    Deterministic policy engine for action authorization.

    All actions must pass through this engine before execution.
    Default: DENY everything not explicitly allowed.

    Policies are evaluated in order:
    1. Hard deny rules (always block)
    2. Autonomy-level rules (based on configured level)
    3. Custom user policies
    4. Default: DENY
    """

    def __init__(self, autonomy_level: int = 2):
        self.autonomy_level = autonomy_level
        self._policies: list[Policy] = []
        self._load_default_policies()

    def check(self, ctx: PolicyContext) -> PolicyResult:
        """
        Evaluate an action against all policies.

        Returns the first matching policy result.
        If no policy matches, returns DENY (default deny).
        """
        # Override context autonomy with engine level
        ctx.autonomy_level = self.autonomy_level

        for policy in self._policies:
            result = policy.evaluate(ctx)
            if result is not None:
                logger.info(
                    "policy_decision",
                    action=ctx.action.value,
                    resource=ctx.resource[:100],
                    decision=result.decision.value,
                    policy=result.policy_name,
                )
                return result

        # Default deny
        result = PolicyResult(
            decision=Decision.DENY,
            reason="No policy matched. Default: deny.",
            policy_name="default_deny",
        )
        logger.info(
            "policy_decision",
            action=ctx.action.value,
            resource=ctx.resource[:100],
            decision="deny",
            policy="default_deny",
        )
        return result

    def add_policy(self, policy: Policy) -> None:
        """Add a custom policy."""
        self._policies.append(policy)

    def _load_default_policies(self) -> None:
        """Load the built-in security policies."""
        self._policies = [
            # === HARD DENY — always block, regardless of autonomy ===
            HardDenyPolicy(),

            # === Autonomy-level policies ===
            AutonomyPolicy(),

            # === Resource-specific policies ===
            FileAccessPolicy(),
            NetworkPolicy(),
            ShellPolicy(),
        ]


class Policy:
    """Base class for policies."""

    name: str = "unnamed"

    def evaluate(self, ctx: PolicyContext) -> PolicyResult | None:
        """Evaluate the policy. Return None if not applicable."""
        return None


class HardDenyPolicy(Policy):
    """
    ALWAYS deny these actions, regardless of autonomy level.

    These represent actions that should NEVER be automated:
    - Accessing SSH keys, GPG keys, cloud credentials
    - Executing rm -rf / or similar destructive commands
    - Accessing password managers or credential stores
    - Modifying system files
    """

    name = "hard_deny"

    # Patterns for commands that should NEVER be executed
    FORBIDDEN_COMMANDS = [
        r"rm\s+-rf\s+/",                    # rm -rf /
        r"rm\s+-rf\s+~",                    # rm -rf ~
        r"mkfs\.",                            # Format filesystem
        r"dd\s+if=.*of=/dev/",              # Direct disk write
        r"chmod\s+-R\s+777\s+/",            # Recursive 777 on root
        r":(){ :\|:& };:",                   # Fork bomb
        r">\s*/dev/sd",                      # Overwrite disk
        r"curl.*\|\s*(bash|sh|sudo)",        # Pipe to shell
        r"wget.*\|\s*(bash|sh|sudo)",        # Pipe to shell
    ]

    def evaluate(self, ctx: PolicyContext) -> PolicyResult | None:
        # Always deny access to sensitive paths
        if ctx.action in (ActionType.FILE_READ, ActionType.FILE_WRITE, ActionType.FILE_DELETE):
            for sensitive in SENSITIVE_PATHS:
                if sensitive in ctx.resource.lower():
                    return PolicyResult(
                        decision=Decision.DENY,
                        reason=f"Access to sensitive path '{sensitive}' is forbidden.",
                        policy_name=self.name,
                    )

        # Always deny dangerous shell commands
        if ctx.action == ActionType.SHELL_EXEC:
            for pattern in self.FORBIDDEN_COMMANDS:
                if re.search(pattern, ctx.resource, re.IGNORECASE):
                    return PolicyResult(
                        decision=Decision.DENY,
                        reason=f"Dangerous command blocked: matches pattern '{pattern}'",
                        policy_name=self.name,
                    )

        # Always deny direct credential access without user consent
        if ctx.action == ActionType.CREDENTIAL_ACCESS:
            return PolicyResult(
                decision=Decision.ASK_USER,
                reason="Credential access always requires user approval.",
                policy_name=self.name,
            )

        return None


class AutonomyPolicy(Policy):
    """
    Enforce autonomy level restrictions.

    Level 0: Ask before every action
    Level 1: Auto-read, ask before writes
    Level 2: Auto safe actions, ask before shell/network
    Level 3: Auto most things, ask before destructive
    Level 4: Auto everything except financial/credential
    """

    name = "autonomy"

    def evaluate(self, ctx: PolicyContext) -> PolicyResult | None:
        level = ctx.autonomy_level

        # Level 0: Ask for everything
        if level == 0:
            return PolicyResult(
                decision=Decision.ASK_USER,
                reason="Autonomy level 0: user approval required for all actions.",
                policy_name=self.name,
            )

        # Level 1: Allow reads, ask for writes
        if level == 1:
            if ctx.action in (ActionType.FILE_READ, ActionType.MEMORY_READ, ActionType.SYSTEM_INFO):
                return PolicyResult(
                    decision=Decision.ALLOW,
                    reason="Autonomy level 1: read actions allowed.",
                    policy_name=self.name,
                )
            return PolicyResult(
                decision=Decision.ASK_USER,
                reason="Autonomy level 1: write/exec actions require approval.",
                policy_name=self.name,
            )

        # Level 2: Allow safe actions, ask for shell/network
        if level == 2:
            safe_actions = {
                ActionType.FILE_READ,
                ActionType.MEMORY_READ,
                ActionType.MEMORY_WRITE,
                ActionType.SYSTEM_INFO,
                ActionType.FILE_WRITE,  # Non-sensitive writes
            }
            if ctx.action in safe_actions:
                return PolicyResult(
                    decision=Decision.ALLOW,
                    reason="Autonomy level 2: safe action allowed.",
                    policy_name=self.name,
                )
            if ctx.action in (ActionType.SHELL_EXEC, ActionType.NETWORK_REQUEST,
                              ActionType.NETWORK_DOWNLOAD, ActionType.EMAIL_SEND):
                return PolicyResult(
                    decision=Decision.ASK_USER,
                    reason="Autonomy level 2: shell/network actions require approval.",
                    policy_name=self.name,
                )

        # Level 3: Auto most, ask before destructive
        if level == 3:
            destructive = {ActionType.FILE_DELETE, ActionType.SHELL_EXEC, ActionType.EMAIL_SEND}
            if ctx.action in destructive:
                return PolicyResult(
                    decision=Decision.ASK_USER,
                    reason="Autonomy level 3: destructive actions require approval.",
                    policy_name=self.name,
                )
            return PolicyResult(
                decision=Decision.ALLOW,
                reason="Autonomy level 3: non-destructive action allowed.",
                policy_name=self.name,
            )

        # Level 4: Auto everything except financial/credential
        if level == 4:
            if ctx.action == ActionType.CREDENTIAL_ACCESS:
                return PolicyResult(
                    decision=Decision.ASK_USER,
                    reason="Autonomy level 4: credential access requires approval.",
                    policy_name=self.name,
                )
            return PolicyResult(
                decision=Decision.ALLOW,
                reason="Autonomy level 4: action allowed.",
                policy_name=self.name,
            )

        return None


class FileAccessPolicy(Policy):
    """File access restrictions beyond the hard deny list."""

    name = "file_access"

    # Directories the agent can freely access
    SAFE_DIRS = [
        "/tmp",
        "/var/tmp",
    ]

    def evaluate(self, ctx: PolicyContext) -> PolicyResult | None:
        if ctx.action not in (ActionType.FILE_READ, ActionType.FILE_WRITE, ActionType.FILE_DELETE):
            return None

        # File deletion always requires confirmation
        if ctx.action == ActionType.FILE_DELETE:
            return PolicyResult(
                decision=Decision.ASK_USER,
                reason="File deletion requires user confirmation.",
                policy_name=self.name,
            )

        # System files are restricted
        resource = ctx.resource.lower()
        system_paths = ["/etc/", "/usr/", "/bin/", "/sbin/", "c:\\windows\\", "c:\\program files"]
        for sys_path in system_paths:
            if resource.startswith(sys_path):
                return PolicyResult(
                    decision=Decision.DENY,
                    reason=f"Access to system path '{sys_path}' is restricted.",
                    policy_name=self.name,
                )

        return None


class NetworkPolicy(Policy):
    """Network access restrictions."""

    name = "network"

    # Domains that are always blocked
    BLOCKED_DOMAINS = [
        "localhost",  # Prevent SSRF to local services
        "127.0.0.1",
        "0.0.0.0",
        "169.254.169.254",  # AWS metadata
        "metadata.google.internal",  # GCP metadata
    ]

    def evaluate(self, ctx: PolicyContext) -> PolicyResult | None:
        if ctx.action not in (ActionType.NETWORK_REQUEST, ActionType.NETWORK_DOWNLOAD):
            return None

        # Block access to cloud metadata endpoints (SSRF prevention)
        resource = ctx.resource.lower()
        for blocked in self.BLOCKED_DOMAINS:
            if blocked in resource:
                return PolicyResult(
                    decision=Decision.DENY,
                    reason=f"Access to '{blocked}' is blocked (SSRF prevention).",
                    policy_name=self.name,
                )

        return None


class ShellPolicy(Policy):
    """Shell command execution restrictions."""

    name = "shell"

    # Commands that should always prompt the user
    PROMPT_COMMANDS = [
        r"sudo\s+",
        r"pip\s+install",
        r"npm\s+install",
        r"apt\s+install",
        r"brew\s+install",
        r"docker\s+",
        r"git\s+push",
        r"git\s+force",
    ]

    def evaluate(self, ctx: PolicyContext) -> PolicyResult | None:
        if ctx.action != ActionType.SHELL_EXEC:
            return None

        # Check for commands that always need user approval
        for pattern in self.PROMPT_COMMANDS:
            if re.search(pattern, ctx.resource, re.IGNORECASE):
                return PolicyResult(
                    decision=Decision.ASK_USER,
                    reason=f"Command matches prompt pattern: '{pattern}'",
                    policy_name=self.name,
                )

        return None
