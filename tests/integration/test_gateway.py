"""
Integration tests for the FastAPI gateway endpoints.

Uses the FastAPI TestClient for synchronous testing
of all REST API endpoints.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """Create a test FastAPI app with auth bypassed."""
    os.environ["GULAMA_TEST_MODE"] = "1"

    with patch("src.gateway.app.load_config") as mock_config:
        config = MagicMock()
        config.gateway.host = "127.0.0.1"
        config.gateway.port = 18789
        config.gateway.websocket_origins = ["http://localhost:3000"]
        config.logging.level = "WARNING"
        config.logging.format = "text"
        config.llm.provider = "test"
        config.llm.model = "test-model"
        config.autonomy.default_level = 2
        config.security.sandbox_enabled = True
        config.security.policy_engine_enabled = True
        config.security.canary_tokens_enabled = True
        config.security.egress_filtering_enabled = True
        config.security.audit_logging_enabled = True
        config.auth.session_timeout_seconds = 3600
        config.cost.daily_budget_usd = 10.0

        mock_config.return_value = config

        from src.gateway.app import create_app

        application = create_app()
        application.state.config = config

        # Make auth manager accept a test token
        application.state.auth_manager.verify_session = MagicMock(return_value=True)

        yield application


@pytest.fixture
def client(app):
    """Create a test client with auth token."""
    c = TestClient(app, raise_server_exceptions=False)
    c.headers["Authorization"] = "Bearer test-token-123"
    return c


# ── Health Endpoints ──────────────────────────────────


class TestHealthEndpoints:
    """Test health check endpoints (no auth required)."""

    def test_health_check(self, client):
        """Basic health check should return 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_detailed_health(self, client):
        """Detailed health should include component status."""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "components" in data
        assert "security" in data["components"]


# ── Skills Endpoint ───────────────────────────────────


class TestSkillsEndpoint:
    """Test the skills listing endpoint."""

    def test_list_skills(self, client):
        """Should list all registered skills."""
        response = client.get("/api/v1/skills")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "skills" in data
        assert data["count"] >= 4  # At least core skills

        for skill in data["skills"]:
            assert "name" in skill
            assert "description" in skill
            assert "version" in skill


# ── Status Endpoint ───────────────────────────────────


class TestStatusEndpoint:
    """Test the status endpoint."""

    def test_get_status(self, client):
        """Should return agent status."""
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert "llm" in data
        assert "autonomy_level" in data
        assert "security" in data


# ── Cost Endpoints ────────────────────────────────────


class TestCostEndpoints:
    """Test cost tracking endpoints."""

    def test_today_cost(self, client):
        """Should return today's cost data."""
        response = client.get("/api/v1/cost/today")
        assert response.status_code == 200
        data = response.json()
        assert "today_cost_usd" in data
        assert "daily_budget_usd" in data
        assert "budget_remaining_usd" in data

    def test_cost_history(self, client):
        """Should return cost history."""
        response = client.get("/api/v1/cost/history?days=3")
        assert response.status_code == 200
        data = response.json()
        assert "days" in data
        assert data["days"] == 3


# ── Conversation Endpoints ────────────────────────────


class TestConversationEndpoints:
    """Test conversation management endpoints."""

    def test_list_conversations(self, client):
        """Should list conversations."""
        response = client.get("/api/v1/conversations")
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data

    def test_get_nonexistent_conversation(self, client):
        """Should handle missing conversations gracefully."""
        response = client.get("/api/v1/conversations/nonexistent-id")
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data


# ── Scheduler Endpoints ───────────────────────────────


class TestSchedulerEndpoints:
    """Test scheduler endpoints."""

    def test_list_tasks_no_scheduler(self, client):
        """Should handle missing scheduler gracefully."""
        response = client.get("/api/v1/scheduler/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data


# ── Sub-Agent Endpoints ───────────────────────────────


class TestSubAgentEndpoints:
    """Test sub-agent management endpoints."""

    def test_list_agents_no_manager(self, client):
        """Should handle missing agent manager gracefully."""
        response = client.get("/api/v1/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert data["active_count"] == 0


# ── Audit Endpoint ────────────────────────────────────


class TestAuditEndpoint:
    """Test audit log endpoint."""

    def test_get_audit_log(self, client):
        """Should return audit entries."""
        response = client.get("/api/v1/audit")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "count" in data


# ── Marketplace Endpoints ─────────────────────────────


class TestMarketplaceEndpoints:
    """Test GulamaHub marketplace endpoints."""

    def test_hub_search(self, client):
        """Should search marketplace."""
        response = client.get("/api/v1/hub/search?query=weather")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "count" in data

    def test_hub_installed(self, client):
        """Should list installed skills."""
        response = client.get("/api/v1/hub/installed")
        assert response.status_code == 200
        data = response.json()
        assert "installed" in data


# ── Debug Endpoint ────────────────────────────────────


class TestDebugEndpoint:
    """Test debug event endpoint."""

    def test_get_debug_events(self, client):
        """Should return debug events."""
        response = client.get("/api/v1/debug/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "subscribers" in data


# ── Auth Endpoints ────────────────────────────────────


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_invalid_totp(self, client):
        """Invalid TOTP should return 401."""
        response = client.post("/api/v1/auth/totp", json={"code": "000000"})
        assert response.status_code == 401

    def test_logout(self, client):
        """Logout should return success."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "logged_out"
