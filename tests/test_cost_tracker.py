"""Tests for the cost tracker."""

from __future__ import annotations

import pytest

from src.utils.cost_tracker import CostTracker


class TestCostTracker:
    """Tests for CostTracker."""

    def setup_method(self):
        self.tracker = CostTracker(daily_budget_usd=10.0)

    @pytest.mark.asyncio
    async def test_record_usage(self):
        """Recording token usage should work."""
        entry = await self.tracker.record(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            input_tokens=1000,
            output_tokens=500,
        )
        assert entry.input_tokens == 1000
        assert entry.output_tokens == 500
        assert entry.provider == "anthropic"

    def test_cost_estimation(self):
        """Cost estimation should return a non-negative value."""
        cost = self.tracker.estimate_cost(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost >= 0.0

    @pytest.mark.asyncio
    async def test_session_stats_accumulate(self):
        """Multiple records should accumulate session totals."""
        for _ in range(5):
            await self.tracker.record(
                provider="openai",
                model="gpt-4o",
                input_tokens=100,
                output_tokens=50,
            )
        session = self.tracker.get_session_stats()
        assert session["session_tokens"] == 750  # 5 * (100 + 50)
        assert session["session_cost_usd"] >= 0

    def test_today_stats_without_store(self):
        """Without memory store, today stats should return defaults."""
        stats = self.tracker.get_today_stats()
        assert "today_cost_usd" in stats
        assert stats["budget_usd"] == 10.0
        assert stats["remaining_usd"] == 10.0

    def test_dashboard_data(self):
        """Dashboard data should include required fields."""
        dashboard = self.tracker.get_dashboard_data()
        assert "today" in dashboard
        assert "session" in dashboard
        assert dashboard["today"]["budget_usd"] == 10.0

    @pytest.mark.asyncio
    async def test_budget_tracking(self):
        """Session cost should track properly."""
        await self.tracker.record(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            input_tokens=10000,
            output_tokens=5000,
        )
        session = self.tracker.get_session_stats()
        assert session["session_cost_usd"] > 0
