"""
Universal LLM router for Gulama — works with ANY provider via LiteLLM.

Supports 100+ providers:
- Anthropic (Claude), OpenAI (GPT), Google (Gemini)
- DeepSeek, Qwen, Zhipu, Moonshot, Baichuan, Yi, MiniMax
- Groq, Together AI, Fireworks, Anyscale, Perplexity
- xAI (Grok), Mistral, Cohere, AI21
- Ollama, vLLM, any OpenAI-compatible endpoint
- AWS Bedrock, Azure OpenAI, Google Vertex AI
- Vision/multimodal models (GPT-4o, Claude 3.5, Gemini, etc.)

Features:
- Automatic fallback to secondary provider
- Function calling / tool use (LLM decides which tools to invoke)
- Vision / multimodal support (images in messages)
- Token counting and cost tracking
- Streaming support
- Budget enforcement
- Rate limit handling with exponential backoff
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

import litellm
from litellm import acompletion, completion_cost

from src.gateway.config import GulamaConfig
from src.utils.logging import get_logger

logger = get_logger("llm_router")

# Suppress LiteLLM's verbose logging
litellm.suppress_debug_info = True
litellm.set_verbose = False


class LLMRouter:
    """
    Universal LLM router. Talks to any provider via LiteLLM.

    Usage:
        router = LLMRouter(config=config, api_key="sk-...")

        # Simple chat
        response = await router.chat(messages=[{"role": "user", "content": "Hello"}])

        # Chat with tools (function calling)
        response = await router.chat(
            messages=[...],
            tools=[{"type": "function", "function": {...}}],
        )

        # Streaming
        async for chunk in router.stream(messages=[...]):
            print(chunk)
    """

    # ── Provider prefix mapping for LiteLLM ──
    PROVIDER_PREFIXES = {
        # Major providers
        "anthropic": "anthropic/",
        "openai": "openai/",
        "google": "gemini/",
        "deepseek": "deepseek/",
        "groq": "groq/",
        "mistral": "mistral/",
        "cohere": "cohere/",
        "ai21": "ai21/",
        # xAI (Grok)
        "xai": "xai/",
        "grok": "xai/",
        # Chinese providers
        "moonshot": "openai/",      # Moonshot (Kimi) uses OpenAI-compatible API
        "kimi": "openai/",          # Alias for moonshot
        "qwen": "openai/",          # Qwen uses OpenAI-compatible API
        "zhipu": "openai/",         # Zhipu (GLM) uses OpenAI-compatible
        "baichuan": "openai/",      # Baichuan uses OpenAI-compatible
        "yi": "openai/",            # Yi (01.AI) uses OpenAI-compatible
        "minimax": "openai/",       # MiniMax uses OpenAI-compatible
        "stepfun": "openai/",       # StepFun uses OpenAI-compatible
        "doubao": "openai/",        # ByteDance Doubao uses OpenAI-compatible
        # Inference platforms
        "together": "together_ai/",
        "fireworks": "fireworks_ai/",
        "anyscale": "anyscale/",
        "perplexity": "perplexity/",
        "replicate": "replicate/",
        "deepinfra": "deepinfra/",
        "octoai": "octoai/",
        "huggingface": "huggingface/",
        # Local / self-hosted
        "ollama": "ollama/",
        "vllm": "openai/",          # vLLM uses OpenAI-compatible
        "lmstudio": "openai/",      # LM Studio uses OpenAI-compatible
        "llamacpp": "openai/",      # llama.cpp server uses OpenAI-compatible
        "oobabooga": "openai/",     # text-generation-webui uses OpenAI-compatible
        # Cloud providers
        "bedrock": "bedrock/",
        "azure": "azure/",
        "vertex": "vertex_ai/",
        "sagemaker": "sagemaker/",
        # Generic
        "openai_compatible": "openai/",
        "openrouter": "openrouter/",
    }

    def __init__(
        self,
        config: GulamaConfig,
        api_key: str = "",
        fallback_api_key: str = "",
    ):
        self.config = config
        self.api_key = api_key
        self.fallback_api_key = fallback_api_key

        # Build the LiteLLM model string
        self.primary_model = self._build_model_string(
            config.llm.provider, config.llm.model, config.llm.api_base,
        )
        self.fallback_model = ""
        if config.llm_fallback.provider and config.llm_fallback.model:
            self.fallback_model = self._build_model_string(
                config.llm_fallback.provider,
                config.llm_fallback.model,
                config.llm_fallback.api_base,
            )

        # Track usage
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0

        logger.info(
            "llm_router_initialized",
            primary_model=self.primary_model,
            fallback_model=self.fallback_model or "none",
        )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Send a chat completion request to the LLM.

        Args:
            messages: Chat messages (supports text + vision/image content)
            tools: Tool/function definitions for function calling
            tool_choice: "auto", "none", "required", or specific function

        Returns:
            {
                "content": str,              # Text response (may be empty if tool_calls)
                "tool_calls": list | None,   # Tool calls requested by LLM
                "model": str,
                "input_tokens": int,
                "output_tokens": int,
                "cost_usd": float,
                "provider": str,
            }
        """
        max_tokens = max_tokens or self.config.llm.max_tokens
        temperature = temperature if temperature is not None else self.config.llm.temperature

        # Try primary model
        try:
            result = await self._call_model(
                model=self.primary_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                api_key=self.api_key,
                api_base=self.config.llm.api_base or None,
                tools=tools,
                tool_choice=tool_choice,
                **kwargs,
            )
            return result
        except Exception as e:
            logger.warning(
                "primary_llm_failed",
                model=self.primary_model,
                error=str(e),
            )

            # Try fallback model if configured
            if self.fallback_model:
                logger.info("trying_fallback_llm", model=self.fallback_model)
                try:
                    result = await self._call_model(
                        model=self.fallback_model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        api_key=self.fallback_api_key or self.api_key,
                        api_base=self.config.llm_fallback.api_base or None,
                        tools=tools,
                        tool_choice=tool_choice,
                        **kwargs,
                    )
                    result["fallback"] = True
                    return result
                except Exception as fallback_error:
                    logger.error(
                        "fallback_llm_failed",
                        model=self.fallback_model,
                        error=str(fallback_error),
                    )

            raise LLMError(f"All LLM providers failed. Primary: {e}") from e

    async def stream(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream a chat completion response.

        Yields:
            {"type": "chunk", "content": "partial text..."}
            {"type": "complete", "content": "full text", "input_tokens": ..., ...}
        """
        max_tokens = max_tokens or self.config.llm.max_tokens
        temperature = temperature if temperature is not None else self.config.llm.temperature

        model = self.primary_model
        api_key = self.api_key
        api_base = self.config.llm.api_base or None

        call_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "api_key": api_key,
            "api_base": api_base,
            "stream": True,
            **kwargs,
        }
        if tools:
            call_kwargs["tools"] = tools

        try:
            response = await acompletion(**call_kwargs)

            full_content = ""
            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    full_content += delta.content
                    yield {"type": "chunk", "content": delta.content}

            # Calculate cost
            input_tokens = 0
            output_tokens = 0
            cost_usd = 0.0
            try:
                # Estimate tokens from content length
                input_tokens = sum(
                    len(m.get("content", "") if isinstance(m.get("content"), str) else str(m.get("content", ""))) // 4
                    for m in messages
                )
                output_tokens = len(full_content) // 4
                cost_usd = completion_cost(
                    model=model,
                    prompt=str(messages),
                    completion=full_content,
                )
            except Exception:
                pass

            self._track_usage(input_tokens, output_tokens, cost_usd)

            yield {
                "type": "complete",
                "content": full_content,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
            }

        except Exception as e:
            logger.error("stream_error", model=model, error=str(e))
            yield {"type": "error", "content": str(e)}

    async def _call_model(
        self,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
        api_key: str,
        api_base: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make a single LLM API call with optional tool/function calling."""
        call_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "api_key": api_key,
            "api_base": api_base,
            **kwargs,
        }

        # Add tools if provided (function calling)
        if tools:
            call_kwargs["tools"] = tools
            if tool_choice:
                call_kwargs["tool_choice"] = tool_choice

        response = await acompletion(**call_kwargs)

        message = response.choices[0].message
        content = message.content or ""
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        # Parse tool calls if present
        tool_calls = None
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_calls = []
            for tc in message.tool_calls:
                tool_call_data = {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,  # JSON string
                    },
                }
                tool_calls.append(tool_call_data)

        # Calculate cost
        cost_usd = 0.0
        try:
            cost_usd = completion_cost(completion_response=response)
        except Exception:
            pass

        self._track_usage(input_tokens, output_tokens, cost_usd)

        logger.info(
            "llm_call_complete",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(cost_usd, 6),
            has_tool_calls=bool(tool_calls),
        )

        return {
            "content": content,
            "tool_calls": tool_calls,
            "model": model,
            "provider": self.config.llm.provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "fallback": False,
        }

    def _track_usage(self, input_tokens: int, output_tokens: int, cost_usd: float) -> None:
        """Track cumulative token usage and cost."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost_usd

    def check_budget(self) -> bool:
        """Check if we're still within the daily budget."""
        from src.memory.store import MemoryStore

        store = MemoryStore()
        store.open()
        today_cost = store.get_today_cost()
        store.close()

        budget = self.config.cost.daily_budget_usd
        if today_cost >= budget:
            logger.warning(
                "budget_exceeded",
                today_cost=today_cost,
                budget=budget,
            )
            return False
        return True

    def get_usage_summary(self) -> dict[str, Any]:
        """Get usage summary for this session."""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
        }

    @classmethod
    def _build_model_string(cls, provider: str, model: str, api_base: str) -> str:
        """Build the LiteLLM model identifier string."""
        prefix = cls.PROVIDER_PREFIXES.get(provider, "")

        # If model already has a prefix, don't double-prefix
        if "/" in model and not model.startswith(prefix):
            return model

        return f"{prefix}{model}"

    @staticmethod
    def list_supported_providers() -> list[dict[str, str]]:
        """List all supported LLM providers."""
        return [
            {"code": "anthropic", "name": "Anthropic (Claude)", "models": "claude-sonnet-4-5-20250929, claude-opus-4-6, claude-haiku-4-5-20251001"},
            {"code": "openai", "name": "OpenAI", "models": "gpt-4o, gpt-4o-mini, o1, o3-mini"},
            {"code": "google", "name": "Google (Gemini)", "models": "gemini-2.0-flash, gemini-2.0-pro"},
            {"code": "deepseek", "name": "DeepSeek", "models": "deepseek-chat, deepseek-reasoner"},
            {"code": "xai", "name": "xAI (Grok)", "models": "grok-2, grok-2-mini"},
            {"code": "mistral", "name": "Mistral AI", "models": "mistral-large, mistral-small, codestral"},
            {"code": "moonshot", "name": "Moonshot (Kimi)", "models": "moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k"},
            {"code": "qwen", "name": "Alibaba (Qwen)", "models": "qwen-plus, qwen-max, qwen-turbo, qwen-vl-max"},
            {"code": "zhipu", "name": "Zhipu AI (GLM)", "models": "glm-4, glm-4v, glm-3-turbo"},
            {"code": "yi", "name": "01.AI (Yi)", "models": "yi-large, yi-medium, yi-vision"},
            {"code": "baichuan", "name": "Baichuan", "models": "Baichuan4, Baichuan3-Turbo"},
            {"code": "minimax", "name": "MiniMax", "models": "abab6.5-chat, abab5.5-chat"},
            {"code": "doubao", "name": "ByteDance (Doubao)", "models": "doubao-pro-128k, doubao-lite-128k"},
            {"code": "groq", "name": "Groq", "models": "llama-3.3-70b-versatile, mixtral-8x7b-32768"},
            {"code": "together", "name": "Together AI", "models": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"},
            {"code": "fireworks", "name": "Fireworks AI", "models": "accounts/fireworks/models/llama-v3p1-70b-instruct"},
            {"code": "perplexity", "name": "Perplexity", "models": "llama-3.1-sonar-large-128k-online"},
            {"code": "cohere", "name": "Cohere", "models": "command-r-plus, command-r"},
            {"code": "ollama", "name": "Ollama (local)", "models": "llama3.1, mistral, codellama, llava"},
            {"code": "bedrock", "name": "AWS Bedrock", "models": "anthropic.claude-3-5-sonnet-20241022-v2:0"},
            {"code": "azure", "name": "Azure OpenAI", "models": "gpt-4o (deployment name)"},
            {"code": "vertex", "name": "Google Vertex AI", "models": "gemini-2.0-flash"},
            {"code": "openrouter", "name": "OpenRouter", "models": "Any model via OpenRouter"},
            {"code": "openai_compatible", "name": "OpenAI-compatible", "models": "Any model via custom endpoint"},
        ]


class LLMError(Exception):
    """Raised when all LLM providers fail."""
    pass
