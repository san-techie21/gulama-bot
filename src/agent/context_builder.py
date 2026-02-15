"""
Context builder for Gulama agent — RAG-based, not full history dump.

Builds an optimized context window for LLM calls by:
1. Including the system prompt with agent persona
2. Retrieving relevant memories via vector similarity (ChromaDB)
3. Including recent conversation messages (sliding window)
4. Injecting relevant facts and user preferences
5. Staying within the configured token budget

Unlike OpenClaw (which dumps entire conversation history),
Gulama uses RAG to retrieve only the most relevant context.

Context budget allocation:
- System prompt: ~500 tokens
- Relevant memories (RAG): ~2000 tokens
- Recent conversation: ~3000 tokens
- User preferences: ~500 tokens
- Tool descriptions: ~2000 tokens
- Total: ~8000 tokens (vs OpenClaw's 10,000+ for basic queries)
"""

from __future__ import annotations

from src.agent.persona import PersonaManager
from src.gateway.config import GulamaConfig
from src.memory.store import MemoryStore
from src.memory.vector_store import VectorStore
from src.utils.logging import get_logger

logger = get_logger("context_builder")

AUTONOMY_DESCRIPTIONS = {
    0: "Observer — I ask before every action",
    1: "Assistant — I auto-read, ask before writes",
    2: "Co-pilot — I auto-handle safe actions, ask before shell/network",
    3: "Autopilot-cautious — I auto-handle most things, ask before destructive",
    4: "Autopilot — I auto-handle everything except financial/credential",
    5: "Full autonomous — unrestricted (dangerous)",
}

# Fallback system prompt when no persona is configured
DEFAULT_SYSTEM_PROMPT = """You are Gulama, a secure personal AI assistant.

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


class ContextBuilder:
    """
    Builds optimized context for LLM calls using RAG.

    Instead of dumping full conversation history (like OpenClaw),
    retrieves the most relevant pieces:
    - Recent messages (for continuity)
    - Relevant facts and preferences (for personalization, via vector search)
    - Relevant past conversations (via vector similarity)
    """

    def __init__(
        self,
        config: GulamaConfig,
        vector_store: VectorStore | None = None,
        persona_manager: PersonaManager | None = None,
    ):
        self.config = config
        self.max_tokens = config.memory.max_context_tokens
        self.vector_store = vector_store
        self.persona_manager = persona_manager

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
            {"role": "system", "content": "relevant memories..."},
            {"role": "user", "content": "older message..."},
            {"role": "assistant", "content": "older reply..."},
            ...
            {"role": "user", "content": "current message"},
        ]
        """
        messages: list[dict[str, str]] = []

        # 1. System prompt (from persona or default)
        system_prompt = self._build_system_prompt()
        messages.append({"role": "system", "content": system_prompt})

        # 2. RAG: Relevant facts via vector similarity
        rag_context = self._get_rag_context(user_message)
        if rag_context:
            messages.append(
                {
                    "role": "system",
                    "content": f"Relevant context from memory:\n{rag_context}",
                }
            )

        # 3. Related past conversations (via vector similarity)
        related_convos = self._get_related_conversations(user_message)
        if related_convos:
            messages.append(
                {
                    "role": "system",
                    "content": f"Related past conversations:\n{related_convos}",
                }
            )

        # 4. Recent conversation messages (sliding window for continuity)
        if conversation_id:
            history = self._get_conversation_history(conversation_id)
            messages.extend(history)

        # 5. Current user message
        messages.append({"role": "user", "content": user_message})

        # 6. Trim to token budget
        messages = self._trim_to_budget(messages)

        logger.info(
            "context_built",
            message_count=len(messages),
            estimated_tokens=self._estimate_tokens(messages),
            has_rag=bool(rag_context),
            has_related=bool(related_convos),
        )

        return messages

    def _build_system_prompt(self) -> str:
        """Build the system prompt from persona + context."""
        level = self.config.autonomy.default_level

        context = {
            "Autonomy Level": f"{level} ({AUTONOMY_DESCRIPTIONS.get(level, 'unknown')})",
            "Provider": f"{self.config.llm.provider} / {self.config.llm.model}",
            "Sandbox": str(self.config.security.sandbox_enabled),
            "Policy Engine": str(self.config.security.policy_engine_enabled),
        }

        # Use persona if available
        if self.persona_manager:
            persona = self.persona_manager.active
            return persona.build_system_prompt(context)

        # Fallback to default template
        return DEFAULT_SYSTEM_PROMPT.format(
            autonomy_level=level,
            autonomy_desc=AUTONOMY_DESCRIPTIONS.get(level, "unknown"),
            provider=self.config.llm.provider,
            model=self.config.llm.model,
            sandbox=self.config.security.sandbox_enabled,
            policy_engine=self.config.security.policy_engine_enabled,
        )

    def _get_rag_context(self, query: str) -> str:
        """Retrieve relevant facts and messages via vector similarity."""
        if not self.vector_store or not self.vector_store.is_available:
            return self._get_text_search_facts(query)

        parts = []

        # Search facts (user preferences, knowledge, decisions)
        facts = self.vector_store.search_facts(query, limit=5)
        if facts:
            fact_lines = []
            for f in facts:
                category = f.get("metadata", {}).get("category", "")
                content = f.get("content", "")
                similarity = f.get("similarity", 0)
                if similarity > 0.3:  # Only include reasonably relevant facts
                    fact_lines.append(f"- [{category}] {content}")
            if fact_lines:
                parts.append("Facts:\n" + "\n".join(fact_lines))

        # Search related messages from other conversations
        related_messages = self.vector_store.search_messages(query, limit=3)
        if related_messages:
            msg_lines = []
            for m in related_messages:
                content = m.get("content", "")
                similarity = m.get("similarity", 0)
                if similarity > 0.4:  # Higher threshold for cross-conversation
                    msg_lines.append(f"- {content[:200]}")
            if msg_lines:
                parts.append("Related messages:\n" + "\n".join(msg_lines))

        return "\n\n".join(parts) if parts else ""

    def _get_text_search_facts(self, query: str) -> str:
        """Fallback: text-based fact retrieval when vector store is unavailable."""
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

    def _get_related_conversations(self, query: str) -> str:
        """Find related past conversation summaries via vector search."""
        if not self.vector_store or not self.vector_store.is_available:
            return ""

        conversations = self.vector_store.search_conversations(query, limit=3)
        if not conversations:
            return ""

        lines = []
        for conv in conversations:
            content = conv.get("content", "")
            similarity = conv.get("similarity", 0)
            if similarity > 0.3 and content:
                lines.append(f"- {content[:300]}")

        return "\n".join(lines) if lines else ""

    def _get_conversation_history(
        self,
        conversation_id: str,
        max_messages: int = 20,
    ) -> list[dict[str, str]]:
        """Get recent messages from the current conversation."""
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

        # Keep system prompts (first 1-3) and current message (last)
        # Trim from the middle (oldest conversation messages)
        if len(messages) <= 2:
            return messages

        # Find where system messages end
        system_end = 0
        for i, msg in enumerate(messages):
            if msg["role"] == "system":
                system_end = i + 1
            else:
                break

        system_msgs = messages[:system_end]
        current = messages[-1]
        middle = messages[system_end:-1]

        # Remove oldest middle messages until within budget
        while middle and self._estimate_tokens(system_msgs + middle + [current]) > self.max_tokens:
            middle.pop(0)

        return system_msgs + middle + [current]

    @staticmethod
    def _estimate_tokens(messages: list[dict[str, str]]) -> int:
        """Rough token count estimate (~4 chars per token)."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4
