#!/usr/bin/env python3
"""
OpenClaw → Gulama migration tool.

Imports conversations, memories, and settings from an existing
OpenClaw installation into Gulama's encrypted storage.

Usage:
    python scripts/migrate_openclaw.py --openclaw-dir ~/.openclaw
    # or via CLI:
    gulama migrate --from openclaw --source ~/.openclaw
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def find_openclaw_dir() -> Path | None:
    """Auto-detect OpenClaw data directory."""
    candidates = [
        Path.home() / ".openclaw",
        Path.home() / "Library" / "Application Support" / "openclaw",
        Path.home() / "AppData" / "Roaming" / "openclaw",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def parse_markdown_memory(filepath: Path) -> list[dict[str, str]]:
    """Parse OpenClaw's MEMORY.md format into structured facts."""
    if not filepath.exists():
        return []

    content = filepath.read_text(encoding="utf-8")
    facts = []
    current_category = "general"

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Headers become categories
        if line.startswith("#"):
            current_category = re.sub(r"^#+\s*", "", line).lower().replace(" ", "_")
        elif line.startswith("- ") or line.startswith("* "):
            fact_content = line[2:].strip()
            if fact_content:
                facts.append({
                    "category": current_category,
                    "content": fact_content,
                })

    return facts


def parse_openclaw_conversations(data_dir: Path) -> list[dict[str, Any]]:
    """Parse OpenClaw conversation files."""
    conversations = []
    conv_dir = data_dir / "conversations"

    if not conv_dir.exists():
        # Try alternative locations
        for alt in ["chats", "history", "messages"]:
            alt_dir = data_dir / alt
            if alt_dir.exists():
                conv_dir = alt_dir
                break
        else:
            return []

    for file in sorted(conv_dir.glob("*.json")):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            conversations.append({
                "id": file.stem,
                "messages": data if isinstance(data, list) else data.get("messages", []),
                "source_file": str(file),
            })
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"  Warning: Could not parse {file.name}: {e}")

    return conversations


def migrate(
    openclaw_dir: str | Path,
    gulama_db_path: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Migrate data from OpenClaw to Gulama.

    Returns migration statistics.
    """
    openclaw_dir = Path(openclaw_dir)
    if not openclaw_dir.exists():
        raise FileNotFoundError(f"OpenClaw directory not found: {openclaw_dir}")

    stats: dict[str, Any] = {
        "facts_imported": 0,
        "conversations_imported": 0,
        "messages_imported": 0,
        "warnings": [],
        "source": str(openclaw_dir),
    }

    print(f"Migrating from: {openclaw_dir}")
    print(f"Dry run: {dry_run}")

    # 1. Import memory/facts
    memory_files = [
        openclaw_dir / "MEMORY.md",
        openclaw_dir / "memory.md",
        openclaw_dir / "SOUL.md",
        openclaw_dir / "soul.md",
    ]

    all_facts = []
    for mf in memory_files:
        if mf.exists():
            print(f"  Found memory file: {mf.name}")
            facts = parse_markdown_memory(mf)
            all_facts.extend(facts)
            print(f"    Extracted {len(facts)} facts")

    stats["facts_imported"] = len(all_facts)

    # 2. Import conversations
    conversations = parse_openclaw_conversations(openclaw_dir)
    stats["conversations_imported"] = len(conversations)

    total_messages = sum(len(c.get("messages", [])) for c in conversations)
    stats["messages_imported"] = total_messages
    print(f"  Found {len(conversations)} conversations ({total_messages} messages)")

    # 3. Check for credentials (warn but DON'T import)
    config_files = list(openclaw_dir.glob("*.yml")) + list(openclaw_dir.glob("*.yaml"))
    config_files += list(openclaw_dir.glob("*.json"))
    for cf in config_files:
        try:
            content = cf.read_text(encoding="utf-8")
            if any(pattern in content.lower() for pattern in ["api_key", "api-key", "apikey", "secret", "token"]):
                stats["warnings"].append(
                    f"SECURITY: {cf.name} contains potential credentials. "
                    f"These were NOT imported. Re-enter them in Gulama's encrypted vault."
                )
                print(f"  WARNING: {cf.name} contains credentials — NOT importing (security)")
        except UnicodeDecodeError:
            pass

    if dry_run:
        print("\nDry run complete. No data was written.")
        return stats

    # 4. Write to Gulama
    from src.memory.store import MemoryStore

    db_path = Path(gulama_db_path) if gulama_db_path else None
    store = MemoryStore(db_path=db_path)
    store.open()

    # Import facts
    for fact in all_facts:
        store.add_fact(
            category=fact["category"],
            content=fact["content"],
            confidence=0.8,  # Lower confidence for imported data
        )

    # Import conversations
    for conv in conversations:
        conv_id = store.create_conversation(
            channel="openclaw_import",
            user_id="imported",
        )
        for msg in conv.get("messages", []):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant", "system") and content:
                store.add_message(
                    conversation_id=conv_id,
                    role=role,
                    content=content,
                )

    store.close()
    print(f"\nMigration complete: {stats['facts_imported']} facts, "
          f"{stats['conversations_imported']} conversations, "
          f"{stats['messages_imported']} messages")

    return stats


def main():
    """CLI entry point for migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate from OpenClaw to Gulama")
    parser.add_argument(
        "--openclaw-dir",
        type=str,
        help="Path to OpenClaw data directory",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to Gulama database (default: auto-detect)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without writing data",
    )

    args = parser.parse_args()

    openclaw_dir = args.openclaw_dir
    if not openclaw_dir:
        detected = find_openclaw_dir()
        if detected:
            print(f"Auto-detected OpenClaw directory: {detected}")
            openclaw_dir = str(detected)
        else:
            print("Error: Could not find OpenClaw directory. Use --openclaw-dir to specify.")
            sys.exit(1)

    try:
        stats = migrate(openclaw_dir, args.db_path, args.dry_run)
        if stats["warnings"]:
            print("\nWarnings:")
            for w in stats["warnings"]:
                print(f"  {w}")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
