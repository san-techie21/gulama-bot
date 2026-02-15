"""Tests for the encrypted memory store."""

import pytest

from src.memory.store import MemoryStore, MemoryStoreError


class TestMemoryStore:
    """Test the memory store CRUD operations."""

    def test_open_and_close(self, db_path):
        """Test opening and closing the store."""
        store = MemoryStore(db_path=db_path)
        store.open()
        assert store.conn is not None
        store.close()

    def test_not_opened_raises(self, db_path):
        """Test that operations on an unopened store fail."""
        store = MemoryStore(db_path=db_path)
        with pytest.raises(MemoryStoreError, match="not opened"):
            _ = store.conn

    def test_conversations(self, db_path):
        """Test conversation CRUD."""
        store = MemoryStore(db_path=db_path)
        store.open()

        # Create
        conv_id = store.create_conversation(channel="cli", user_id="user1")
        assert conv_id

        # Get
        conv = store.get_conversation(conv_id)
        assert conv is not None
        assert conv["channel"] == "cli"
        assert conv["user_id"] == "user1"

        # End
        store.end_conversation(conv_id, summary="test summary")
        conv = store.get_conversation(conv_id)
        assert conv["summary"] == "test summary"
        assert conv["ended_at"] is not None

        store.close()

    def test_messages(self, db_path):
        """Test message operations."""
        store = MemoryStore(db_path=db_path)
        store.open()

        conv_id = store.create_conversation(channel="cli")

        # Add messages
        msg1 = store.add_message(conv_id, role="user", content="Hello")
        msg2 = store.add_message(conv_id, role="assistant", content="Hi there!")

        # Get messages
        messages = store.get_messages(conv_id)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        assert messages[1]["role"] == "assistant"

        # Recent messages
        recent = store.get_recent_messages(limit=10)
        assert len(recent) == 2

        store.close()

    def test_facts(self, db_path):
        """Test fact storage and retrieval."""
        store = MemoryStore(db_path=db_path)
        store.open()

        # Add facts
        f1 = store.add_fact(category="preference", content="User likes Python")
        f2 = store.add_fact(category="knowledge", content="Project uses FastAPI")

        # Get by category
        prefs = store.get_facts(category="preference")
        assert len(prefs) == 1
        assert prefs[0]["content"] == "User likes Python"

        # Get all
        all_facts = store.get_facts()
        assert len(all_facts) == 2

        # Search
        results = store.search_facts("Python")
        assert len(results) == 1
        assert "Python" in results[0]["content"]

        store.close()

    def test_cost_tracking(self, db_path):
        """Test cost tracking."""
        store = MemoryStore(db_path=db_path)
        store.open()

        store.record_cost(
            provider="anthropic",
            model="claude-sonnet",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.01,
            channel="cli",
        )

        cost = store.get_today_cost()
        assert cost == 0.01

        summary = store.get_cost_summary(days=7)
        assert len(summary) == 1

        store.close()

    def test_stats(self, db_path):
        """Test database statistics."""
        store = MemoryStore(db_path=db_path)
        store.open()

        conv_id = store.create_conversation(channel="cli")
        store.add_message(conv_id, role="user", content="test")
        store.add_fact(category="knowledge", content="test fact")

        stats = store.get_stats()
        assert stats["conversations"] == 1
        assert stats["messages"] == 1
        assert stats["facts"] == 1

        store.close()

    def test_schema_version(self, db_path):
        """Test schema version tracking."""
        store = MemoryStore(db_path=db_path)
        store.open()

        version = store.get_schema_version()
        assert version == 1

        store.close()
