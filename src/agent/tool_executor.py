"""
Sandboxed tool executor for Gulama.

Orchestrates the secure execution of skills:
1. Receives tool call from the LLM
2. Validates input
3. Checks policy engine for authorization
4. Injects canary tokens in tool output
5. Executes the skill in the sandbox
6. Scans output for sensitive data
7. Logs the action in the audit trail
8. Returns sanitized result to the LLM

This is the critical security checkpoint — ALL tool calls
flow through here, no exceptions.
"""

from __future__ import annotations

from typing import Any

from src.security.audit_logger import AuditLogger
from src.security.canary import CanarySystem
from src.security.egress_filter import EgressFilter
from src.security.input_validator import InputValidator
from src.security.policy_engine import (
    ActionType,
    Decision,
    PolicyContext,
    PolicyEngine,
)
from src.skills.base import SkillResult
from src.skills.registry import SkillRegistry
from src.utils.logging import get_logger

logger = get_logger("tool_executor")


class ToolExecutor:
    """
    Secure tool execution pipeline.

    Every tool call goes through:
    Input Validation -> Policy Check -> Sandbox Execution -> Output Scan -> Audit Log
    """

    def __init__(
        self,
        registry: SkillRegistry,
        policy_engine: PolicyEngine,
        audit_logger: AuditLogger | None = None,
        canary_system: CanarySystem | None = None,
        egress_filter: EgressFilter | None = None,
    ):
        self.registry = registry
        self.policy = policy_engine
        self.audit = audit_logger or AuditLogger()
        self.canary = canary_system or CanarySystem()
        self.egress = egress_filter or EgressFilter()
        self.validator = InputValidator()

    async def execute_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        channel: str = "cli",
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute a tool call through the full security pipeline.

        Returns:
            {
                "success": bool,
                "output": str,
                "error": str,
                "decision": str,  # "allow", "deny", "ask_user"
            }
        """
        logger.info("tool_call", tool=tool_name, args=list(arguments.keys()))

        # Step 1: Find the skill
        skill = self.registry.get(tool_name)
        if skill is None:
            self.audit.log(
                action=f"tool:{tool_name}",
                actor="agent",
                resource=tool_name,
                decision="deny",
                detail="Skill not found",
                channel=channel,
            )
            return {
                "success": False,
                "output": "",
                "error": f"Unknown tool: {tool_name}",
                "decision": "deny",
            }

        # Step 2: Determine required action type
        meta = skill.get_metadata()
        action_type = (
            meta.required_actions[0] if meta.required_actions else ActionType.SKILL_EXECUTE
        )

        # Build resource string from arguments
        resource = self._build_resource_string(tool_name, arguments)

        # Step 3: Policy check
        ctx = PolicyContext(
            action=action_type,
            resource=resource,
            channel=channel,
            user_id=user_id,
        )
        policy_result = self.policy.check(ctx)

        # Log the policy decision
        self.audit.log(
            action=f"tool:{tool_name}",
            actor="agent",
            resource=resource[:200],
            decision=policy_result.decision.value,
            policy=policy_result.policy_name,
            detail=policy_result.reason,
            channel=channel,
        )

        if policy_result.decision == Decision.DENY:
            return {
                "success": False,
                "output": "",
                "error": f"Action denied by policy: {policy_result.reason}",
                "decision": "deny",
            }

        if policy_result.decision == Decision.ASK_USER:
            return {
                "success": False,
                "output": "",
                "error": f"User approval required: {policy_result.reason}",
                "decision": "ask_user",
                "action": tool_name,
                "arguments": arguments,
            }

        # Step 4: Execute the skill
        try:
            result: SkillResult = await skill.execute(**arguments)
        except Exception as e:
            logger.error("tool_execution_error", tool=tool_name, error=str(e))
            self.audit.log(
                action=f"tool:{tool_name}:error",
                actor="system",
                resource=resource[:200],
                decision="error",
                detail=str(e),
                channel=channel,
            )
            return {
                "success": False,
                "output": "",
                "error": f"Execution error: {str(e)}",
                "decision": "allow",
            }

        # Step 5: Scan output for sensitive data
        output = result.output
        if output:
            egress_check = self.egress.check_data(output)
            if not egress_check.allowed:
                logger.warning(
                    "tool_output_redacted",
                    tool=tool_name,
                    patterns=egress_check.blocked_patterns,
                )
                output = "[Output contained sensitive data and was redacted]"

        # Step 6: Inject canary token in output
        if output:
            output, canary = self.canary.inject_tool_canary(output)

        # Step 7: Log successful execution
        self.audit.log(
            action=f"tool:{tool_name}:complete",
            actor="agent",
            resource=resource[:200],
            decision="allow",
            detail=f"success={result.success}",
            channel=channel,
        )

        return {
            "success": result.success,
            "output": output,
            "error": result.error,
            "decision": "allow",
            "metadata": result.metadata,
        }

    @staticmethod
    def _build_resource_string(tool_name: str, arguments: dict[str, Any]) -> str:
        """Build a resource string for policy evaluation."""
        parts = [tool_name]
        if "path" in arguments:
            parts.append(str(arguments["path"]))
        elif "command" in arguments:
            parts.append(str(arguments["command"])[:100])
        elif "url" in arguments:
            parts.append(str(arguments["url"]))
        elif "query" in arguments:
            parts.append(str(arguments["query"])[:100])
        return ":".join(parts)
