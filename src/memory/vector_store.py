"""
ChromaDB vector store for Gulama — semantic memory retrieval.

Provides vector similarity search over conversations, facts, and messages.
Uses ChromaDB with sentence-transformers for embeddings.

This is the RAG backbone: instead of dumping full history (like OpenClaw),
Gulama retrieves only semantically relevant memories.
"""

from __future__ import annotations

from typing import Any

from src.constants import CHROMA_DIR
from src.utils.logging import get_logger

logger = get_logger("vector_store")


class VectorStore:
    """
    ChromaDB-backed vector store for semantic memory retrieval.

    Collections:
    - messages: Conversation messages with embeddings
    - facts: Extracted facts and user preferences
    - conversations: Conversation summaries
    """

    def __init__(self, persist_dir: str | None = None):
        self.persist_dir = persist_dir or str(CHROMA_DIR)
        self._client = None
        self._messages_col = None
        self._facts_col = None
        self._conversations_col = None

    def open(self) -> None:
        """Initialize ChromaDB client and collections."""
        try:
            import chromadb
            from chromadb.config import Settings

            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=False,
                ),
            )

            # Create or get collections
            self._messages_col = self._client.get_or_create_collection(
                name="messages",
                metadata={"hnsw:space": "cosine"},
            )
            self._facts_col = self._client.get_or_create_collection(
                name="facts",
                metadata={"hnsw:space": "cosine"},
            )
            self._conversations_col = self._client.get_or_create_collection(
                name="conversations",
                metadata={"hnsw:space": "cosine"},
            )

            logger.info(
                "vector_store_opened",
                path=self.persist_dir,
                messages=self._messages_col.count(),
                facts=self._facts_col.count(),
                conversations=self._conversations_col.count(),
            )
        except ImportError:
            logger.warning(
                "chromadb_not_available",
                msg="ChromaDB not installed. Vector search disabled. "
                "Install with: pip install chromadb sentence-transformers",
            )
        except Exception as e:
            logger.error("vector_store_open_failed", error=str(e))
            raise VectorStoreError(f"Failed to open vector store: {e}") from e

    def close(self) -> None:
        """Close the vector store."""
        self._client = None
        self._messages_col = None
        self._facts_col = None
        self._conversations_col = None
        logger.info("vector_store_closed")

    @property
    def is_available(self) -> bool:
        """Check if the vector store is initialized."""
        return self._client is not None

    # --- Messages ---

    def add_message(
        self,
        message_id: str,
        content: str,
        conversation_id: str,
        role: str,
        timestamp: str,
    ) -> None:
        """Add a message embedding to the vector store."""
        if not self._messages_col:
            return

        self._messages_col.upsert(
            ids=[message_id],
            documents=[content],
            metadatas=[
                {
                    "conversation_id": conversation_id,
                    "role": role,
                    "timestamp": timestamp,
                }
            ],
        )

    def search_messages(
        self,
        query: str,
        limit: int = 10,
        conversation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar messages using vector similarity."""
        if not self._messages_col or self._messages_col.count() == 0:
            return []

        where_filter = None
        if conversation_id:
            where_filter = {"conversation_id": conversation_id}

        try:
            results = self._messages_col.query(
                query_texts=[query],
                n_results=min(limit, self._messages_col.count()),
                where=where_filter,
            )
            return self._format_results(results)
        except Exception as e:
            logger.warning("message_search_failed", error=str(e))
            return []

    # --- Facts ---

    def add_fact(
        self,
        fact_id: str,
        content: str,
        category: str,
        confidence: float = 1.0,
    ) -> None:
        """Add a fact embedding to the vector store."""
        if not self._facts_col:
            return

        self._facts_col.upsert(
            ids=[fact_id],
            documents=[content],
            metadatas=[
                {
                    "category": category,
                    "confidence": confidence,
                }
            ],
        )

    def search_facts(
        self,
        query: str,
        limit: int = 5,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for relevant facts using vector similarity."""
        if not self._facts_col or self._facts_col.count() == 0:
            return []

        where_filter = None
        if category:
            where_filter = {"category": category}

        try:
            results = self._facts_col.query(
                query_texts=[query],
                n_results=min(limit, self._facts_col.count()),
                where=where_filter,
            )
            return self._format_results(results)
        except Exception as e:
            logger.warning("fact_search_failed", error=str(e))
            return []

    # --- Conversations ---

    def add_conversation_summary(
        self,
        conversation_id: str,
        summary: str,
        channel: str,
        started_at: str,
    ) -> None:
        """Add a conversation summary embedding."""
        if not self._conversations_col:
            return

        self._conversations_col.upsert(
            ids=[conversation_id],
            documents=[summary],
            metadatas=[
                {
                    "channel": channel,
                    "started_at": started_at,
                }
            ],
        )

    def search_conversations(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for relevant past conversations."""
        if not self._conversations_col or self._conversations_col.count() == 0:
            return []

        try:
            results = self._conversations_col.query(
                query_texts=[query],
                n_results=min(limit, self._conversations_col.count()),
            )
            return self._format_results(results)
        except Exception as e:
            logger.warning("conversation_search_failed", error=str(e))
            return []

    # --- Maintenance ---

    def delete_message(self, message_id: str) -> None:
        """Remove a message from the vector store."""
        if self._messages_col:
            try:
                self._messages_col.delete(ids=[message_id])
            except Exception:
                pass

    def delete_fact(self, fact_id: str) -> None:
        """Remove a fact from the vector store."""
        if self._facts_col:
            try:
                self._facts_col.delete(ids=[fact_id])
            except Exception:
                pass

    def delete_conversation(self, conversation_id: str) -> None:
        """Remove a conversation summary from the vector store."""
        if self._conversations_col:
            try:
                self._conversations_col.delete(ids=[conversation_id])
            except Exception:
                pass

    def get_stats(self) -> dict[str, int]:
        """Get vector store statistics."""
        stats = {"messages": 0, "facts": 0, "conversations": 0}
        if self._messages_col:
            stats["messages"] = self._messages_col.count()
        if self._facts_col:
            stats["facts"] = self._facts_col.count()
        if self._conversations_col:
            stats["conversations"] = self._conversations_col.count()
        return stats

    @staticmethod
    def _format_results(results: dict) -> list[dict[str, Any]]:
        """Format ChromaDB query results into a clean list of dicts."""
        formatted = []
        if not results or not results.get("ids"):
            return formatted

        ids = results["ids"][0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            entry = {
                "id": doc_id,
                "content": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "distance": distances[i] if i < len(distances) else 1.0,
                "similarity": 1.0 - (distances[i] if i < len(distances) else 1.0),
            }
            formatted.append(entry)

        return formatted


class VectorStoreError(Exception):
    """Raised for vector store errors."""

    pass
