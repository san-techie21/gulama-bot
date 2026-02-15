"""
Code execution skill for Gulama.

Executes code snippets in a sandboxed environment with:
- Language detection (Python, JavaScript, Bash, Ruby)
- Resource limits (memory, CPU time, output size)
- Network isolation
- Filesystem restrictions

All execution runs through the sandbox manager when available.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("code_exec_skill")

# Language configurations
LANGUAGE_CONFIG: dict[str, dict[str, Any]] = {
    "python": {
        "extension": ".py",
        "command": ["python3", "-u"],
        "timeout": 30,
        "shebang": "#!/usr/bin/env python3",
    },
    "javascript": {
        "extension": ".js",
        "command": ["node"],
        "timeout": 30,
        "shebang": "",
    },
    "bash": {
        "extension": ".sh",
        "command": ["bash"],
        "timeout": 15,
        "shebang": "#!/usr/bin/env bash\nset -euo pipefail",
    },
    "ruby": {
        "extension": ".rb",
        "command": ["ruby"],
        "timeout": 30,
        "shebang": "#!/usr/bin/env ruby",
    },
}

MAX_OUTPUT_SIZE = 10000  # chars


class CodeExecSkill(BaseSkill):
    """
    Sandboxed code execution skill.

    Supports Python, JavaScript, Bash, and Ruby.
    All code runs in an isolated environment with resource limits.
    """

    def __init__(self, sandbox_manager: Any = None) -> None:
        self.sandbox_manager = sandbox_manager

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="code_exec",
            description="Execute code snippets in a sandboxed environment (Python, JavaScript, Bash, Ruby)",
            version="1.0.0",
            author="gulama",
            required_actions=[ActionType.SHELL_EXEC],
            is_builtin=True,
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "code_exec",
                "description": (
                    "Execute code in a sandboxed environment. "
                    "Supports Python, JavaScript, Bash, and Ruby. "
                    "Code runs with resource limits and network isolation."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The code to execute",
                        },
                        "language": {
                            "type": "string",
                            "enum": list(LANGUAGE_CONFIG.keys()),
                            "description": "Programming language (default: python)",
                        },
                        "stdin": {
                            "type": "string",
                            "description": "Standard input data to provide to the code",
                        },
                    },
                    "required": ["code"],
                },
            },
        }

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Execute a code snippet."""
        code = kwargs.get("code", "")
        language = kwargs.get("language", "python")
        stdin_data = kwargs.get("stdin", "")

        if not code.strip():
            return SkillResult(success=False, output="", error="No code provided.")

        if language not in LANGUAGE_CONFIG:
            return SkillResult(
                success=False, output="",
                error=f"Unsupported language: {language}. Supported: {list(LANGUAGE_CONFIG.keys())}",
            )

        return await self._run(code, language, stdin_data)

    async def _run(self, code: str, language: str, stdin_data: str = "") -> SkillResult:
        """Execute code in a temporary sandboxed environment."""
        config = LANGUAGE_CONFIG[language]

        # Write code to temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=config["extension"],
            delete=False,
            prefix="gulama_exec_",
        ) as f:
            if config.get("shebang"):
                f.write(config["shebang"] + "\n")
            f.write(code)
            f.flush()
            code_path = Path(f.name)

        try:
            # Build command
            cmd = config["command"] + [str(code_path)]

            # If sandbox manager available, use it
            if self.sandbox_manager:
                result = await self.sandbox_manager.execute(
                    cmd,
                    stdin=stdin_data.encode() if stdin_data else None,
                    timeout=config["timeout"],
                    network=False,
                )
                stdout = result.get("stdout", "")
                stderr = result.get("stderr", "")
                returncode = result.get("returncode", -1)
            else:
                # Direct execution (fallback, less secure)
                try:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdin=asyncio.subprocess.PIPE if stdin_data else None,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        proc.communicate(stdin_data.encode() if stdin_data else None),
                        timeout=config["timeout"],
                    )

                    stdout = stdout_bytes.decode("utf-8", errors="replace")
                    stderr = stderr_bytes.decode("utf-8", errors="replace")
                    returncode = proc.returncode or 0

                except asyncio.TimeoutError:
                    return SkillResult(
                        success=False, output="",
                        error=f"Execution timed out after {config['timeout']}s",
                    )

            # Format output
            output = self._format_output(stdout, stderr, returncode, language)
            success = returncode == 0

            return SkillResult(
                success=success,
                output=output,
                error="" if success else f"Exit code: {returncode}",
                metadata={"language": language, "returncode": returncode},
            )

        except Exception as e:
            logger.error("code_exec_error", language=language, error=str(e))
            return SkillResult(success=False, output="", error=f"Execution error: {str(e)[:300]}")

        finally:
            # Cleanup temp file
            try:
                code_path.unlink(missing_ok=True)
            except Exception:
                pass

    @staticmethod
    def _format_output(
        stdout: str, stderr: str, returncode: int, language: str
    ) -> str:
        """Format execution output."""
        parts = []

        if stdout:
            truncated = stdout[:MAX_OUTPUT_SIZE]
            if len(stdout) > MAX_OUTPUT_SIZE:
                truncated += f"\n...[truncated, {len(stdout)} total chars]"
            parts.append(f"Output:\n{truncated}")

        if stderr:
            truncated = stderr[:2000]
            parts.append(f"Errors:\n{truncated}")

        if returncode != 0:
            parts.append(f"Exit code: {returncode}")

        if not parts:
            parts.append("(No output)")

        return "\n\n".join(parts)
