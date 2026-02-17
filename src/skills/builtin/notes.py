"""
Built-in notes/memory skill for Gulama.

Provides persistent memory operations:
- Save facts about the user (preferences, knowledge)
- Recall saved facts
- Search memory
"""

from __future__ import annotations

from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult


class NotesSkill(BaseSkill):
    """Persistent memory and notes management."""

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="notes",
            description="Save and recall facts, notes, and user preferences",
            version="0.1.0",
            author="gulama",
            required_actions=[ActionType.MEMORY_READ, ActionType.MEMORY_WRITE],
            is_builtin=True,
        )

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Execute a notes operation."""
        operation = kwargs.get("operation", "search")

        match operation:
            case "save":
                return await self._save(
                    category=kwargs.get("category", "knowledge"),
                    content=kwargs.get("content", ""),
                )
            case "search":
                return await self._search(kwargs.get("query", ""))
            case "list":
                return await self._list(kwargs.get("category"))
            case _:
                return SkillResult(
                    success=False,
                    output="",
                    error=f"Unknown operation: {operation}",
                )

    async def _save(self, category: str, content: str) -> SkillResult:
        """Save a fact to memory."""
        if not content:
            return SkillResult(success=False, output="", error="Content is required")

        valid_categories = {"preference", "identity", "knowledge", "skill", "context", "conversation_summary", "decision"}
        if category not in valid_categories:
            category = "knowledge"

        from src.memory.store import MemoryStore

        store = MemoryStore()
        store.open()
        try:
            fact_id = store.add_fact(category=category, content=content)
        finally:
            store.close()

        return SkillResult(
            success=True,
            output=f"Saved to memory [{category}]: {content[:100]}",
            metadata={"fact_id": fact_id},
        )

    async def _search(self, query: str) -> SkillResult:
        """Search memory for facts."""
        if not query:
            return SkillResult(success=False, output="", error="Query is required")

        from src.memory.store import MemoryStore

        store = MemoryStore()
        store.open()
        try:
            facts = store.search_facts(query, limit=10)
        finally:
            store.close()

        if not facts:
            return SkillResult(success=True, output="No matching facts found.")

        lines = []
        for fact in facts:
            lines.append(f"[{fact['category']}] {fact['content']}")

        return SkillResult(
            success=True,
            output="\n".join(lines),
            metadata={"count": len(facts)},
        )

    async def _list(self, category: str | None = None) -> SkillResult:
        """List facts, optionally filtered by category."""
        from src.memory.store import MemoryStore

        store = MemoryStore()
        store.open()
        try:
            facts = store.get_facts(category=category, limit=20)
        finally:
            store.close()

        if not facts:
            return SkillResult(success=True, output="No facts stored yet.")

        lines = []
        for fact in facts:
            lines.append(f"[{fact['category']}] {fact['content']}")

        return SkillResult(
            success=True,
            output="\n".join(lines),
            metadata={"count": len(facts)},
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "notes",
                "description": "Save, search, and list notes and facts from memory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["save", "search", "list"],
                            "description": "save = store a fact, search = find facts, list = show all",
                        },
                        "category": {
                            "type": "string",
                            "enum": ["preference", "identity", "knowledge", "skill", "context", "conversation_summary", "decision"],
                            "description": "Category for save/list operations",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to save (for save operation)",
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query (for search operation)",
                        },
                    },
                    "required": ["operation"],
                },
            },
        }
