"""
Cost tracker for Gulama — tracks token usage and spending across all LLM providers.

Provides real-time cost monitoring, daily/weekly/monthly budgets,
and alerts when spending approaches limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.memory.store import MemoryStore
from src.utils.logging import get_logger

logger = get_logger("cost_tracker")

# Approximate per-token pricing (USD) — updated regularly
# These are fallback estimates; actual cost comes from LiteLLM when available
TOKEN_PRICING: dict[str, dict[str, float]] = {
    "anthropic/claude-sonnet-4-5-20250929": {"input": 0.000003, "output": 0.000015},
    "anthropic/claude-opus-4-6": {"input": 0.000015, "output": 0.000075},
    "anthropic/claude-haiku-4-5-20251001": {"input": 0.0000008, "output": 0.000004},
    "openai/gpt-4o": {"input": 0.0000025, "output": 0.00001},
    "openai/gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},
    "openai/o1": {"input": 0.000015, "output": 0.00006},
    "deepseek/deepseek-chat": {"input": 0.00000014, "output": 0.00000028},
    "google/gemini-2.0-flash": {"input": 0.00000015, "output": 0.0000006},
    "groq/llama-3.3-70b-versatile": {"input": 0.00000059, "output": 0.00000079},
    "ollama/*": {"input": 0.0, "output": 0.0},
}


@dataclass
class CostEntry:
    """A single cost tracking entry."""

    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    channel: str | None = None
    skill: str | None = None
    conversation_id: str | None = None
    timestamp: str | None = None


class CostTracker:
    """
    Tracks LLM token usage and costs.

    Features:
    - Per-call cost recording
    - Daily/weekly/monthly budget enforcement
    - Cost estimation for any provider/model
    - Dashboard data generation
    """

    def __init__(
        self,
        memory_store: MemoryStore | None = None,
        daily_budget_usd: float = 10.0,
    ):
        self.memory_store = memory_store
        self.daily_budget_usd = daily_budget_usd
        self._session_cost: float = 0.0
        self._session_tokens: int = 0

    async def record(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float | None = None,
        channel: str | None = None,
        skill: str | None = None,
        conversation_id: str | None = None,
    ) -> CostEntry:
        """Record a cost entry for an LLM call."""
        # Calculate cost if not provided
        if cost_usd is None:
            cost_usd = self.estimate_cost(provider, model, input_tokens, output_tokens)

        entry = CostEntry(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            channel=channel,
            skill=skill,
            conversation_id=conversation_id,
            timestamp=datetime.now(UTC).isoformat(),
        )

        # Update session totals
        self._session_cost += cost_usd
        self._session_tokens += input_tokens + output_tokens

        # Persist to memory store
        if self.memory_store:
            try:
                self.memory_store.record_cost(
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost_usd,
                    channel=channel,
                    skill=skill,
                    conversation_id=conversation_id,
                )
            except Exception as e:
                logger.warning("cost_persist_failed", error=str(e))

        # Check budget
        if self.memory_store:
            today_cost = self.memory_store.get_today_cost()
            if today_cost >= self.daily_budget_usd:
                logger.warning(
                    "daily_budget_exceeded",
                    today_cost=today_cost,
                    budget=self.daily_budget_usd,
                )

        logger.debug(
            "cost_recorded",
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(cost_usd, 6),
        )

        return entry

    @staticmethod
    def estimate_cost(
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate the cost for a given number of tokens."""
        key = f"{provider}/{model}"

        # Exact match
        if key in TOKEN_PRICING:
            pricing = TOKEN_PRICING[key]
            return (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])

        # Wildcard match (e.g., ollama/*)
        for pattern, pricing in TOKEN_PRICING.items():
            if pattern.endswith("/*") and key.startswith(pattern[:-1]):
                return (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])

        # Default: assume $0.002 per 1K tokens
        return ((input_tokens + output_tokens) / 1000) * 0.002

    def get_session_stats(self) -> dict[str, Any]:
        """Get cost stats for the current session."""
        return {
            "session_cost_usd": round(self._session_cost, 6),
            "session_tokens": self._session_tokens,
        }

    def get_today_stats(self) -> dict[str, Any]:
        """Get today's cost summary."""
        if not self.memory_store:
            return {
                "today_cost_usd": 0.0,
                "budget_usd": self.daily_budget_usd,
                "remaining_usd": self.daily_budget_usd,
            }

        today_cost = self.memory_store.get_today_cost()
        return {
            "today_cost_usd": round(today_cost, 6),
            "budget_usd": self.daily_budget_usd,
            "remaining_usd": round(max(0, self.daily_budget_usd - today_cost), 6),
            "budget_used_pct": round((today_cost / self.daily_budget_usd) * 100, 1)
            if self.daily_budget_usd > 0
            else 0,
        }

    def get_history(self, days: int = 7) -> list[dict[str, Any]]:
        """Get cost history for the last N days."""
        if not self.memory_store:
            return []
        return self.memory_store.get_cost_summary(days)

    def is_budget_exceeded(self) -> bool:
        """Check if the daily budget has been exceeded."""
        if not self.memory_store:
            return False
        return self.memory_store.get_today_cost() >= self.daily_budget_usd

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get comprehensive dashboard data."""
        today = self.get_today_stats()
        session = self.get_session_stats()
        history = self.get_history(days=30)

        # Calculate weekly and monthly totals
        weekly_cost = sum(day.get("total_cost", 0) for day in self.get_history(days=7))
        monthly_cost = sum(day.get("total_cost", 0) for day in history)

        return {
            "today": today,
            "session": session,
            "weekly_cost_usd": round(weekly_cost, 4),
            "monthly_cost_usd": round(monthly_cost, 4),
            "daily_history": history,
        }
