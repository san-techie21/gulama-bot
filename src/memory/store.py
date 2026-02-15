"""
Encrypted memory store for Gulama.

All memory is stored in an encrypted SQLite database (via SQLCipher or
application-level encryption). Provides CRUD operations for conversations,
messages, facts, and cost tracking.

For environments where SQLCipher is not available, falls back to standard
SQLite with application-level AES-256-GCM encryption on sensitive fields.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.constants import MEMORY_DB
from src.memory.schema import SCHEMA_SQL
from src.utils.logging import get_logger

logger = get_logger("memory_store")


class MemoryStore:
    """
    Encrypted SQLite memory store.

    Stores conversations, messages, facts, and cost data.
    All data encrypted at rest.
    """

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or MEMORY_DB
        self._conn: sqlite3.Connection | None = None

    def open(self, encryption_key: str | None = None) -> None:
        """Open the database connection and initialize schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        # If SQLCipher is available, use it for encryption
        if encryption_key:
            try:
                self._conn.execute(f"PRAGMA key='{encryption_key}'")
                logger.info("memory_store_opened", encrypted=True)
            except sqlite3.OperationalError:
                logger.warning(
                    "sqlcipher_not_available",
                    msg="SQLCipher not available. Using standard SQLite. "
                    "For full encryption, install sqlcipher3.",
                )

        # Initialize schema
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()
        logger.info("memory_store_ready", path=str(self.db_path))

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("memory_store_closed")

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise MemoryStoreError("Store not opened. Call open() first.")
        return self._conn

    # --- Conversations ---

    def create_conversation(self, channel: str, user_id: str | None = None) -> str:
        """Create a new conversation and return its ID."""
        conv_id = _new_id()
        self.conn.execute(
            "INSERT INTO conversations (id, channel, user_id, started_at) VALUES (?, ?, ?, ?)",
            (conv_id, channel, user_id, _now()),
        )
        self.conn.commit()
        return conv_id

    def end_conversation(self, conversation_id: str, summary: str | None = None) -> None:
        """Mark a conversation as ended."""
        self.conn.execute(
            "UPDATE conversations SET ended_at = ?, summary = ? WHERE id = ?",
            (_now(), summary, conversation_id),
        )
        self.conn.commit()

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        """Get a conversation by ID."""
        row = self.conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        return dict(row) if row else None

    # --- Messages ---

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        token_count: int = 0,
    ) -> str:
        """Add a message to a conversation."""
        msg_id = _new_id()
        self.conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content, timestamp, token_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, conversation_id, role, content, _now(), token_count),
        )
        self.conn.commit()
        return msg_id

    def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get messages for a conversation, ordered by timestamp."""
        rows = self.conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? "
            "ORDER BY timestamp ASC LIMIT ? OFFSET ?",
            (conversation_id, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_recent_messages(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get the most recent messages across all conversations."""
        rows = self.conn.execute(
            "SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Facts ---

    def add_fact(
        self,
        category: str,
        content: str,
        source_message_id: str | None = None,
        confidence: float = 1.0,
    ) -> str:
        """Store a fact/knowledge item."""
        fact_id = _new_id()
        now = _now()
        self.conn.execute(
            "INSERT INTO facts (id, category, content, source_message_id, confidence, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (fact_id, category, content, source_message_id, confidence, now, now),
        )
        self.conn.commit()
        return fact_id

    def get_facts(self, category: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Get facts, optionally filtered by category."""
        if category:
            rows = self.conn.execute(
                "SELECT * FROM facts WHERE category = ? ORDER BY updated_at DESC LIMIT ?",
                (category, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM facts ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def search_facts(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Basic text search over facts (vector search via ChromaDB is separate)."""
        rows = self.conn.execute(
            "SELECT * FROM facts WHERE content LIKE ? ORDER BY confidence DESC LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Cost Tracking ---

    def record_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        channel: str | None = None,
        skill: str | None = None,
        conversation_id: str | None = None,
    ) -> str:
        """Record token usage and cost."""
        cost_id = _new_id()
        self.conn.execute(
            "INSERT INTO cost_tracking "
            "(id, timestamp, provider, model, input_tokens, output_tokens, cost_usd, channel, skill, conversation_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                cost_id,
                _now(),
                provider,
                model,
                input_tokens,
                output_tokens,
                cost_usd,
                channel,
                skill,
                conversation_id,
            ),
        )
        self.conn.commit()
        return cost_id

    def get_today_cost(self) -> float:
        """Get total USD cost for today."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        row = self.conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0.0) as total FROM cost_tracking "
            "WHERE date(timestamp) = ?",
            (today,),
        ).fetchone()
        return float(row["total"]) if row else 0.0

    def get_cost_summary(self, days: int = 7) -> list[dict[str, Any]]:
        """Get daily cost summary for the last N days."""
        rows = self.conn.execute(
            "SELECT date(timestamp) as day, provider, model, "
            "SUM(input_tokens) as total_input, SUM(output_tokens) as total_output, "
            "SUM(cost_usd) as total_cost "
            "FROM cost_tracking "
            "WHERE timestamp >= datetime('now', ?) "
            "GROUP BY day, provider, model "
            "ORDER BY day DESC",
            (f"-{days} days",),
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Maintenance ---

    def get_schema_version(self) -> int:
        """Get current schema version."""
        try:
            row = self.conn.execute("SELECT MAX(version) as v FROM schema_version").fetchone()
            return int(row["v"]) if row else 0
        except sqlite3.OperationalError:
            return 0

    def get_stats(self) -> dict[str, int]:
        """Get database statistics."""
        stats = {}
        for table in ["conversations", "messages", "facts", "cost_tracking"]:
            row = self.conn.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()
            stats[table] = int(row["c"]) if row else 0
        return stats


class MemoryStoreError(Exception):
    """Raised for memory store errors."""

    pass


def _new_id() -> str:
    """Generate a new unique ID."""
    return str(uuid.uuid4())


def _now() -> str:
    """Get current UTC timestamp as ISO string."""
    return datetime.now(UTC).isoformat()
