"""
Built-in shell execution skill for Gulama.

Executes shell commands inside the security sandbox.
All commands go through:
1. Input validation (command injection prevention)
2. Policy engine (autonomy level check)
3. Sandbox execution (filesystem + network isolation)
4. Output scanning (sensitive data redaction)
"""

from __future__ import annotations

from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult


class ShellExecSkill(BaseSkill):
    """Execute shell commands in a secure sandbox."""

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="shell_exec",
            description="Execute shell commands in a secure sandbox",
            version="0.1.0",
            author="gulama",
            required_actions=[ActionType.SHELL_EXEC],
            is_builtin=True,
        )

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Execute a shell command."""
        command = kwargs.get("command", "")
        cwd = kwargs.get("cwd")
        timeout = kwargs.get("timeout", 30)

        if not command:
            return SkillResult(success=False, output="", error="Command is required")

        # Validate command
        from src.security.input_validator import InputValidator
        validator = InputValidator()
        result = validator.validate_command(command)

        if not result.valid:
            return SkillResult(
                success=False, output="", error=result.blocked_reason,
            )

        # Execute in sandbox
        from src.security.sandbox import Sandbox, SandboxConfig
        sandbox = Sandbox(config=SandboxConfig(timeout=timeout))

        sandbox_result = await sandbox.execute(command=result.sanitized, cwd=cwd)

        output = sandbox_result.stdout
        if sandbox_result.stderr:
            output += f"\n--- stderr ---\n{sandbox_result.stderr}"

        if sandbox_result.timed_out:
            return SkillResult(
                success=False,
                output=output,
                error=f"Command timed out after {timeout}s",
            )

        return SkillResult(
            success=sandbox_result.exit_code == 0,
            output=output,
            error=sandbox_result.error,
            metadata={"exit_code": sandbox_result.exit_code},
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "shell_exec",
                "description": "Execute a shell command in a secure sandbox. Use for system operations, package management, git, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute",
                        },
                        "cwd": {
                            "type": "string",
                            "description": "Working directory (optional)",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 30)",
                            "default": 30,
                        },
                    },
                    "required": ["command"],
                },
            },
        }
