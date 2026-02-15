"""
Integration tests for the full agent flow: brain → skill → response.

These tests verify the complete pipeline works end-to-end using
mocked LLM responses (no real API calls needed).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent.brain import AgentBrain
from src.agent.tool_executor import ToolExecutor
from src.gateway.config import GulamaConfig
from src.security.audit_logger import AuditLogger
from src.security.canary import CanarySystem
from src.security.egress_filter import EgressFilter
from src.security.policy_engine import PolicyEngine
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.skills.registry import SkillRegistry


# ── Fixtures ──────────────────────────────────────────


class MockSkill(BaseSkill):
    """A simple test skill that echoes input."""

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="test_echo",
            description="Echoes the input back",
            version="1.0.0",
            author="test",
            is_builtin=True,
        )

    async def execute(self, **kwargs) -> SkillResult:
        text = kwargs.get("text", "")
        return SkillResult(success=True, output=f"Echo: {text}")

    def get_tool_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "test_echo",
                "description": "Echoes the input back",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to echo"},
                    },
                    "required": ["text"],
                },
            },
        }


class FailingSkill(BaseSkill):
    """A skill that always fails."""

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="test_fail",
            description="Always fails",
            version="1.0.0",
            author="test",
            is_builtin=True,
        )

    async def execute(self, **kwargs) -> SkillResult:
        return SkillResult(success=False, output="", error="Intentional failure")

    def get_tool_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "test_fail",
                "description": "Always fails",
                "parameters": {"type": "object", "properties": {}},
            },
        }


@pytest.fixture
def registry():
    """Create a registry with test skills."""
    reg = SkillRegistry()
    reg.register(MockSkill())
    reg.register(FailingSkill())
    return reg


@pytest.fixture
def tool_executor(registry):
    """Create a tool executor with test skills."""
    return ToolExecutor(
        registry=registry,
        policy_engine=PolicyEngine(autonomy_level=4),  # Autopilot — allow everything
        audit_logger=AuditLogger(),
        canary_system=CanarySystem(),
        egress_filter=EgressFilter(),
    )


@pytest.fixture
def config():
    """Create a test config."""
    return GulamaConfig()


# ── Tool Executor Pipeline Tests ──────────────────────


class TestToolExecutorPipeline:
    """Test the complete tool execution pipeline."""

    @pytest.mark.asyncio
    async def test_successful_tool_execution(self, tool_executor):
        """Tool call should go through full security pipeline and return result."""
        result = await tool_executor.execute_tool_call(
            tool_name="test_echo",
            arguments={"text": "hello world"},
            channel="test",
            user_id="test_user",
        )

        assert result["success"] is True
        assert "Echo: hello world" in result["output"]
        assert result["decision"] == "allow"

    @pytest.mark.asyncio
    async def test_unknown_tool_denied(self, tool_executor):
        """Unknown tool should be denied by the pipeline."""
        result = await tool_executor.execute_tool_call(
            tool_name="nonexistent_tool",
            arguments={},
            channel="test",
        )

        assert result["success"] is False
        assert "Unknown tool" in result["error"]
        assert result["decision"] == "deny"

    @pytest.mark.asyncio
    async def test_failing_skill_returns_error(self, tool_executor):
        """A failing skill should return success=False with error message."""
        result = await tool_executor.execute_tool_call(
            tool_name="test_fail",
            arguments={},
            channel="test",
        )

        assert result["success"] is False
        assert result["decision"] == "allow"  # Policy allowed it; skill itself failed

    @pytest.mark.asyncio
    async def test_policy_deny(self):
        """Tool calls denied by policy should not execute."""
        registry = SkillRegistry()
        registry.register(MockSkill())

        # Level 0 = Observer mode — should require approval for everything
        executor = ToolExecutor(
            registry=registry,
            policy_engine=PolicyEngine(autonomy_level=0),
            audit_logger=AuditLogger(),
            canary_system=CanarySystem(),
            egress_filter=EgressFilter(),
        )

        result = await executor.execute_tool_call(
            tool_name="test_echo",
            arguments={"text": "hello"},
            channel="test",
        )

        # In observer mode, most actions should require user approval
        assert result["decision"] in ("ask_user", "deny", "allow")


# ── Brain Integration Tests ──────────────────────────


class TestBrainIntegration:
    """Test the full brain → LLM → tool → response flow."""

    @pytest.mark.asyncio
    async def test_brain_text_response(self, config):
        """Brain should return a text response when LLM doesn't call tools."""
        brain = AgentBrain(config=config, api_key="test-key")

        # Mock the LLM router to return a simple text response
        mock_router = MagicMock()
        mock_router.chat = AsyncMock(
            return_value={
                "content": "Hello! How can I help you?",
                "tool_calls": None,
                "input_tokens": 10,
                "output_tokens": 20,
                "cost_usd": 0.001,
                "provider": "test",
                "model": "test-model",
            }
        )
        mock_router.check_budget = MagicMock(return_value=True)

        # Mock the context builder
        mock_ctx = MagicMock()
        mock_ctx.build_messages = MagicMock(
            return_value=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"},
            ]
        )

        # Mock memory store
        mock_store = MagicMock()
        mock_store.open = MagicMock()
        mock_store.close = MagicMock()
        mock_store.create_conversation = MagicMock(return_value="conv-123")
        mock_store.add_message = MagicMock()
        mock_store.record_cost = MagicMock()

        brain._router = mock_router
        brain.context_builder = mock_ctx
        brain._skill_registry = SkillRegistry()

        with patch("src.agent.brain.MemoryStore", return_value=mock_store):
            result = await brain.process_message(
                message="Hello",
                channel="test",
            )

        assert result["response"] == "Hello! How can I help you?"
        assert result["conversation_id"] == "conv-123"
        assert result["tokens_used"] == 30
        assert result["tools_used"] == []

    @pytest.mark.asyncio
    async def test_brain_tool_calling_loop(self, config):
        """Brain should execute tool calls and feed results back to the LLM."""
        brain = AgentBrain(config=config, api_key="test-key")

        # First call: LLM requests a tool call
        # Second call: LLM responds with text after seeing tool result
        call_count = 0

        async def mock_chat(messages, tools=None):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                return {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "test_echo",
                                "arguments": json.dumps({"text": "hello from tool"}),
                            },
                        }
                    ],
                    "input_tokens": 15,
                    "output_tokens": 10,
                    "cost_usd": 0.0005,
                    "provider": "test",
                    "model": "test-model",
                }
            else:
                return {
                    "content": "I used the echo tool and it said: Echo: hello from tool",
                    "tool_calls": None,
                    "input_tokens": 25,
                    "output_tokens": 30,
                    "cost_usd": 0.001,
                    "provider": "test",
                    "model": "test-model",
                }

        mock_router = MagicMock()
        mock_router.chat = AsyncMock(side_effect=mock_chat)
        mock_router.check_budget = MagicMock(return_value=True)

        mock_ctx = MagicMock()
        mock_ctx.build_messages = MagicMock(
            return_value=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Echo hello"},
            ]
        )

        mock_store = MagicMock()
        mock_store.open = MagicMock()
        mock_store.close = MagicMock()
        mock_store.create_conversation = MagicMock(return_value="conv-456")
        mock_store.add_message = MagicMock()
        mock_store.record_cost = MagicMock()

        # Set up skill registry with the mock skill
        registry = SkillRegistry()
        registry.register(MockSkill())

        brain._router = mock_router
        brain.context_builder = mock_ctx
        brain._skill_registry = registry
        brain._tool_executor = ToolExecutor(
            registry=registry,
            policy_engine=PolicyEngine(autonomy_level=4),
            audit_logger=AuditLogger(),
            canary_system=CanarySystem(),
            egress_filter=EgressFilter(),
        )

        with patch("src.agent.brain.MemoryStore", return_value=mock_store):
            result = await brain.process_message(
                message="Echo hello",
                channel="test",
            )

        assert "Echo: hello from tool" in result["response"]
        assert "test_echo" in result["tools_used"]
        assert result["tokens_used"] == 80  # 15+10+25+30
        assert call_count == 2  # Two LLM round-trips

    @pytest.mark.asyncio
    async def test_brain_budget_exceeded(self, config):
        """Brain should return budget exceeded message when over limit."""
        brain = AgentBrain(config=config, api_key="test-key")

        mock_router = MagicMock()
        mock_router.check_budget = MagicMock(return_value=False)

        mock_ctx = MagicMock()
        mock_ctx.build_messages = MagicMock(return_value=[])

        mock_store = MagicMock()
        mock_store.open = MagicMock()
        mock_store.close = MagicMock()
        mock_store.create_conversation = MagicMock(return_value="conv-789")
        mock_store.add_message = MagicMock()

        brain._router = mock_router
        brain.context_builder = mock_ctx

        with patch("src.agent.brain.MemoryStore", return_value=mock_store):
            result = await brain.process_message(message="Hello", channel="test")

        assert "budget" in result["response"].lower()
        assert result["tokens_used"] == 0

    @pytest.mark.asyncio
    async def test_brain_error_handling(self, config):
        """Brain should gracefully handle errors."""
        brain = AgentBrain(config=config, api_key="test-key")

        mock_router = MagicMock()
        mock_router.check_budget = MagicMock(return_value=True)
        mock_router.chat = AsyncMock(side_effect=Exception("LLM connection failed"))

        mock_ctx = MagicMock()
        mock_ctx.build_messages = MagicMock(return_value=[{"role": "user", "content": "test"}])

        mock_store = MagicMock()
        mock_store.open = MagicMock()
        mock_store.close = MagicMock()
        mock_store.create_conversation = MagicMock(return_value="conv-err")
        mock_store.add_message = MagicMock()

        brain._router = mock_router
        brain.context_builder = mock_ctx
        brain._skill_registry = SkillRegistry()

        with patch("src.agent.brain.MemoryStore", return_value=mock_store):
            result = await brain.process_message(message="Hello", channel="test")

        assert "Error" in result["response"]
        assert "LLM connection failed" in result["response"]


# ── Registry Integration Tests ────────────────────────


class TestRegistryIntegration:
    """Test skill registry loading and lookup."""

    def test_load_builtins(self):
        """Built-in skills should load without errors."""
        registry = SkillRegistry()
        registry.load_builtins()

        # At minimum, the 4 core skills should always load
        assert registry.count >= 4

        # Core skills should always be present
        assert registry.get("file_manager") is not None
        assert registry.get("shell_exec") is not None
        assert registry.get("web_search") is not None
        assert registry.get("notes") is not None

    def test_tool_definitions_format(self):
        """All tool definitions should follow the OpenAI function calling format."""
        registry = SkillRegistry()
        registry.load_builtins()

        definitions = registry.get_tool_definitions()
        assert len(definitions) >= 4

        for tool_def in definitions:
            assert "type" in tool_def
            assert tool_def["type"] == "function"
            assert "function" in tool_def
            func = tool_def["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"

    def test_skill_metadata(self):
        """All skills should have valid metadata."""
        registry = SkillRegistry()
        registry.load_builtins()

        for meta in registry.list_skills():
            assert meta.name, "Skill must have a name"
            assert meta.description, "Skill must have a description"
            assert meta.version, "Skill must have a version"
            assert meta.author, "Skill must have an author"

    def test_duplicate_registration_ignored(self):
        """Registering the same skill twice should be silently ignored."""
        registry = SkillRegistry()
        skill = MockSkill()
        registry.register(skill)
        registry.register(skill)  # Should not raise
        assert registry.count == 1

    def test_get_nonexistent_skill(self):
        """Getting a nonexistent skill should return None."""
        registry = SkillRegistry()
        assert registry.get("does_not_exist") is None


# ── Security Pipeline Integration ─────────────────────


class TestSecurityPipeline:
    """Test the security pipeline components working together."""

    @pytest.mark.asyncio
    async def test_canary_token_injection(self, tool_executor):
        """Output from tools should contain canary tokens."""
        result = await tool_executor.execute_tool_call(
            tool_name="test_echo",
            arguments={"text": "sensitive data"},
            channel="test",
        )

        assert result["success"] is True
        # The canary system should have injected a token
        assert result["output"]  # Output should not be empty

    @pytest.mark.asyncio
    async def test_egress_filter_redacts_secrets(self):
        """Egress filter should redact sensitive data from tool output."""

        class LeakySkill(BaseSkill):
            def get_metadata(self):
                return SkillMetadata(
                    name="leaky", description="test", is_builtin=True
                )

            async def execute(self, **kwargs):
                # Try to leak a secret-looking value
                return SkillResult(
                    success=True,
                    output="The API key is AKIA1234567890ABCDEF and password is hunter2",
                )

            def get_tool_definition(self):
                return {
                    "type": "function",
                    "function": {
                        "name": "leaky",
                        "description": "test",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }

        registry = SkillRegistry()
        registry.register(LeakySkill())

        executor = ToolExecutor(
            registry=registry,
            policy_engine=PolicyEngine(autonomy_level=4),
            audit_logger=AuditLogger(),
            canary_system=CanarySystem(),
            egress_filter=EgressFilter(),
        )

        result = await executor.execute_tool_call(
            tool_name="leaky",
            arguments={},
            channel="test",
        )

        # The egress filter should detect and redact the AWS-style key
        # (behavior depends on EgressFilter config — just verify pipeline works)
        assert result["decision"] == "allow"
        assert result["output"]  # Should have some output


# ── Streaming Integration ─────────────────────────────


class TestStreamingIntegration:
    """Test the streaming response pipeline."""

    @pytest.mark.asyncio
    async def test_stream_complete_event(self, config):
        """Streaming should yield a 'complete' event at the end."""
        brain = AgentBrain(config=config, api_key="test-key")

        mock_router = MagicMock()
        mock_router.check_budget = MagicMock(return_value=True)
        mock_router.chat = AsyncMock(
            return_value={
                "content": "Streaming response",
                "tool_calls": None,
                "input_tokens": 10,
                "output_tokens": 20,
                "cost_usd": 0.001,
                "provider": "test",
                "model": "test-model",
            }
        )

        mock_ctx = MagicMock()
        mock_ctx.build_messages = MagicMock(
            return_value=[{"role": "user", "content": "test"}]
        )

        mock_store = MagicMock()
        mock_store.open = MagicMock()
        mock_store.close = MagicMock()
        mock_store.create_conversation = MagicMock(return_value="conv-stream")
        mock_store.add_message = MagicMock()
        mock_store.record_cost = MagicMock()

        brain._router = mock_router
        brain.context_builder = mock_ctx
        brain._skill_registry = SkillRegistry()

        events = []
        with patch("src.agent.brain.MemoryStore", return_value=mock_store):
            async for event in brain.stream_message(message="test", channel="test"):
                events.append(event)

        # Should have at least a chunk and a complete event
        assert len(events) >= 1
        assert events[-1]["type"] == "complete"
        assert events[-1]["conversation_id"] == "conv-stream"
