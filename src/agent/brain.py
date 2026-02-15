"""
Agent brain for Gulama — the central reasoning engine.

The brain:
1. Receives user messages from any channel
2. Builds context via RAG (not full history dump)
3. Routes to the appropriate LLM via the universal router
4. Processes tool calls through the security sandbox
5. Tracks tokens/cost and stores in memory
6. Returns responses (sync or streaming)

This is a simple brain for Phase 0 — no tool execution yet.
Tool execution and policy engine integration come in Phase 1.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from src.agent.context_builder import ContextBuilder
from src.agent.llm_router import LLMRouter
from src.gateway.config import GulamaConfig
from src.memory.store import MemoryStore
from src.utils.logging import get_logger

logger = get_logger("brain")


class AgentBrain:
    """
    Central reasoning engine for Gulama.

    Phase 0: Simple chat (no tools)
    Phase 1: + tool execution via sandbox + policy engine
    Phase 2: + RAG with vector search + autonomy enforcement
    """

    def __init__(self, config: GulamaConfig, api_key: str = ""):
        self.config = config
        self.context_builder = ContextBuilder(config=config)
        self._api_key = api_key
        self._router: LLMRouter | None = None

    @property
    def router(self) -> LLMRouter:
        """Lazy-init the LLM router (needs API key from vault)."""
        if self._router is None:
            api_key = self._api_key or self._load_api_key()
            self._router = LLMRouter(config=self.config, api_key=api_key)
        return self._router

    async def process_message(
        self,
        message: str,
        conversation_id: str | None = None,
        channel: str = "cli",
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a user message and return the agent's response.

        Returns:
            {
                "response": str,
                "conversation_id": str,
                "tokens_used": int,
                "cost_usd": float,
            }
        """
        store = MemoryStore()
        store.open()

        try:
            # Create or continue conversation
            if not conversation_id:
                conversation_id = store.create_conversation(
                    channel=channel, user_id=user_id,
                )

            # Store user message
            store.add_message(conversation_id, role="user", content=message)

            # Check budget
            if not self.router.check_budget():
                response_text = (
                    "Daily token budget exceeded. "
                    f"Budget: ${self.config.cost.daily_budget_usd:.2f}/day. "
                    "Please wait until tomorrow or increase the budget in config."
                )
                store.add_message(conversation_id, role="assistant", content=response_text)
                return {
                    "response": response_text,
                    "conversation_id": conversation_id,
                    "tokens_used": 0,
                    "cost_usd": 0.0,
                }

            # Build context
            messages = self.context_builder.build_messages(
                user_message=message,
                conversation_id=conversation_id,
                channel=channel,
            )

            # Call LLM
            result = await self.router.chat(messages=messages)

            response_text = result["content"]
            input_tokens = result["input_tokens"]
            output_tokens = result["output_tokens"]
            cost_usd = result["cost_usd"]

            # Store assistant response
            store.add_message(
                conversation_id,
                role="assistant",
                content=response_text,
                token_count=output_tokens,
            )

            # Record cost
            store.record_cost(
                provider=result.get("provider", self.config.llm.provider),
                model=result.get("model", self.config.llm.model),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                channel=channel,
                conversation_id=conversation_id,
            )

            logger.info(
                "message_processed",
                conversation_id=conversation_id[:12],
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=round(cost_usd, 6),
            )

            return {
                "response": response_text,
                "conversation_id": conversation_id,
                "tokens_used": input_tokens + output_tokens,
                "cost_usd": cost_usd,
            }

        except Exception as e:
            logger.error("brain_error", error=str(e))
            return {
                "response": f"Error: {str(e)}",
                "conversation_id": conversation_id or "",
                "tokens_used": 0,
                "cost_usd": 0.0,
            }
        finally:
            store.close()

    async def stream_message(
        self,
        message: str,
        conversation_id: str | None = None,
        channel: str = "cli",
        user_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream a response from the agent.

        Yields:
            {"type": "chunk", "content": "partial text..."}
            {"type": "complete", "content": "full text", "conversation_id": ..., ...}
        """
        store = MemoryStore()
        store.open()

        try:
            if not conversation_id:
                conversation_id = store.create_conversation(
                    channel=channel, user_id=user_id,
                )

            store.add_message(conversation_id, role="user", content=message)

            if not self.router.check_budget():
                yield {
                    "type": "complete",
                    "content": "Daily token budget exceeded.",
                    "conversation_id": conversation_id,
                    "tokens_used": 0,
                    "cost_usd": 0.0,
                }
                return

            messages = self.context_builder.build_messages(
                user_message=message,
                conversation_id=conversation_id,
                channel=channel,
            )

            full_content = ""
            async for chunk in self.router.stream(messages=messages):
                if chunk["type"] == "chunk":
                    yield chunk
                elif chunk["type"] == "complete":
                    full_content = chunk["content"]

                    store.add_message(
                        conversation_id,
                        role="assistant",
                        content=full_content,
                        token_count=chunk.get("output_tokens", 0),
                    )

                    store.record_cost(
                        provider=self.config.llm.provider,
                        model=chunk.get("model", self.config.llm.model),
                        input_tokens=chunk.get("input_tokens", 0),
                        output_tokens=chunk.get("output_tokens", 0),
                        cost_usd=chunk.get("cost_usd", 0.0),
                        channel=channel,
                        conversation_id=conversation_id,
                    )

                    yield {
                        "type": "complete",
                        "content": full_content,
                        "conversation_id": conversation_id,
                        "tokens_used": chunk.get("input_tokens", 0) + chunk.get("output_tokens", 0),
                        "cost_usd": chunk.get("cost_usd", 0.0),
                    }
                elif chunk["type"] == "error":
                    yield chunk

        except Exception as e:
            logger.error("stream_error", error=str(e))
            yield {"type": "error", "content": str(e)}
        finally:
            store.close()

    def _load_api_key(self) -> str:
        """Load API key from environment or secrets vault."""
        import os

        # Load .env file if present
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Try environment variables (priority order)
        env_key = (
            os.getenv("LLM_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("GROQ_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
        )
        if env_key:
            logger.info("api_key_loaded", source="environment")
            return env_key

        # Try vault
        try:
            from src.security.secrets_vault import SecretsVault

            vault = SecretsVault()
            if vault.is_initialized:
                logger.info("api_key_loaded", source="vault")
                # Vault requires unlock — handled at setup time
        except Exception:
            pass

        logger.warning(
            "no_api_key",
            msg="No API key found. Set LLM_API_KEY env var or run 'gulama setup'.",
        )
        return ""
