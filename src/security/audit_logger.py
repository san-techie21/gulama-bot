"""
Tamper-proof audit logger for Gulama.

Every security-relevant action is logged with:
- Timestamp (UTC)
- Action type
- Actor (user, agent, system)
- Resource affected
- Policy decision
- Hash chain (each entry includes hash of previous entry)

The hash chain makes it detectable if any log entry is modified
or deleted. A future Rust-based Merkle tree implementation will
provide even stronger guarantees.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.constants import AUDIT_DIR
from src.utils.logging import get_logger

logger = get_logger("audit")


@dataclass
class AuditEntry:
    """A single audit log entry."""

    timestamp: str
    action: str
    actor: str  # "user", "agent", "system"
    resource: str
    decision: str  # "allow", "deny", "ask_user"
    policy: str  # Policy that made the decision
    detail: str = ""
    channel: str = ""
    prev_hash: str = ""  # Hash of previous entry (chain)
    entry_hash: str = ""  # Hash of this entry


class AuditLogger:
    """
    Tamper-proof audit logger with hash chain.

    Every entry includes the hash of the previous entry,
    creating a chain that detects modifications.
    """

    def __init__(self, audit_dir: Path | None = None):
        self.audit_dir = audit_dir or AUDIT_DIR
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self._current_file: Path | None = None
        self._prev_hash: str = "genesis"  # Hash of the genesis block
        self._entry_count: int = 0

    def log(
        self,
        action: str,
        actor: str,
        resource: str,
        decision: str,
        policy: str = "",
        detail: str = "",
        channel: str = "",
    ) -> AuditEntry:
        """
        Log a security-relevant action.

        The entry is appended to the current audit file with
        a hash chain linking it to the previous entry.
        """
        entry = AuditEntry(
            timestamp=datetime.now(UTC).isoformat(),
            action=action,
            actor=actor,
            resource=resource,
            decision=decision,
            policy=policy,
            detail=detail,
            channel=channel,
            prev_hash=self._prev_hash,
        )

        # Calculate entry hash (includes prev_hash for chaining)
        entry.entry_hash = self._hash_entry(entry)
        self._prev_hash = entry.entry_hash
        self._entry_count += 1

        # Write to audit file
        self._write_entry(entry)

        logger.info(
            "audit_logged",
            action=action,
            actor=actor,
            decision=decision,
            entry_hash=entry.entry_hash[:12],
        )

        return entry

    def verify_chain(self, entries: list[AuditEntry] | None = None) -> tuple[bool, str]:
        """
        Verify the integrity of the audit chain.

        Returns (is_valid, message).
        If any entry has been tampered with, returns False.
        """
        if entries is None:
            entries = self.read_entries()

        if not entries:
            return True, "No entries to verify."

        prev_hash = "genesis"
        for i, entry in enumerate(entries):
            # Verify prev_hash links
            if entry.prev_hash != prev_hash:
                return False, f"Chain broken at entry {i}: prev_hash mismatch."

            # Verify entry hash
            expected_hash = self._hash_entry(entry)
            if entry.entry_hash != expected_hash:
                return False, f"Entry {i} tampered: hash mismatch."

            prev_hash = entry.entry_hash

        return True, f"Chain valid. {len(entries)} entries verified."

    def read_entries(self, date: str | None = None) -> list[AuditEntry]:
        """Read audit entries for a given date (or today)."""
        if date is None:
            date = datetime.now(UTC).strftime("%Y-%m-%d")

        file_path = self.audit_dir / f"audit-{date}.jsonl"
        if not file_path.exists():
            return []

        entries = []
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    entries.append(AuditEntry(**data))

        return entries

    def get_summary(self, date: str | None = None) -> dict[str, Any]:
        """Get a summary of audit entries for a date."""
        entries = self.read_entries(date)

        decisions = {"allow": 0, "deny": 0, "ask_user": 0}
        actions: dict[str, int] = {}

        for entry in entries:
            decisions[entry.decision] = decisions.get(entry.decision, 0) + 1
            actions[entry.action] = actions.get(entry.action, 0) + 1

        return {
            "total_entries": len(entries),
            "decisions": decisions,
            "actions": actions,
            "chain_valid": self.verify_chain(entries)[0],
        }

    def _write_entry(self, entry: AuditEntry) -> None:
        """Append an entry to the current audit file."""
        date = datetime.now(UTC).strftime("%Y-%m-%d")
        file_path = self.audit_dir / f"audit-{date}.jsonl"

        with open(file_path, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    @staticmethod
    def _hash_entry(entry: AuditEntry) -> str:
        """Calculate the hash of an audit entry."""
        # Hash everything except the entry_hash itself
        data = {
            "timestamp": entry.timestamp,
            "action": entry.action,
            "actor": entry.actor,
            "resource": entry.resource,
            "decision": entry.decision,
            "policy": entry.policy,
            "detail": entry.detail,
            "channel": entry.channel,
            "prev_hash": entry.prev_hash,
        }
        payload = json.dumps(data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
