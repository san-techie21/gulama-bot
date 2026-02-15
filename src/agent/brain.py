"""
Agent brain for Gulama — the central reasoning engine.

Phase 1 — Full agentic tool execution with security pipeline.

The brain:
1. Receives user messages from any channel
2. Builds context via RAG (not full history dump)
3. Routes to the appropriate LLM via the universal router
4. Runs an agentic tool-calling loop (LLM -> tools -> LLM -> ...)
5. All tool calls go through the 8-step security pipeline
6. Tracks tokens/cost and stores in memory
7. Returns responses (sync or streaming)
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from src.agent.context_builder import ContextBuilder
from src.agent.llm_router import LLMRouter
from src.agent.tool_executor import ToolExecutor
from src.gateway.config import GulamaConfig
from src.memory.store import MemoryStore
from src.security.audit_logger import AuditLogger
from src.security.canary import CanarySystem
from src.security.egress_filter import EgressFilter
from src.security.policy_engine import PolicyEngine
from src.skills.registry import SkillRegistry
from src.utils.logging import get_logger

logger = get_logger("brain")

# Safety limit: maximum rounds of LLM -> tool -> LLM before forcing text response
MAX_TOOL_ROUNDS = 10


class AgentBrain:
    """
    Central reasoning engine for Gulama.

    Runs a full agentic loop:
    1. LLM receives user message + tool definitions
    2. LLM either responds with text OR requests tool calls
    3. Tool calls execute through the security pipeline
    4. Tool results are injected back into conversation
    5. LLM receives updated conversation and may call more tools
    6. Loop until LLM responds with text (or MAX_TOOL_ROUNDS hit)
    """

    def __init__(self, config: GulamaConfig, api_key: str = ""):
        self.config = config
        self.context_builder = ContextBuilder(config=config)
        self._api_key = api_key
        self._router: LLMRouter | None = None
        self._tool_executor: ToolExecutor | None = None
        self._skill_registry: SkillRegistry | None = None

    # ── Lazy-initialized components ────────────────────────────

    @property
    def router(self) -> LLMRouter:
        """Lazy-init the LLM router (needs API key from vault)."""
        if self._router is None:
            api_key = self._api_key or self._load_api_key()
            self._auto_detect_provider(api_key)
            self._router = LLMRouter(config=self.config, api_key=api_key)
        return self._router

    @property
    def skill_registry(self) -> SkillRegistry:
        """Lazy-init skill registry and load built-in skills."""
        if self._skill_registry is None:
            self._skill_registry = SkillRegistry()
            self._skill_registry.load_builtins()
            logger.info(
                "skills_loaded",
                count=self._skill_registry.count,
                skills=[s.name for s in self._skill_registry.list_skills()],
            )
        return self._skill_registry

    @property
    def tool_executor(self) -> ToolExecutor:
        """Lazy-init tool executor with full security pipeline."""
        if self._tool_executor is None:
            autonomy = self.config.autonomy.default_level
            self._tool_executor = ToolExecutor(
                registry=self.skill_registry,
                policy_engine=PolicyEngine(autonomy_level=autonomy),
                audit_logger=AuditLogger(),
                canary_system=CanarySystem(),
                egress_filter=EgressFilter(),
            )
            logger.info("tool_executor_initialized", autonomy_level=autonomy)
        return self._tool_executor

    # ── Main message processing (agentic loop) ────────────────

    async def process_message(
        self,
        message: str,
        conversation_id: str | None = None,
        channel: str = "cli",
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a user message through the full agentic loop.

        The LLM may request tool calls, which are executed through the
        security pipeline, and results fed back to the LLM until it
        produces a final text response.

        Returns:
            {
                "response": str,
                "conversation_id": str,
                "tokens_used": int,
                "cost_usd": float,
                "tools_used": list[str],
            }
        """
        store = MemoryStore()
        store.open()

        tools_used: list[str] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0.0

        try:
            # Create or continue conversation
            if not conversation_id:
                conversation_id = store.create_conversation(
                    channel=channel,
                    user_id=user_id,
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
                    "tools_used": [],
                }

            # Build context messages (system prompt + conversation history + RAG)
            messages = self.context_builder.build_messages(
                user_message=message,
                conversation_id=conversation_id,
                channel=channel,
            )

            # Get tool definitions for function calling
            tool_definitions = self.skill_registry.get_tool_definitions()

            # ── AGENTIC LOOP ──────────────────────────────────
            response_text = ""

            for round_num in range(MAX_TOOL_ROUNDS):
                logger.info(
                    "agentic_round",
                    round=round_num + 1,
                    max_rounds=MAX_TOOL_ROUNDS,
                    tools_used_so_far=tools_used,
                )

                # On the last round, don't offer tools (force text response)
                tools_param = tool_definitions if round_num < MAX_TOOL_ROUNDS - 1 else None

                # Call LLM
                result = await self.router.chat(
                    messages=messages,
                    tools=tools_param,
                )

                # Track usage
                total_input_tokens += result.get("input_tokens", 0)
                total_output_tokens += result.get("output_tokens", 0)
                total_cost += result.get("cost_usd", 0.0)

                tool_calls = result.get("tool_calls")
                content = result.get("content", "")

                # If no tool calls, we have our final text response
                if not tool_calls:
                    response_text = content or "(No response)"
                    break

                # ── Execute tool calls ────────────────────────
                # Add assistant message with tool calls to conversation
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": content or None,
                    "tool_calls": tool_calls,
                }
                messages.append(assistant_msg)

                for tool_call in tool_calls:
                    func = tool_call["function"]
                    tool_name = func["name"]
                    tool_call_id = tool_call["id"]

                    # Parse arguments
                    try:
                        arguments = (
                            json.loads(func["arguments"])
                            if isinstance(func["arguments"], str)
                            else func["arguments"]
                        )
                    except (json.JSONDecodeError, TypeError):
                        arguments = {}

                    logger.info(
                        "executing_tool",
                        tool=tool_name,
                        args=list(arguments.keys()),
                        round=round_num + 1,
                    )

                    # Execute through full security pipeline
                    exec_result = await self.tool_executor.execute_tool_call(
                        tool_name=tool_name,
                        arguments=arguments,
                        channel=channel,
                        user_id=user_id,
                    )

                    tools_used.append(tool_name)

                    # Build tool result message
                    if exec_result["success"]:
                        tool_output = exec_result["output"] or "(Success, no output)"
                    else:
                        decision = exec_result.get("decision", "error")
                        error = exec_result.get("error", "Unknown error")
                        if decision == "deny":
                            tool_output = f"[DENIED] {error}"
                        elif decision == "ask_user":
                            tool_output = f"[REQUIRES APPROVAL] {error}"
                        else:
                            tool_output = f"[ERROR] {error}"

                    # Inject tool result back into conversation
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": tool_output,
                        }
                    )

                    logger.info(
                        "tool_result",
                        tool=tool_name,
                        success=exec_result["success"],
                        output_len=len(tool_output),
                    )
            else:
                # MAX_TOOL_ROUNDS exhausted without a text response
                response_text = (
                    "I've used multiple tools to work on your request. "
                    "Here's what I did:\n"
                    + "\n".join(f"- Used {t}" for t in tools_used)
                    + "\n\nPlease let me know if you need anything else."
                )

            # ── Store results ─────────────────────────────────

            # Store assistant response
            store.add_message(
                conversation_id,
                role="assistant",
                content=response_text,
                token_count=total_output_tokens,
            )

            # Record cost
            store.record_cost(
                provider=result.get("provider", self.config.llm.provider),
                model=result.get("model", self.config.llm.model),
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                cost_usd=total_cost,
                channel=channel,
                conversation_id=conversation_id,
            )

            logger.info(
                "message_processed",
                conversation_id=conversation_id[:12],
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                cost_usd=round(total_cost, 6),
                tools_used=tools_used,
                rounds=round_num + 1,
            )

            return {
                "response": response_text,
                "conversation_id": conversation_id,
                "tokens_used": total_input_tokens + total_output_tokens,
                "cost_usd": total_cost,
                "tools_used": tools_used,
            }

        except Exception as e:
            logger.error("brain_error", error=str(e))
            return {
                "response": f"Error: {str(e)}",
                "conversation_id": conversation_id or "",
                "tokens_used": 0,
                "cost_usd": 0.0,
                "tools_used": tools_used,
            }
        finally:
            store.close()

    # ── Streaming with tool use ───────────────────────────────

    async def stream_message(
        self,
        message: str,
        conversation_id: str | None = None,
        channel: str = "cli",
        user_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream a response from the agent with tool-use support.

        Yields:
            {"type": "chunk", "content": "partial text..."}
            {"type": "tool_use", "tool": "web_search", "status": "executing"}
            {"type": "tool_result", "tool": "web_search", "success": true}
            {"type": "complete", "content": "full text", "conversation_id": ..., ...}
        """
        store = MemoryStore()
        store.open()

        tools_used: list[str] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0.0

        try:
            if not conversation_id:
                conversation_id = store.create_conversation(
                    channel=channel,
                    user_id=user_id,
                )

            store.add_message(conversation_id, role="user", content=message)

            if not self.router.check_budget():
                yield {
                    "type": "complete",
                    "content": "Daily token budget exceeded.",
                    "conversation_id": conversation_id,
                    "tokens_used": 0,
                    "cost_usd": 0.0,
                    "tools_used": [],
                }
                return

            messages = self.context_builder.build_messages(
                user_message=message,
                conversation_id=conversation_id,
                channel=channel,
            )

            tool_definitions = self.skill_registry.get_tool_definitions()
            response_text = ""

            for round_num in range(MAX_TOOL_ROUNDS):
                tools_param = tool_definitions if round_num < MAX_TOOL_ROUNDS - 1 else None

                # For the first round (or after tools), try streaming
                if round_num == 0 and not tools_param:
                    # No tools available, pure streaming
                    async for chunk in self.router.stream(messages=messages):
                        if chunk["type"] == "chunk":
                            yield chunk
                        elif chunk["type"] == "complete":
                            response_text = chunk["content"]
                            total_input_tokens += chunk.get("input_tokens", 0)
                            total_output_tokens += chunk.get("output_tokens", 0)
                            total_cost += chunk.get("cost_usd", 0.0)
                    break

                # Non-streaming call (tool rounds)
                result = await self.router.chat(
                    messages=messages,
                    tools=tools_param,
                )

                total_input_tokens += result.get("input_tokens", 0)
                total_output_tokens += result.get("output_tokens", 0)
                total_cost += result.get("cost_usd", 0.0)

                tool_calls = result.get("tool_calls")
                content = result.get("content", "")

                if not tool_calls:
                    response_text = content or "(No response)"
                    # Stream the final text response
                    yield {"type": "chunk", "content": response_text}
                    break

                # Execute tools
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": content or None,
                    "tool_calls": tool_calls,
                }
                messages.append(assistant_msg)

                for tool_call in tool_calls:
                    func = tool_call["function"]
                    tool_name = func["name"]
                    tool_call_id = tool_call["id"]

                    try:
                        arguments = (
                            json.loads(func["arguments"])
                            if isinstance(func["arguments"], str)
                            else func["arguments"]
                        )
                    except (json.JSONDecodeError, TypeError):
                        arguments = {}

                    # Notify client that we're using a tool
                    yield {
                        "type": "tool_use",
                        "tool": tool_name,
                        "status": "executing",
                        "arguments": arguments,
                    }

                    exec_result = await self.tool_executor.execute_tool_call(
                        tool_name=tool_name,
                        arguments=arguments,
                        channel=channel,
                        user_id=user_id,
                    )
                    tools_used.append(tool_name)

                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "success": exec_result["success"],
                    }

                    if exec_result["success"]:
                        tool_output = exec_result["output"] or "(Success, no output)"
                    else:
                        tool_output = f"[ERROR] {exec_result.get('error', 'Unknown error')}"

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": tool_output,
                        }
                    )

            # Store and finalize
            if response_text:
                store.add_message(
                    conversation_id,
                    role="assistant",
                    content=response_text,
                    token_count=total_output_tokens,
                )

                store.record_cost(
                    provider=self.config.llm.provider,
                    model=self.config.llm.model,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    cost_usd=total_cost,
                    channel=channel,
                    conversation_id=conversation_id,
                )

            yield {
                "type": "complete",
                "content": response_text,
                "conversation_id": conversation_id,
                "tokens_used": total_input_tokens + total_output_tokens,
                "cost_usd": total_cost,
                "tools_used": tools_used,
            }

        except Exception as e:
            logger.error("stream_error", error=str(e))
            yield {"type": "error", "content": str(e)}
        finally:
            store.close()

    # ── Provider auto-detection ───────────────────────────────

    def _auto_detect_provider(self, api_key: str) -> None:
        """Auto-detect and override provider/model based on available API keys.

        If the configured provider's API key isn't available but another
        provider's key IS available, switch to the available one.
        This makes Gulama truly model-agnostic — just set an API key and go.
        """
        import os

        # Map of env var -> (provider, default_model)
        provider_map = {
            "DEEPSEEK_API_KEY": ("deepseek", "deepseek-chat"),
            "GROQ_API_KEY": ("groq", "llama-3.3-70b-versatile"),
            "OPENAI_API_KEY": ("openai", "gpt-4o-mini"),
            "ANTHROPIC_API_KEY": ("anthropic", "claude-sonnet-4-5-20250929"),
            "XAI_API_KEY": ("xai", "grok-2"),
            "MISTRAL_API_KEY": ("mistral", "mistral-large-latest"),
            "MOONSHOT_API_KEY": ("moonshot", "moonshot-v1-8k"),
            "COHERE_API_KEY": ("cohere", "command-r-plus"),
            "GOOGLE_API_KEY": ("google", "gemini-2.0-flash"),
        }

        # Check if the currently configured provider has a valid key
        current_provider = self.config.llm.provider
        current_has_key = False
        for env_var, (provider, _) in provider_map.items():
            if provider == current_provider and os.getenv(env_var):
                current_has_key = True
                break

        # Also check LLM_API_KEY as a generic key for the current provider
        if os.getenv("LLM_API_KEY"):
            current_has_key = True

        if current_has_key:
            return  # Current config is fine

        # Current provider has no key — auto-detect from available keys
        for env_var, (provider, model) in provider_map.items():
            if os.getenv(env_var):
                logger.info(
                    "provider_auto_detected",
                    configured=current_provider,
                    detected=provider,
                    model=model,
                    reason=f"No key for {current_provider}, found {env_var}",
                )
                self.config.llm.provider = provider
                self.config.llm.model = model
                return

        logger.warning(
            "no_provider_detected",
            msg="No API key found for any provider.",
        )

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
            or os.getenv("XAI_API_KEY")
            or os.getenv("MISTRAL_API_KEY")
            or os.getenv("MOONSHOT_API_KEY")
            or os.getenv("COHERE_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
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
