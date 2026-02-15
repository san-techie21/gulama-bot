"""
Context builder for Gulama agent — RAG-based, not full history dump.

Builds an optimized context window for LLM calls by:
1. Including the system prompt with agent persona
2. Retrieving relevant memories via similarity search
3. Including recent conversation messages
4. Injecting relevant facts and user preferences
5. Staying within the configured token budget

Unlike OpenClaw (which dumps entire conversation history),
Gulama uses RAG to retrieve only the most relevant context.
"""

from __future__ import annotations

from typing import Any

from src.gateway.config import GulamaConfig
from src.memory.store import MemoryStore
from src.utils.logging import get_logger

logger = get_logger("context_builder")

# System prompt — the agent's core persona and rules
SYSTEM_PROMPT = """You are Gulama, a secure personal AI assistant.

Core principles:
1. SECURITY FIRST — Never execute commands or access files without proper authorization.
2. PRIVACY — Never leak user data, API keys, or personal information.
3. HONESTY — Be transparent about your capabilities and limitations.
4. HELPFUL — Proactively assist while respecting autonomy boundaries.

You have access to various skills (tools) that must be executed within a security sandbox.
All actions are policy-checked before execution. Destructive actions require explicit user confirmation.

Current context:
- Autonomy Level: {autonomy_level} ({autonomy_desc})
- Provider: {provider} / {model}
- Security: Sandbox={sandbox}, Policy Engine={policy_engine}
"""

AUTONOMY_DESCRIPTIONS = {
    0: "Observer — I ask before every action",
    1: "Assistant — I auto-read, ask before writes",
    2: "Co-pilot — I auto-handle safe actions, ask before shell/network",
    3: "Autopilot-cautious — I auto-handle most things, ask before destructive",
    4: "Autopilot — I auto-handle everything except financial/credential",
    5: "Full autonomous — unrestricted (dangerous)",
}


class ContextBuilder:
    """
    Builds optimized context for LLM calls using RAG.

    Instead of dumping full conversation history (like OpenClaw),
    retrieves the most relevant pieces:
    - Recent messages (for continuity)
    - Relevant facts and preferences (for personalization)
    - Relevant past conversations (via vector search)
    """

    def __init__(self, config: GulamaConfig):
        self.config = config
        self.max_tokens = config.memory.max_context_tokens

    def build_messages(
        self,
        user_message: str,
        conversation_id: str | None = None,
        channel: str = "cli",
    ) -> list[dict[str, str]]:
        """
        Build the full messages list for an LLM call.

        Returns a list of messages in the format:
        [
            {"role": "system", "content": "system prompt..."},
            {"role": "user", "content": "older message..."},
            {"role": "assistant", "content": "older reply..."},
            ...
            {"role": "user", "content": "current message"},
        ]
        """
        messages: list[dict[str, str]] = []

        # 1. System prompt
        system_prompt = self._build_system_prompt()
        messages.append({"role": "system", "content": system_prompt})

        # 2. Relevant facts / user preferences
        facts_context = self._get_relevant_facts(user_message)
        if facts_context:
            messages.append({
                "role": "system",
                "content": f"Relevant context from memory:\n{facts_context}",
            })

        # 3. Recent conversation messages (for continuity)
        if conversation_id:
            history = self._get_conversation_history(conversation_id)
            messages.extend(history)

        # 4. Current user message
        messages.append({"role": "user", "content": user_message})

        # 5. Trim to token budget
        messages = self._trim_to_budget(messages)

        logger.info(
            "context_built",
            message_count=len(messages),
            estimated_tokens=self._estimate_tokens(messages),
        )

        return messages

    def _build_system_prompt(self) -> str:
        """Build the system prompt with current configuration."""
        level = self.config.autonomy.default_level
        return SYSTEM_PROMPT.format(
            autonomy_level=level,
            autonomy_desc=AUTONOMY_DESCRIPTIONS.get(level, "unknown"),
            provider=self.config.llm.provider,
            model=self.config.llm.model,
            sandbox=self.config.security.sandbox_enabled,
            policy_engine=self.config.security.policy_engine_enabled,
        )

    def _get_relevant_facts(self, query: str) -> str:
        """Retrieve relevant facts from memory via text search."""
        try:
            store = MemoryStore()
            store.open()
            facts = store.search_facts(query, limit=5)
            store.close()

            if not facts:
                return ""

            lines = []
            for fact in facts:
                category = fact.get("category", "")
                content = fact.get("content", "")
                lines.append(f"- [{category}] {content}")

            return "\n".join(lines)
        except Exception as e:
            logger.warning("fact_retrieval_failed", error=str(e))
            return ""

    def _get_conversation_history(
        self,
        conversation_id: str,
        max_messages: int = 20,
    ) -> list[dict[str, str]]:
        """Get recent messages from the conversation."""
        try:
            store = MemoryStore()
            store.open()
            messages = store.get_messages(conversation_id, limit=max_messages)
            store.close()

            return [
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages
                if msg["role"] in ("user", "assistant")
            ]
        except Exception as e:
            logger.warning("history_retrieval_failed", error=str(e))
            return []

    def _trim_to_budget(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        """Trim messages to stay within the token budget."""
        total = self._estimate_tokens(messages)

        if total <= self.max_tokens:
            return messages

        # Keep system prompt (first) and current message (last)
        # Trim from the middle (oldest conversation messages)
        if len(messages) <= 2:
            return messages

        system = messages[0]
        current = messages[-1]
        middle = messages[1:-1]

        # Remove oldest messages until within budget
        while middle and self._estimate_tokens([system] + middle + [current]) > self.max_tokens:
            middle.pop(0)

        return [system] + middle + [current]

    @staticmethod
    def _estimate_tokens(messages: list[dict[str, str]]) -> int:
        """Rough token count estimate (~4 chars per token)."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4
