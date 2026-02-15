"""
Base skill interface for Gulama.

All skills (tools) implement this interface. Skills are how the agent
interacts with the world — file system, shell, network, etc.

Each skill:
- Has a unique name and description
- Declares required permissions
- Is verified via cryptographic signature before loading
- Runs inside the security sandbox
- Goes through the policy engine before execution
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from src.security.policy_engine import ActionType


@dataclass
class SkillMetadata:
    """Metadata about a skill."""

    name: str
    description: str
    version: str = "0.1.0"
    author: str = "gulama"
    required_actions: list[ActionType] = field(default_factory=list)
    is_builtin: bool = False
    signature: str = ""  # Cryptographic signature for verification


@dataclass
class SkillResult:
    """Result of a skill execution."""

    success: bool
    output: str
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseSkill(abc.ABC):
    """
    Abstract base class for all Gulama skills.

    Every skill must:
    1. Provide metadata (name, description, required permissions)
    2. Implement execute() for the actual work
    3. Implement get_tool_definition() for LLM function calling
    """

    @abc.abstractmethod
    def get_metadata(self) -> SkillMetadata:
        """Return skill metadata."""
        ...

    @abc.abstractmethod
    async def execute(self, **kwargs: Any) -> SkillResult:
        """Execute the skill with given parameters."""
        ...

    @abc.abstractmethod
    def get_tool_definition(self) -> dict[str, Any]:
        """
        Return the tool definition for LLM function calling.

        Format compatible with OpenAI/Anthropic tool calling:
        {
            "type": "function",
            "function": {
                "name": "skill_name",
                "description": "What the skill does",
                "parameters": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        }
        """
        ...

    @property
    def name(self) -> str:
        return self.get_metadata().name
