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

import os

from src.agent.persona import PersonaManager
from src.gateway.config import GulamaConfig
from src.memory.store import MemoryStore
from src.memory.vector_store import VectorStore
from src.utils.logging import get_logger

logger = get_logger("context_builder")

# Optional skills that require API keys or external configuration.
# Format: (skill_name, display_name, required_env_vars, setup_hint)
OPTIONAL_SKILL_REQUIREMENTS: list[tuple[str, str, list[str], str]] = [
    ("image_gen", "Image Generation", ["OPENAI_API_KEY"], "Set OPENAI_API_KEY for DALL-E, or STABILITY_API_KEY for Stable Diffusion"),
    ("spotify", "Spotify", ["SPOTIFY_ACCESS_TOKEN"], "Set SPOTIFY_ACCESS_TOKEN env var"),
    ("github", "GitHub", ["GITHUB_TOKEN"], "Set GITHUB_TOKEN env var or run 'gulama vault set GITHUB_TOKEN'"),
    ("email", "Email (Gmail/IMAP)", ["EMAIL_ADDRESS", "EMAIL_PASSWORD"], "Set EMAIL_ADDRESS and EMAIL_PASSWORD env vars"),
    ("calendar", "Google Calendar", ["GOOGLE_CALENDAR_ACCESS_TOKEN"], "Set GOOGLE_CALENDAR_ACCESS_TOKEN env var"),
    ("notion", "Notion", ["NOTION_TOKEN"], "Set NOTION_TOKEN env var or run 'gulama vault set NOTION_TOKEN'"),
    ("twitter", "Twitter/X", ["TWITTER_BEARER_TOKEN"], "Set TWITTER_BEARER_TOKEN env var"),
    ("smart_home", "Smart Home (Home Assistant)", ["HA_URL", "HA_TOKEN"], "Set HA_URL and HA_TOKEN env vars"),
    ("voice", "Voice (TTS/STT)", ["OPENAI_API_KEY"], "Set OPENAI_API_KEY for Whisper, or ELEVENLABS_API_KEY for ElevenLabs"),
    ("google_docs", "Google Docs/Drive", ["GOOGLE_DOCS_ACCESS_TOKEN"], "Set GOOGLE_DOCS_ACCESS_TOKEN env var"),
    ("productivity", "Productivity (Trello/Linear/Jira/Todoist)", ["TRELLO_API_KEY", "LINEAR_API_KEY", "JIRA_API_TOKEN", "TODOIST_API_TOKEN"], "Set the relevant API token for your service (any one of them)"),
]


def _build_skill_availability_block() -> str:
    """Build a dynamic block listing which optional features are ready vs need setup."""
    ready = []
    needs_setup = []

    for skill_name, display_name, env_vars, hint in OPTIONAL_SKILL_REQUIREMENTS:
        # Check if ANY of the required env vars are set
        has_key = any(os.getenv(var) for var in env_vars)
        if has_key:
            ready.append(display_name)
        else:
            needs_setup.append((display_name, hint))

    parts = []

    if ready:
        parts.append("Additional features READY to use: " + ", ".join(ready))

    if needs_setup:
        lines = [
            "Features that need API key setup (tell the user how to enable these if they ask):"
        ]
        for name, hint in needs_setup:
            lines.append(f"  - {name}: {hint}")
        parts.append("\n".join(lines))

    return "\n\n".join(parts) if parts else ""

AUTONOMY_DESCRIPTIONS = {
    0: "Observer — I ask before every action",
    1: "Assistant — I auto-read, ask before writes",
    2: "Co-pilot — I auto-handle safe actions, ask before shell/network",
    3: "Autopilot-cautious — I auto-handle most things, ask before destructive",
    4: "Autopilot — I auto-handle everything except financial/credential",
    5: "Full autonomous — unrestricted (dangerous)",
}

# Fallback system prompt when no persona is configured
DEFAULT_SYSTEM_PROMPT = """You are Gulama, a secure personal AI assistant running on the user's computer.

You have REAL capabilities — you are NOT a chatbot limited to text. You have tools that let you:
- READ and WRITE files on the user's computer (use the file_manager tool)
- LIST directory contents (use file_manager with operation="list" and the directory path)
- EXECUTE shell commands (use the shell_exec tool)
- SEARCH the web (use the web_search tool)
- SAVE and RECALL notes/facts (use the notes tool)

IMPORTANT: When the user asks you to do something (read a file, list a folder, run a command, search the web), USE YOUR TOOLS to do it. Do NOT say "I can't access your file system" — you CAN and SHOULD use the file_manager and shell_exec tools to fulfill requests.

Security (enforced automatically by the policy engine — you don't need to worry about this):
- All tool calls are security-checked before execution. Sensitive paths and dangerous commands are blocked automatically.
- Never leak user data, API keys, or personal information in your responses.
- Be transparent about what you're doing and why.
- Destructive actions (file deletion, certain shell commands) require user confirmation.

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
        """Build the system prompt from persona + context + skill availability."""
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
            base_prompt = persona.build_system_prompt(context)
        else:
            # Fallback to default template
            base_prompt = DEFAULT_SYSTEM_PROMPT.format(
                autonomy_level=level,
                autonomy_desc=AUTONOMY_DESCRIPTIONS.get(level, "unknown"),
                provider=self.config.llm.provider,
                model=self.config.llm.model,
                sandbox=self.config.security.sandbox_enabled,
                policy_engine=self.config.security.policy_engine_enabled,
            )

        # Append dynamic skill availability info
        skill_block = _build_skill_availability_block()
        if skill_block:
            base_prompt += "\n\n" + skill_block

        return base_prompt

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
