"""Tests for the tamper-proof audit logger."""

import json

import pytest

from src.security.audit_logger import AuditLogger


class TestAuditLogger:
    """Test the hash-chain audit logger."""

    def test_log_entry(self, audit_dir):
        """Test logging a single entry."""
        logger = AuditLogger(audit_dir=audit_dir)
        entry = logger.log(
            action="file:read",
            actor="agent",
            resource="/tmp/test.txt",
            decision="allow",
            policy="autonomy",
        )

        assert entry.action == "file:read"
        assert entry.actor == "agent"
        assert entry.decision == "allow"
        assert entry.entry_hash  # Should have a hash
        assert entry.prev_hash == "genesis"  # First entry

    def test_hash_chain(self, audit_dir):
        """Test that entries form a valid hash chain."""
        logger = AuditLogger(audit_dir=audit_dir)

        entry1 = logger.log(
            action="file:read", actor="agent",
            resource="/tmp/a", decision="allow",
        )
        entry2 = logger.log(
            action="shell:exec", actor="agent",
            resource="ls -la", decision="ask_user",
        )
        entry3 = logger.log(
            action="network:request", actor="agent",
            resource="https://example.com", decision="deny",
        )

        # Chain should link entries
        assert entry1.prev_hash == "genesis"
        assert entry2.prev_hash == entry1.entry_hash
        assert entry3.prev_hash == entry2.entry_hash

    def test_verify_valid_chain(self, audit_dir):
        """Test chain verification passes for untampered logs."""
        logger = AuditLogger(audit_dir=audit_dir)

        for i in range(5):
            logger.log(
                action=f"action_{i}",
                actor="agent",
                resource=f"resource_{i}",
                decision="allow",
            )

        is_valid, msg = logger.verify_chain()
        assert is_valid
        assert "5 entries verified" in msg

    def test_detect_tampering(self, audit_dir):
        """Test that tampered entries are detected."""
        logger = AuditLogger(audit_dir=audit_dir)

        for i in range(3):
            logger.log(
                action=f"action_{i}",
                actor="agent",
                resource=f"resource_{i}",
                decision="allow",
            )

        # Read entries, tamper with one, and verify
        entries = logger.read_entries()
        assert len(entries) == 3

        # Tamper: change the decision of entry 1
        entries[1].decision = "deny"  # Changed from "allow"

        is_valid, msg = logger.verify_chain(entries)
        assert not is_valid
        assert "tampered" in msg.lower() or "mismatch" in msg.lower()

    def test_summary(self, audit_dir):
        """Test audit summary generation."""
        logger = AuditLogger(audit_dir=audit_dir)

        logger.log(action="file:read", actor="agent", resource="a", decision="allow")
        logger.log(action="shell:exec", actor="agent", resource="b", decision="deny")
        logger.log(action="file:read", actor="agent", resource="c", decision="allow")

        summary = logger.get_summary()
        assert summary["total_entries"] == 3
        assert summary["decisions"]["allow"] == 2
        assert summary["decisions"]["deny"] == 1
        assert summary["chain_valid"] is True

    def test_empty_chain_valid(self, audit_dir):
        """An empty chain should be valid."""
        logger = AuditLogger(audit_dir=audit_dir)
        is_valid, msg = logger.verify_chain()
        assert is_valid
