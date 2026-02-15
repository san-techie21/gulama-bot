"""Gulama CLI — command-line interface and setup wizard."""

from src.cli.commands import cli
from src.cli.doctor import SecurityDoctor

__all__ = ["cli", "SecurityDoctor"]
