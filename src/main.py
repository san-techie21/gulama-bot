"""
Gulama — Main entry point.

This module bootstraps the entire application:
1. Loads configuration
2. Initializes logging
3. Sets up the secrets vault
4. Initializes the memory store
5. Starts the requested channel/gateway

Usage:
    python -m src.main          # Start with defaults
    gulama start                # Via CLI entry point
    gulama start --channel cli  # Interactive chat
"""

from __future__ import annotations

import os
import signal
import sys
from pathlib import Path

from src.constants import DATA_DIR, PROJECT_DISPLAY_NAME, PROJECT_VERSION
from src.utils.logging import get_logger, setup_logging

logger = get_logger("main")


def bootstrap() -> None:
    """
    Bootstrap the Gulama application.

    Called before any channel starts. Sets up:
    - Data directory
    - Logging
    - Configuration
    - PID file
    """
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load config and setup logging
    from src.gateway.config import load_config

    config = load_config()
    setup_logging(
        level=config.logging.level,
        json_format=config.logging.format == "json",
    )

    logger.info(
        "gulama_bootstrap",
        version=PROJECT_VERSION,
        data_dir=str(DATA_DIR),
    )

    # Write PID file
    pid_file = DATA_DIR / "gulama.pid"
    pid_file.write_text(str(os.getpid()))

    # Setup signal handlers for graceful shutdown
    def _shutdown(signum, frame):
        logger.info("shutdown_signal", signal=signum)
        pid_file.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, _shutdown)

    return config


def main() -> None:
    """Main entry point — starts Gulama via CLI."""
    from src.cli.commands import cli

    cli()


if __name__ == "__main__":
    main()
