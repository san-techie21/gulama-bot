"""Shared test fixtures for Gulama."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def vault_path(tmp_dir):
    """Provide a temporary vault path."""
    return tmp_dir / "test_vault.age"


@pytest.fixture
def db_path(tmp_dir):
    """Provide a temporary database path."""
    return tmp_dir / "test_memory.db"


@pytest.fixture
def audit_dir(tmp_dir):
    """Provide a temporary audit directory."""
    d = tmp_dir / "audit"
    d.mkdir()
    return d
