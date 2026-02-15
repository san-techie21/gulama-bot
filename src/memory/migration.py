"""
Schema migration manager for Gulama memory store.

Handles database schema upgrades as the application evolves.
Migrations are numbered and applied in order.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from src.utils.logging import get_logger

logger = get_logger("migration")

# Migration scripts — each is a (version, description, sql) tuple
MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "Initial schema",
        "",  # Already applied by schema.py
    ),
    (
        2,
        "Add embedding_id columns for vector store integration",
        """
        -- Add embedding_id to messages if not exists
        ALTER TABLE messages ADD COLUMN embedding_id TEXT;
        -- Add embedding_id to facts if not exists
        ALTER TABLE facts ADD COLUMN embedding_id TEXT;
        """,
    ),
    (
        3,
        "Add user_id to conversations for multi-user support",
        """
        ALTER TABLE conversations ADD COLUMN user_id TEXT;
        CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
        """,
    ),
    (
        4,
        "Add personas table",
        """
        CREATE TABLE IF NOT EXISTS personas (
            name TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            config_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
    ),
    (
        5,
        "Add scheduled tasks table",
        """
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            cron_expression TEXT NOT NULL,
            action_type TEXT NOT NULL,
            action_config TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            last_run TEXT,
            next_run TEXT,
            created_at TEXT NOT NULL
        );
        """,
    ),
]


class MigrationManager:
    """Handles database schema migrations."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_current_version(self) -> int:
        """Get the current schema version."""
        try:
            row = self.conn.execute("SELECT MAX(version) as v FROM schema_version").fetchone()
            return int(row[0]) if row and row[0] else 0
        except sqlite3.OperationalError:
            return 0

    def get_pending_migrations(self) -> list[tuple[int, str, str]]:
        """Get migrations that haven't been applied yet."""
        current = self.get_current_version()
        return [(v, desc, sql) for v, desc, sql in MIGRATIONS if v > current]

    def apply_pending(self) -> list[int]:
        """Apply all pending migrations."""
        pending = self.get_pending_migrations()
        applied = []

        for version, description, sql in pending:
            try:
                if sql.strip():
                    # Some ALTER TABLE commands may fail if column already exists
                    for statement in sql.strip().split(";"):
                        statement = statement.strip()
                        if statement:
                            try:
                                self.conn.execute(statement)
                            except sqlite3.OperationalError as e:
                                if "duplicate column" in str(e).lower():
                                    logger.debug("column_exists", version=version)
                                else:
                                    raise

                # Record migration
                self.conn.execute(
                    "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, datetime('now'))",
                    (version,),
                )
                self.conn.commit()
                applied.append(version)
                logger.info("migration_applied", version=version, description=description)

            except Exception as e:
                logger.error("migration_failed", version=version, error=str(e))
                raise MigrationError(f"Migration {version} failed: {e}") from e

        if applied:
            logger.info("migrations_complete", applied=applied)
        else:
            logger.debug("no_pending_migrations")

        return applied

    def get_history(self) -> list[dict[str, Any]]:
        """Get migration history."""
        try:
            rows = self.conn.execute(
                "SELECT version, applied_at FROM schema_version ORDER BY version"
            ).fetchall()
            return [{"version": r[0], "applied_at": r[1]} for r in rows]
        except sqlite3.OperationalError:
            return []


class MigrationError(Exception):
    """Raised for migration failures."""

    pass
