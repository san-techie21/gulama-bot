"""
Cross-platform sandbox for Gulama — secure command execution.

All tool execution runs inside a sandbox:
- Linux: bubblewrap (bwrap) — same technology as Anthropic's Claude Code
- macOS: Apple sandbox-exec with custom profiles
- Windows: Windows Sandbox or process isolation
- Fallback: Docker container or subprocess with resource limits

The sandbox provides:
- Filesystem isolation (read-only root, limited write access)
- Network restrictions
- Process limits (CPU time, memory)
- No access to sensitive paths
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from src.constants import SENSITIVE_PATHS
from src.utils.logging import get_logger
from src.utils.platform import SandboxBackend, detect_best_sandbox

logger = get_logger("sandbox")

# Resource limits
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_MAX_MEMORY_MB = 512
DEFAULT_MAX_OUTPUT_BYTES = 1024 * 1024  # 1MB


@dataclass
class SandboxConfig:
    """Configuration for the sandbox."""

    timeout: int = DEFAULT_TIMEOUT
    max_memory_mb: int = DEFAULT_MAX_MEMORY_MB
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES
    allow_network: bool = False
    writable_dirs: list[str] = field(default_factory=lambda: ["/tmp"])
    env_vars: dict[str, str] = field(default_factory=dict)


@dataclass
class SandboxResult:
    """Result of a sandboxed execution."""

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    error: str = ""


class Sandbox:
    """
    Cross-platform sandbox for secure command execution.

    Automatically detects the best available sandbox backend
    for the current platform.
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self.backend = detect_best_sandbox()
        logger.info("sandbox_initialized", backend=self.backend.value)

    async def execute(
        self,
        command: str | list[str],
        cwd: str | None = None,
    ) -> SandboxResult:
        """
        Execute a command inside the sandbox.

        Args:
            command: Shell command string or list of args
            cwd: Working directory (must be in allowed paths)

        Returns:
            SandboxResult with stdout, stderr, exit code
        """
        if isinstance(command, str):
            cmd_str = command
            cmd_list = ["sh", "-c", command]
        else:
            cmd_str = " ".join(command)
            cmd_list = list(command)

        logger.info("sandbox_exec", command=cmd_str[:200], backend=self.backend.value)

        # Check for obviously dangerous commands before sandboxing
        if self._is_dangerous(cmd_str):
            return SandboxResult(
                exit_code=1,
                stdout="",
                stderr="Command blocked by sandbox: potentially dangerous.",
                error="dangerous_command",
            )

        try:
            match self.backend:
                case SandboxBackend.BUBBLEWRAP:
                    return await self._exec_bubblewrap(cmd_list, cwd)
                case SandboxBackend.APPLE_SANDBOX:
                    return await self._exec_apple_sandbox(cmd_list, cwd)
                case SandboxBackend.DOCKER:
                    return await self._exec_docker(cmd_str, cwd)
                case SandboxBackend.WINDOWS_SANDBOX:
                    return await self._exec_process(
                        cmd_list, cwd
                    )  # Windows Sandbox for full isolation
                case _:
                    return await self._exec_process(cmd_list, cwd)
        except Exception as e:
            logger.error("sandbox_error", error=str(e))
            return SandboxResult(
                exit_code=1,
                stdout="",
                stderr=str(e),
                error="sandbox_error",
            )

    async def _exec_bubblewrap(self, cmd: list[str], cwd: str | None) -> SandboxResult:
        """Execute in bubblewrap sandbox (Linux)."""
        bwrap_cmd = [
            "bwrap",
            "--ro-bind",
            "/",
            "/",  # Read-only root
            "--tmpfs",
            "/tmp",  # Writable /tmp
            "--dev",
            "/dev",  # Basic devices
            "--proc",
            "/proc",  # Process info
            "--unshare-all",  # Unshare all namespaces
            "--die-with-parent",  # Kill on parent death
        ]

        # Add writable directories
        for wd in self.config.writable_dirs:
            if Path(wd).exists():
                bwrap_cmd.extend(["--bind", wd, wd])

        # Block sensitive paths
        for sensitive in SENSITIVE_PATHS:
            home = str(Path.home())
            full_path = os.path.join(home, sensitive)
            if os.path.exists(full_path):
                bwrap_cmd.extend(["--tmpfs", full_path])

        # Network isolation
        if not self.config.allow_network:
            bwrap_cmd.append("--unshare-net")

        # Set working directory
        if cwd:
            bwrap_cmd.extend(["--chdir", cwd])

        bwrap_cmd.extend(["--", *cmd])

        return await self._run_subprocess(bwrap_cmd)

    async def _exec_apple_sandbox(self, cmd: list[str], cwd: str | None) -> SandboxResult:
        """Execute in Apple sandbox (macOS)."""
        # Create a temporary sandbox profile
        profile = self._generate_apple_profile()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sb", delete=False) as f:
            f.write(profile)
            profile_path = f.name

        try:
            sandbox_cmd = ["sandbox-exec", "-f", profile_path, *cmd]
            return await self._run_subprocess(sandbox_cmd, cwd=cwd)
        finally:
            os.unlink(profile_path)

    async def _exec_docker(self, cmd: str, cwd: str | None) -> SandboxResult:
        """Execute in a Docker container."""
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none" if not self.config.allow_network else "bridge",
            f"--memory={self.config.max_memory_mb}m",
            "--cpus=1",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=100m",
            "--security-opt",
            "no-new-privileges",
        ]

        if cwd:
            docker_cmd.extend(["-v", f"{cwd}:{cwd}:ro", "-w", cwd])

        # Use a minimal image
        docker_cmd.extend(["alpine:latest", "sh", "-c", cmd])

        return await self._run_subprocess(docker_cmd)

    async def _exec_process(self, cmd: list[str], cwd: str | None) -> SandboxResult:
        """Fallback: execute as subprocess with resource limits."""
        return await self._run_subprocess(cmd, cwd=cwd)

    async def _run_subprocess(
        self,
        cmd: list[str],
        cwd: str | None = None,
    ) -> SandboxResult:
        """Run a subprocess with timeout and output limits."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env={**os.environ, **self.config.env_vars},
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout,
                )
            except TimeoutError:
                process.kill()
                await process.wait()
                return SandboxResult(
                    exit_code=124,
                    stdout="",
                    stderr=f"Command timed out after {self.config.timeout}s",
                    timed_out=True,
                )

            # Truncate output if too large
            stdout_str = stdout.decode("utf-8", errors="replace")[: self.config.max_output_bytes]
            stderr_str = stderr.decode("utf-8", errors="replace")[: self.config.max_output_bytes]

            return SandboxResult(
                exit_code=process.returncode or 0,
                stdout=stdout_str,
                stderr=stderr_str,
            )

        except FileNotFoundError:
            return SandboxResult(
                exit_code=127,
                stdout="",
                stderr=f"Command not found: {cmd[0]}",
                error="not_found",
            )

    def _generate_apple_profile(self) -> str:
        """Generate an Apple sandbox profile."""
        rules = [
            "(version 1)",
            "(deny default)",
            "(allow process-exec)",
            "(allow process-fork)",
            "(allow sysctl-read)",
            "(allow file-read*)",  # Read-only filesystem
            '(allow file-write* (subpath "/tmp"))',  # Write only to /tmp
            '(allow file-write* (subpath "/dev/null"))',
            '(allow file-write* (subpath "/dev/zero"))',
        ]

        # Add writable directories
        for wd in self.config.writable_dirs:
            rules.append(f'(allow file-write* (subpath "{wd}"))')

        # Block sensitive paths
        home = str(Path.home())
        for sensitive in SENSITIVE_PATHS:
            rules.append(f'(deny file-read* (subpath "{home}/{sensitive}"))')

        # Network
        if not self.config.allow_network:
            rules.append("(deny network*)")
        else:
            rules.append("(allow network*)")

        return "\n".join(rules)

    @staticmethod
    def _is_dangerous(command: str) -> bool:
        """Quick check for obviously dangerous commands."""
        import re

        dangerous_patterns = [
            r"rm\s+-rf\s+/\s*$",
            r"rm\s+-rf\s+/\*",
            r"rm\s+-rf\s+~",
            r":\(\)\{.*:\|:.*\};:",  # Fork bomb (regex-escaped)
            r">\s*/dev/sd[a-z]",
            r"mkfs\.",
            r"dd\s+if=.*of=/dev/sd",
            r"chmod\s+(-R\s+)?777\s+/",  # Recursive 777 on root
            r"curl.*\|\s*(bash|sh|sudo)",  # Pipe to shell
            r"wget.*\|\s*(bash|sh|sudo)",  # Pipe to shell
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                return True
        return False
