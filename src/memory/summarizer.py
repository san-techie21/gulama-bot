"""
Memory summarization for Gulama.

Periodically compresses old conversations into summaries to keep the
memory store efficient. Uses the configured LLM to generate summaries.

Key behaviors:
- Conversations older than `summary_after_hours` get summarized
- Original messages are preserved but marked as summarized
- Summaries are stored as facts and in the vector store
- Reduces token usage for context building
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from src.memory.store import MemoryStore
from src.memory.vector_store import VectorStore
from src.utils.logging import get_logger

logger = get_logger("summarizer")

# Default prompt for summarization
SUMMARIZE_PROMPT = """Summarize the following conversation concisely.
Focus on: key topics discussed, decisions made, user preferences learned, and action items.
Keep the summary under 200 words.

Conversation:
{conversation_text}

Summary:"""


class MemorySummarizer:
    """
    Compresses old conversations into summaries.

    This keeps the memory store from growing unbounded while
    preserving the essential information for future context building.
    """

    def __init__(
        self,
        memory_store: MemoryStore,
        vector_store: VectorStore | None = None,
        summary_after_hours: int = 24,
    ):
        self.memory_store = memory_store
        self.vector_store = vector_store
        self.summary_after_hours = summary_after_hours

    async def summarize_old_conversations(
        self,
        llm_complete_fn: Any = None,
    ) -> list[str]:
        """
        Find and summarize conversations older than the threshold.

        Args:
            llm_complete_fn: Async function that takes messages list and returns response text.
                            If None, uses a simple extractive summary.

        Returns:
            List of conversation IDs that were summarized.
        """
        cutoff = datetime.now(UTC) - timedelta(hours=self.summary_after_hours)
        cutoff_str = cutoff.isoformat()

        # Find unsummarized conversations that ended before the cutoff
        rows = self.memory_store.conn.execute(
            "SELECT id, channel, started_at FROM conversations "
            "WHERE ended_at IS NOT NULL AND ended_at < ? AND summary IS NULL "
            "ORDER BY ended_at ASC LIMIT 10",
            (cutoff_str,),
        ).fetchall()

        summarized = []
        for row in rows:
            conv_id = row["id"]
            try:
                summary = await self._summarize_conversation(conv_id, llm_complete_fn)
                if summary:
                    # Store summary on the conversation
                    self.memory_store.conn.execute(
                        "UPDATE conversations SET summary = ? WHERE id = ?",
                        (summary, conv_id),
                    )
                    self.memory_store.conn.commit()

                    # Also store as a fact for retrieval
                    self.memory_store.add_fact(
                        category="conversation_summary",
                        content=summary,
                    )

                    # Add to vector store for semantic search
                    if self.vector_store and self.vector_store.is_available:
                        self.vector_store.add_conversation_summary(
                            conversation_id=conv_id,
                            summary=summary,
                            channel=row["channel"],
                            started_at=row["started_at"],
                        )

                    summarized.append(conv_id)
                    logger.info(
                        "conversation_summarized",
                        conversation_id=conv_id,
                        summary_length=len(summary),
                    )
            except Exception as e:
                logger.warning(
                    "summarization_failed",
                    conversation_id=conv_id,
                    error=str(e),
                )

        logger.info(
            "summarization_complete",
            summarized_count=len(summarized),
            checked_count=len(rows),
        )
        return summarized

    async def _summarize_conversation(
        self,
        conversation_id: str,
        llm_complete_fn: Any = None,
    ) -> str | None:
        """Generate a summary for a single conversation."""
        messages = self.memory_store.get_messages(conversation_id, limit=100)
        if not messages:
            return None

        # Build conversation text
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")

        conversation_text = "\n".join(lines)

        # If we have an LLM function, use it for abstractive summary
        if llm_complete_fn:
            try:
                prompt = SUMMARIZE_PROMPT.format(conversation_text=conversation_text[:4000])
                response = await llm_complete_fn([{"role": "user", "content": prompt}])
                return response.strip()
            except Exception as e:
                logger.warning("llm_summarization_failed", error=str(e))
                # Fall through to extractive summary

        # Extractive summary fallback (no LLM needed)
        return self._extractive_summary(messages)

    @staticmethod
    def _extractive_summary(messages: list[dict[str, Any]]) -> str:
        """Simple extractive summary — picks key messages."""
        if not messages:
            return ""

        user_messages = [m for m in messages if m.get("role") == "user"]
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]

        topics = []
        # Take first user message as topic
        if user_messages:
            first_content = user_messages[0].get("content", "")[:200]
            topics.append(f"Topic: {first_content}")

        # Count exchanges
        topics.append(
            f"Messages: {len(messages)} ({len(user_messages)} user, {len(assistant_messages)} assistant)"
        )

        # Take last assistant message as conclusion
        if assistant_messages:
            last_content = assistant_messages[-1].get("content", "")[:200]
            topics.append(f"Conclusion: {last_content}")

        return " | ".join(topics)

    async def extract_facts(
        self,
        conversation_id: str,
        llm_complete_fn: Any = None,
    ) -> list[dict[str, str]]:
        """
        Extract key facts from a conversation for long-term memory.

        Returns list of dicts with 'category' and 'content' keys.
        """
        messages = self.memory_store.get_messages(conversation_id, limit=50)
        if not messages:
            return []

        if llm_complete_fn:
            return await self._llm_extract_facts(messages, llm_complete_fn)

        return self._rule_extract_facts(messages)

    async def _llm_extract_facts(
        self,
        messages: list[dict[str, Any]],
        llm_complete_fn: Any,
    ) -> list[dict[str, str]]:
        """Use LLM to extract facts from messages."""
        conversation_text = "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in messages
        )

        prompt = (
            "Extract key facts from this conversation. "
            "Return each fact on a new line in the format: [category] fact\n"
            "Categories: preference, decision, knowledge, action_item\n\n"
            f"Conversation:\n{conversation_text[:3000]}\n\nFacts:"
        )

        try:
            response = await llm_complete_fn([{"role": "user", "content": prompt}])
            return self._parse_facts(response)
        except Exception as e:
            logger.warning("llm_fact_extraction_failed", error=str(e))
            return self._rule_extract_facts(messages)

    @staticmethod
    def _parse_facts(text: str) -> list[dict[str, str]]:
        """Parse LLM fact extraction output."""
        facts = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Parse [category] content format
            if line.startswith("[") and "]" in line:
                bracket_end = line.index("]")
                category = line[1:bracket_end].strip().lower()
                content = line[bracket_end + 1 :].strip()
                if content:
                    facts.append({"category": category, "content": content})
            elif line.startswith("- "):
                facts.append({"category": "knowledge", "content": line[2:].strip()})
        return facts

    @staticmethod
    def _rule_extract_facts(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Simple rule-based fact extraction (no LLM)."""
        facts = []
        for msg in messages:
            if msg.get("role") != "user":
                continue
            content = msg.get("content", "").lower()

            # Detect preferences
            preference_markers = [
                "i prefer",
                "i like",
                "i want",
                "i need",
                "always use",
                "never use",
                "my favorite",
            ]
            for marker in preference_markers:
                if marker in content:
                    facts.append(
                        {
                            "category": "preference",
                            "content": msg.get("content", "")[:200],
                        }
                    )
                    break

            # Detect decisions
            decision_markers = [
                "let's go with",
                "i decided",
                "we'll use",
                "the plan is",
                "i chose",
            ]
            for marker in decision_markers:
                if marker in content:
                    facts.append(
                        {
                            "category": "decision",
                            "content": msg.get("content", "")[:200],
                        }
                    )
                    break

        return facts[:10]  # Cap at 10 facts per conversation
