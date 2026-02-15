"""
Built-in file manager skill for Gulama.

Provides safe file operations:
- Read files (with size limits)
- Write/create files (with path validation)
- List directory contents
- Search files by pattern

All operations go through the policy engine and sandbox.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult


class FileManagerSkill(BaseSkill):
    """Safe file management operations."""

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="file_manager",
            description="Read, write, and manage files safely",
            version="0.1.0",
            author="gulama",
            required_actions=[ActionType.FILE_READ, ActionType.FILE_WRITE],
            is_builtin=True,
        )

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Execute a file operation."""
        operation = kwargs.get("operation", "read")
        path = kwargs.get("path", "")

        if not path:
            return SkillResult(success=False, output="", error="Path is required")

        # Validate path
        from src.security.input_validator import InputValidator
        validator = InputValidator()
        result = validator.validate_path(path)
        if not result.valid:
            return SkillResult(
                success=False, output="", error=result.blocked_reason,
            )

        match operation:
            case "read":
                return await self._read(result.sanitized)
            case "write":
                content = kwargs.get("content", "")
                return await self._write(result.sanitized, content)
            case "list":
                return await self._list_dir(result.sanitized)
            case _:
                return SkillResult(
                    success=False, output="",
                    error=f"Unknown operation: {operation}",
                )

    async def _read(self, path: str) -> SkillResult:
        """Read a file."""
        try:
            p = Path(path)
            if not p.exists():
                return SkillResult(success=False, output="", error="File not found")
            if not p.is_file():
                return SkillResult(success=False, output="", error="Not a file")
            if p.stat().st_size > 1024 * 1024:  # 1MB limit
                return SkillResult(
                    success=False, output="",
                    error="File too large (>1MB). Use a more specific tool.",
                )
            content = p.read_text(encoding="utf-8", errors="replace")
            return SkillResult(success=True, output=content)
        except Exception as e:
            return SkillResult(success=False, output="", error=str(e))

    async def _write(self, path: str, content: str) -> SkillResult:
        """Write to a file."""
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return SkillResult(
                success=True, output=f"Written {len(content)} bytes to {path}",
            )
        except Exception as e:
            return SkillResult(success=False, output="", error=str(e))

    async def _list_dir(self, path: str) -> SkillResult:
        """List directory contents."""
        try:
            p = Path(path)
            if not p.exists():
                return SkillResult(success=False, output="", error="Directory not found")
            if not p.is_dir():
                return SkillResult(success=False, output="", error="Not a directory")

            entries = []
            for item in sorted(p.iterdir()):
                kind = "dir" if item.is_dir() else "file"
                size = item.stat().st_size if item.is_file() else 0
                entries.append(f"{kind}\t{size}\t{item.name}")

            return SkillResult(
                success=True,
                output="\n".join(entries) if entries else "(empty directory)",
            )
        except Exception as e:
            return SkillResult(success=False, output="", error=str(e))

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "file_manager",
                "description": "Read, write, and list files. Operations: read, write, list",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["read", "write", "list"],
                            "description": "The file operation to perform",
                        },
                        "path": {
                            "type": "string",
                            "description": "File or directory path",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write (for write operation)",
                        },
                    },
                    "required": ["operation", "path"],
                },
            },
        }
