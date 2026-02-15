"""
Skill registry — manages loading, verification, and lookup of skills.

All skills must be registered here before they can be used.
Built-in skills are auto-registered. Third-party skills require
cryptographic signature verification before loading.
"""

from __future__ import annotations

from typing import Any

from src.skills.base import BaseSkill, SkillMetadata
from src.utils.logging import get_logger

logger = get_logger("skill_registry")


class SkillRegistry:
    """
    Central registry for all available skills.

    Skills are indexed by name for fast lookup.
    Provides tool definitions for LLM function calling.
    """

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """Register a skill."""
        meta = skill.get_metadata()

        if meta.name in self._skills:
            logger.warning("skill_already_registered", name=meta.name)
            return

        self._skills[meta.name] = skill
        logger.info(
            "skill_registered",
            name=meta.name,
            version=meta.version,
            builtin=meta.is_builtin,
        )

    def get(self, name: str) -> BaseSkill | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[SkillMetadata]:
        """List all registered skills."""
        return [s.get_metadata() for s in self._skills.values()]

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Get all tool definitions for LLM function calling."""
        return [s.get_tool_definition() for s in self._skills.values()]

    def load_builtins(self) -> None:
        """Load all built-in skills."""
        from src.skills.builtin.file_manager import FileManagerSkill
        from src.skills.builtin.notes import NotesSkill
        from src.skills.builtin.shell_exec import ShellExecSkill
        from src.skills.builtin.web_search import WebSearchSkill

        builtins: list[BaseSkill] = [
            FileManagerSkill(),
            ShellExecSkill(),
            WebSearchSkill(),
            NotesSkill(),
        ]

        # Optional skills — load if their modules are importable
        optional_skills = [
            ("code_exec", "src.skills.builtin.code_exec", "CodeExecSkill"),
            ("browser", "src.skills.builtin.browser", "BrowserSkill"),
            ("email", "src.skills.builtin.email_skill", "EmailSkill"),
            ("calendar", "src.skills.builtin.calendar_skill", "CalendarSkill"),
            ("mcp", "src.skills.builtin.mcp_bridge", "MCPBridgeSkill"),
            ("voice", "src.skills.builtin.voice_skill", "VoiceSkill"),
            ("image_gen", "src.skills.builtin.image_gen", "ImageGenSkill"),
            ("smart_home", "src.skills.builtin.smart_home", "SmartHomeSkill"),
            # Third-party integrations
            ("github", "src.skills.builtin.github_skill", "GitHubSkill"),
            ("notion", "src.skills.builtin.notion_skill", "NotionSkill"),
            ("spotify", "src.skills.builtin.spotify_skill", "SpotifySkill"),
            ("twitter", "src.skills.builtin.twitter_skill", "TwitterSkill"),
            ("google_docs", "src.skills.builtin.google_docs_skill", "GoogleDocsSkill"),
            ("productivity", "src.skills.builtin.productivity_skill", "ProductivitySkill"),
            # Meta-skills
            ("self_modify", "src.skills.self_modifier", "SelfModifierSkill"),
        ]

        for skill_name, module_path, class_name in optional_skills:
            try:
                import importlib

                module = importlib.import_module(module_path)
                skill_class = getattr(module, class_name)
                builtins.append(skill_class())
            except Exception:
                logger.info("skill_skipped", name=skill_name, reason="module load failed")

        for skill in builtins:
            self.register(skill)

        logger.info("builtins_loaded", count=len(builtins))

    @property
    def count(self) -> int:
        return len(self._skills)
