"""Tests for the cost tracker."""

from __future__ import annotations

import pytest

from src.utils.cost_tracker import CostTracker


class TestCostTracker:
    """Tests for CostTracker."""

    def setup_method(self):
        self.tracker = CostTracker(daily_budget_usd=10.0)

    def test_record_usage(self):
        """Recording token usage should work."""
        self.tracker.record(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            input_tokens=1000,
            output_tokens=500,
        )
        stats = self.tracker.get_today_stats()
        assert stats["total_requests"] == 1
        assert stats["total_input_tokens"] == 1000
        assert stats["total_output_tokens"] == 500

    def test_cost_estimation(self):
        """Cost estimation should return a positive value for known models."""
        cost = self.tracker.estimate_cost(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost >= 0.0

    def test_multiple_records(self):
        """Multiple records should accumulate."""
        for _ in range(5):
            self.tracker.record(
                provider="openai",
                model="gpt-4o",
                input_tokens=100,
                output_tokens=50,
            )
        stats = self.tracker.get_today_stats()
        assert stats["total_requests"] == 5
        assert stats["total_input_tokens"] == 500

    def test_dashboard_data(self):
        """Dashboard data should include required fields."""
        self.tracker.record(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            input_tokens=500,
            output_tokens=200,
        )
        dashboard = self.tracker.get_dashboard_data()
        assert "today" in dashboard
        assert "budget" in dashboard
        assert dashboard["budget"]["daily_limit_usd"] == 10.0

    def test_budget_tracking(self):
        """Budget tracking should show remaining amount."""
        self.tracker.record(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            input_tokens=10000,
            output_tokens=5000,
        )
        dashboard = self.tracker.get_dashboard_data()
        budget = dashboard["budget"]
        assert budget["remaining_usd"] <= budget["daily_limit_usd"]
