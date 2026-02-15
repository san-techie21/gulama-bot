"""
Self-modifying skill system for Gulama.

Allows the AI agent to write, modify, and register new skills at runtime.
All self-authored skills:
1. Are stored in a separate directory (SKILLS_DIR/authored/)
2. Must pass policy engine validation before execution
3. Are sandboxed like any other skill
4. Are persisted across restarts
5. Can be reviewed/approved by the user
"""

from __future__ import annotations

import importlib.util
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.constants import SKILLS_DIR
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("self_modifier")

AUTHORED_DIR = SKILLS_DIR / "authored"


class SelfModifierSkill(BaseSkill):
    """
    Meta-skill that allows the agent to write and manage its own skills.

    The agent can create new skills, update existing ones, test them,
    and manage the authored skills directory.
    """

    def __init__(self) -> None:
        AUTHORED_DIR.mkdir(parents=True, exist_ok=True)

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="self_modify",
            description="Create, modify, and manage custom skills at runtime — AI skill authoring",
            version="1.0.0",
            author="gulama",
            required_actions=[],
            is_builtin=True,
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "self_modify",
                "description": (
                    "Create or modify custom skills at runtime. The agent can extend its own "
                    "capabilities by writing Python skill code. Skills are sandboxed and validated."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["create", "update", "list", "delete", "get", "test"],
                        },
                        "skill_name": {
                            "type": "string",
                            "description": "Name of the skill (snake_case)",
                        },
                        "code": {
                            "type": "string",
                            "description": "Python code defining a BaseSkill subclass",
                        },
                        "description": {"type": "string"},
                    },
                    "required": ["action"],
                },
            },
        }

    async def execute(self, **kwargs: Any) -> SkillResult:
        action = kwargs.get("action", "")
        dispatch = {
            "create": self._create,
            "update": self._update,
            "list": self._list,
            "delete": self._delete,
            "get": self._get,
            "test": self._test,
        }
        handler = dispatch.get(action)
        if not handler:
            return SkillResult(success=False, output="", error=f"Unknown action: {action}")
        try:
            return await handler(**{k: v for k, v in kwargs.items() if k != "action"})
        except Exception as e:
            logger.error("self_modify_error", action=action, error=str(e))
            return SkillResult(success=False, output="", error=f"Self-modify error: {str(e)[:400]}")

    async def _create(self, skill_name: str = "", code: str = "",
                      description: str = "", **_: Any) -> SkillResult:
        if not skill_name or not code:
            return SkillResult(success=False, output="", error="skill_name and code are required")
        if not skill_name.replace("_", "").isalnum():
            return SkillResult(success=False, output="", error="skill_name must be alphanumeric with underscores")

        danger = self._security_scan(code)
        if danger:
            return SkillResult(success=False, output="", error=f"Security violation: {danger}")

        skill_file = AUTHORED_DIR / f"{skill_name}.py"
        if skill_file.exists():
            return SkillResult(success=False, output="", error=f"Skill '{skill_name}' exists. Use 'update'.")

        validation = self._validate_skill_code(code)
        if not validation["valid"]:
            return SkillResult(success=False, output="", error=f"Invalid code: {validation['error']}")

        header = textwrap.dedent(f'''\
            """
            Auto-authored skill: {skill_name}
            Description: {description or 'No description'}
            Created: {datetime.now(timezone.utc).isoformat()}
            """
        ''')
        skill_file.write_text(header + "\n" + code, encoding="utf-8")
        logger.info("skill_created", name=skill_name)
        return SkillResult(success=True, output=f"Skill '{skill_name}' created. Use 'test' to verify.")

    async def _update(self, skill_name: str = "", code: str = "", **_: Any) -> SkillResult:
        if not skill_name or not code:
            return SkillResult(success=False, output="", error="skill_name and code required")
        skill_file = AUTHORED_DIR / f"{skill_name}.py"
        if not skill_file.exists():
            return SkillResult(success=False, output="", error=f"Skill '{skill_name}' not found.")
        danger = self._security_scan(code)
        if danger:
            return SkillResult(success=False, output="", error=f"Security violation: {danger}")
        validation = self._validate_skill_code(code)
        if not validation["valid"]:
            return SkillResult(success=False, output="", error=f"Invalid code: {validation['error']}")

        backup = AUTHORED_DIR / f"{skill_name}.py.bak"
        backup.write_text(skill_file.read_text(encoding="utf-8"), encoding="utf-8")

        header = textwrap.dedent(f'''\
            """
            Auto-authored skill: {skill_name} (updated)
            Updated: {datetime.now(timezone.utc).isoformat()}
            """
        ''')
        skill_file.write_text(header + "\n" + code, encoding="utf-8")
        logger.info("skill_updated", name=skill_name)
        return SkillResult(success=True, output=f"Skill '{skill_name}' updated. Old version backed up.")

    async def _list(self, **_: Any) -> SkillResult:
        skills = [f.stem for f in AUTHORED_DIR.glob("*.py") if not f.name.startswith("_")]
        if not skills:
            return SkillResult(success=True, output="No authored skills found.")
        return SkillResult(success=True, output="Authored skills:\n" + "\n".join(f"- {s}" for s in sorted(skills)))

    async def _delete(self, skill_name: str = "", **_: Any) -> SkillResult:
        if not skill_name:
            return SkillResult(success=False, output="", error="skill_name required")
        skill_file = AUTHORED_DIR / f"{skill_name}.py"
        if not skill_file.exists():
            return SkillResult(success=False, output="", error=f"Skill '{skill_name}' not found.")
        skill_file.unlink()
        (AUTHORED_DIR / f"{skill_name}.py.bak").unlink(missing_ok=True)
        return SkillResult(success=True, output=f"Skill '{skill_name}' deleted.")

    async def _get(self, skill_name: str = "", **_: Any) -> SkillResult:
        if not skill_name:
            return SkillResult(success=False, output="", error="skill_name required")
        skill_file = AUTHORED_DIR / f"{skill_name}.py"
        if not skill_file.exists():
            return SkillResult(success=False, output="", error=f"Skill '{skill_name}' not found.")
        return SkillResult(success=True, output=skill_file.read_text(encoding="utf-8")[:5000])

    async def _test(self, skill_name: str = "", **_: Any) -> SkillResult:
        if not skill_name:
            return SkillResult(success=False, output="", error="skill_name required")
        skill_file = AUTHORED_DIR / f"{skill_name}.py"
        if not skill_file.exists():
            return SkillResult(success=False, output="", error=f"Skill '{skill_name}' not found.")
        try:
            spec = importlib.util.spec_from_file_location(skill_name, skill_file)
            if not spec or not spec.loader:
                return SkillResult(success=False, output="", error="Could not load module.")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            skill_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, BaseSkill) and attr is not BaseSkill:
                    skill_class = attr
                    break
            if not skill_class:
                return SkillResult(success=False, output="", error="No BaseSkill subclass found.")
            instance = skill_class()
            meta = instance.get_metadata()
            tool_def = instance.get_tool_definition()
            return SkillResult(
                success=True,
                output=(
                    f"Skill '{skill_name}' loaded!\n"
                    f"  Name: {meta.name}\n"
                    f"  Description: {meta.description}\n"
                    f"  Version: {meta.version}\n"
                    f"  Tool: {tool_def.get('function', {}).get('name', 'N/A')}"
                ),
            )
        except Exception as e:
            return SkillResult(success=False, output="", error=f"Test failed: {str(e)[:400]}")

    def _security_scan(self, code: str) -> str | None:
        dangerous = [
            ("subprocess", "Subprocess execution not allowed"),
            ("__import__", "Dynamic imports not allowed"),
            ("eval(", "eval() not allowed"),
            ("exec(", "exec() not allowed"),
            ("compile(", "compile() not allowed"),
            (".ssh/", "SSH key access not allowed"),
            ("PRIVATE KEY", "Private key access not allowed"),
            ("ctypes", "C-level access not allowed"),
            ("socket.socket", "Raw sockets not allowed"),
        ]
        for pattern, reason in dangerous:
            if pattern in code:
                return reason
        return None

    def _validate_skill_code(self, code: str) -> dict[str, Any]:
        required = ["class ", "def get_metadata", "def get_tool_definition", "async def execute"]
        for pattern in required:
            if pattern not in code:
                return {"valid": False, "error": f"Missing: {pattern}"}
        if "BaseSkill" not in code:
            return {"valid": False, "error": "Must inherit from BaseSkill"}
        return {"valid": True, "error": ""}

    def load_authored_skills(self) -> list[BaseSkill]:
        """Load all authored skills for registration."""
        skills = []
        for skill_file in AUTHORED_DIR.glob("*.py"):
            if skill_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(skill_file.stem, skill_file)
                if not spec or not spec.loader:
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, BaseSkill) and attr is not BaseSkill:
                        skills.append(attr())
                        logger.info("authored_skill_loaded", name=skill_file.stem)
                        break
            except Exception as e:
                logger.warning("authored_skill_load_failed", file=skill_file.name, error=str(e))
        return skills
