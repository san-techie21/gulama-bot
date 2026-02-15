"""
Tests for sandbox escape prevention.

Verifies that the sandbox correctly blocks dangerous commands
and prevents access to sensitive paths.
"""

from __future__ import annotations

import pytest

from src.security.sandbox import Sandbox, SandboxConfig, SandboxResult


class TestSandboxEscapePrevention:
    """Verify sandbox isolation."""

    def test_dangerous_command_rm_rf(self):
        """rm -rf / should be blocked."""
        assert Sandbox._is_dangerous("rm -rf /")

    def test_dangerous_command_fork_bomb(self):
        """Fork bomb should be blocked."""
        assert Sandbox._is_dangerous(":(){ :|:& };:")

    def test_dangerous_command_mkfs(self):
        """Disk formatting should be blocked."""
        assert Sandbox._is_dangerous("mkfs.ext4 /dev/sda")

    def test_dangerous_command_dd(self):
        """dd to disk device should be blocked."""
        assert Sandbox._is_dangerous("dd if=/dev/zero of=/dev/sda")

    def test_dangerous_command_chmod_root(self):
        """chmod -R 777 / should be blocked."""
        assert Sandbox._is_dangerous("chmod -R 777 /")

    def test_safe_command_ls(self):
        """ls should be allowed."""
        assert not Sandbox._is_dangerous("ls -la")

    def test_safe_command_echo(self):
        """echo should be allowed."""
        assert not Sandbox._is_dangerous("echo hello world")

    def test_safe_command_python(self):
        """python script should be allowed."""
        assert not Sandbox._is_dangerous("python3 script.py")

    def test_sandbox_config_defaults(self):
        """Sandbox config should have secure defaults."""
        config = SandboxConfig()
        assert config.timeout == 30
        assert config.max_memory_mb == 512
        assert not config.allow_network  # Network off by default

    def test_sandbox_result_structure(self):
        """SandboxResult should have required fields."""
        result = SandboxResult(exit_code=0, stdout="output", stderr="")
        assert result.exit_code == 0
        assert result.stdout == "output"
        assert not result.timed_out

    @pytest.mark.asyncio
    async def test_dangerous_command_blocked_by_sandbox(self):
        """Sandbox.execute should block dangerous commands."""
        sandbox = Sandbox()
        result = await sandbox.execute("rm -rf /")
        assert result.exit_code != 0
        assert "blocked" in result.stderr.lower() or result.error == "dangerous_command"
