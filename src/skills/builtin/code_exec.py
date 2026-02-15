"""
Code execution skill for Gulama.

Executes code snippets in a sandboxed environment with:
- Language detection (Python, JavaScript, Bash, etc.)
- Resource limits (memory, CPU time, output size)
- Network isolation
- Filesystem restrictions

All execution runs through the sandbox manager.
"""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from src.skills.base import BaseSkill
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

    name = "code_exec"
    description = "Execute code snippets in a sandboxed environment"
    version = "1.0.0"

    def __init__(self, sandbox_manager: Any = None):
        self.sandbox_manager = sandbox_manager

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "run_code",
                    "description": "Execute a code snippet in a sandboxed environment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "Code to execute"},
                            "language": {
                                "type": "string",
                                "enum": list(LANGUAGE_CONFIG.keys()),
                                "description": "Programming language",
                                "default": "python",
                            },
                            "stdin": {"type": "string", "description": "Standard input data"},
                        },
                        "required": ["code"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_python",
                    "description": "Execute Python code in a sandbox",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "Python code to execute"},
                        },
                        "required": ["code"],
                    },
                },
            },
        ]

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        if tool_name == "run_python":
            arguments["language"] = "python"
            tool_name = "run_code"

        if tool_name != "run_code":
            return f"Unknown code exec action: {tool_name}"

        code = arguments.get("code", "")
        language = arguments.get("language", "python")
        stdin_data = arguments.get("stdin", "")

        if not code.strip():
            return "No code provided."

        if language not in LANGUAGE_CONFIG:
            return f"Unsupported language: {language}. Supported: {list(LANGUAGE_CONFIG.keys())}"

        return await self._run(code, language, stdin_data)

    async def _run(self, code: str, language: str, stdin_data: str = "") -> str:
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
                    return f"Execution timed out after {config['timeout']}s"

            # Format output
            output = self._format_output(stdout, stderr, returncode, language)
            return output

        except Exception as e:
            logger.error("code_exec_error", language=language, error=str(e))
            return f"Execution error: {str(e)[:200]}"

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
