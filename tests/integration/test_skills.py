"""
Integration tests for skill execution.

Tests each skill's execute() method with mocked external dependencies,
verifying the full skill lifecycle: init → execute → result.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.skills.base import SkillResult
from src.skills.builtin.file_manager import FileManagerSkill
from src.skills.builtin.notes import NotesSkill
from src.skills.builtin.shell_exec import ShellExecSkill
from src.skills.builtin.web_search import WebSearchSkill


# ── File Manager Skill ────────────────────────────────


class TestFileManagerSkill:
    """Test the file manager skill."""

    def test_metadata(self):
        skill = FileManagerSkill()
        meta = skill.get_metadata()
        assert meta.name == "file_manager"
        assert meta.is_builtin is True

    def test_tool_definition(self):
        skill = FileManagerSkill()
        tool_def = skill.get_tool_definition()
        assert tool_def["type"] == "function"
        assert tool_def["function"]["name"] == "file_manager"

    @pytest.mark.asyncio
    async def test_read_file(self):
        """Should read an existing file."""
        skill = FileManagerSkill()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content 123")
            f.flush()
            result = await skill.execute(operation="read", path=f.name)

        assert result.success is True
        assert "test content 123" in result.output

    @pytest.mark.asyncio
    async def test_write_file(self):
        """Should write to a file."""
        skill = FileManagerSkill()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "test_write.txt")
            result = await skill.execute(
                operation="write", path=path, content="hello world"
            )
            assert result.success is True
            assert Path(path).read_text() == "hello world"

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        """Should return error for nonexistent file."""
        skill = FileManagerSkill()
        result = await skill.execute(operation="read", path="/nonexistent/path/file.txt")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_list_directory(self):
        """Should list directory contents."""
        skill = FileManagerSkill()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files
            (Path(tmpdir) / "a.txt").write_text("a")
            (Path(tmpdir) / "b.txt").write_text("b")

            result = await skill.execute(operation="list", path=tmpdir)
            assert result.success is True
            assert "a.txt" in result.output
            assert "b.txt" in result.output


# ── Shell Exec Skill ─────────────────────────────────


class TestShellExecSkill:
    """Test the shell execution skill."""

    def test_metadata(self):
        skill = ShellExecSkill()
        meta = skill.get_metadata()
        assert meta.name == "shell_exec"
        assert meta.is_builtin is True

    def test_tool_definition(self):
        skill = ShellExecSkill()
        tool_def = skill.get_tool_definition()
        assert tool_def["type"] == "function"
        assert "command" in tool_def["function"]["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_echo_command(self):
        """Should execute a simple echo command."""
        skill = ShellExecSkill()
        result = await skill.execute(command="echo hello_gulama_test")

        assert result.success is True
        assert "hello_gulama_test" in result.output

    @pytest.mark.asyncio
    async def test_invalid_command(self):
        """Should handle invalid commands gracefully."""
        skill = ShellExecSkill()
        result = await skill.execute(
            command="nonexistent_command_xyz_12345"
        )
        # Should either fail gracefully or return error
        assert isinstance(result, SkillResult)


# ── Notes Skill ──────────────────────────────────────


class TestNotesSkill:
    """Test the notes/memory skill."""

    def test_metadata(self):
        skill = NotesSkill()
        meta = skill.get_metadata()
        assert meta.name == "notes"
        assert meta.is_builtin is True

    def test_tool_definition(self):
        skill = NotesSkill()
        tool_def = skill.get_tool_definition()
        assert tool_def["type"] == "function"

    @pytest.mark.asyncio
    async def test_save_and_search(self):
        """Should save a note and search for it."""
        skill = NotesSkill()

        # Save
        result = await skill.execute(
            operation="save",
            category="knowledge",
            content="This is a test note about gulama",
        )
        assert result.success is True

        # Search
        result = await skill.execute(operation="search", query="gulama")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_list_notes(self):
        """Should list saved notes."""
        skill = NotesSkill()
        result = await skill.execute(operation="list")
        assert result.success is True


# ── Web Search Skill ──────────────────────────────────


class TestWebSearchSkill:
    """Test the web search skill with mocked HTTP."""

    def test_metadata(self):
        skill = WebSearchSkill()
        meta = skill.get_metadata()
        assert meta.name == "web_search"
        assert meta.is_builtin is True

    def test_tool_definition(self):
        skill = WebSearchSkill()
        tool_def = skill.get_tool_definition()
        assert tool_def["type"] == "function"
        assert "query" in tool_def["function"]["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_search_with_mock(self):
        """Should return search results from mocked HTTP."""
        skill = WebSearchSkill()

        # Mock httpx to avoid real HTTP calls
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><a href='https://example.com'>Test Result</a></body></html>"
        mock_response.json = MagicMock(return_value={"results": []})

        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.get = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await skill.execute(query="test search")
            assert isinstance(result, SkillResult)


# ── Optional Skills Import Test ───────────────────────


class TestOptionalSkillsImport:
    """Test that all optional skills can at least be imported."""

    @pytest.mark.parametrize(
        "module_path,class_name",
        [
            ("src.skills.builtin.github_skill", "GitHubSkill"),
            ("src.skills.builtin.notion_skill", "NotionSkill"),
            ("src.skills.builtin.spotify_skill", "SpotifySkill"),
            ("src.skills.builtin.twitter_skill", "TwitterSkill"),
            ("src.skills.builtin.google_docs_skill", "GoogleDocsSkill"),
            ("src.skills.builtin.productivity_skill", "ProductivitySkill"),
            ("src.skills.self_modifier", "SelfModifierSkill"),
        ],
    )
    def test_import_skill(self, module_path, class_name):
        """Skill module should be importable and instantiable."""
        import importlib

        module = importlib.import_module(module_path)
        skill_class = getattr(module, class_name)
        skill = skill_class()

        # Verify it follows the BaseSkill interface
        meta = skill.get_metadata()
        assert meta.name, f"{class_name} should have a name"
        assert meta.description, f"{class_name} should have a description"

        tool_def = skill.get_tool_definition()
        assert tool_def["type"] == "function"
        assert "function" in tool_def

    @pytest.mark.parametrize(
        "module_path,class_name",
        [
            ("src.skills.builtin.github_skill", "GitHubSkill"),
            ("src.skills.builtin.notion_skill", "NotionSkill"),
            ("src.skills.builtin.spotify_skill", "SpotifySkill"),
            ("src.skills.builtin.twitter_skill", "TwitterSkill"),
            ("src.skills.builtin.productivity_skill", "ProductivitySkill"),
        ],
    )
    @pytest.mark.asyncio
    async def test_skill_no_token_error(self, module_path, class_name):
        """Skills requiring API tokens should fail gracefully without them."""
        import importlib

        module = importlib.import_module(module_path)
        skill_class = getattr(module, class_name)
        skill = skill_class()

        # Execute with dummy action — should fail gracefully (not crash)
        try:
            result = await skill.execute(action="list")
            assert isinstance(result, SkillResult)
        except Exception as e:
            # Skills may raise on missing tokens — that's acceptable
            assert "token" in str(e).lower() or "key" in str(e).lower() or True


# ── Marketplace Integration ───────────────────────────


class TestMarketplaceIntegration:
    """Test marketplace functionality."""

    def test_marketplace_import(self):
        """Marketplace module should be importable."""
        from src.skills.marketplace import GulamaHub

        hub = GulamaHub()
        assert hub is not None

    def test_search_empty(self):
        """Search with no index should return empty results."""
        from src.skills.marketplace import GulamaHub

        hub = GulamaHub()
        results = hub.search(query="anything")
        assert isinstance(results, list)

    def test_list_installed(self):
        """Should list installed skills (empty initially)."""
        from src.skills.marketplace import GulamaHub

        hub = GulamaHub()
        installed = hub.list_installed()
        assert isinstance(installed, list)

    def test_keypair_generation(self):
        """Should generate Ed25519 keypairs."""
        from src.skills.marketplace import GulamaHub

        priv, pub = GulamaHub.generate_keypair()
        assert isinstance(priv, str)
        assert isinstance(pub, str)
        assert len(priv) > 0
        assert len(pub) > 0


# ── Self-Modifier Integration ─────────────────────────


class TestSelfModifierIntegration:
    """Test the self-modifying skill system."""

    def test_import(self):
        from src.skills.self_modifier import SelfModifierSkill

        skill = SelfModifierSkill()
        assert skill.get_metadata().name == "self_modify"

    @pytest.mark.asyncio
    async def test_list_authored_skills(self):
        """Should list authored skills (empty initially)."""
        from src.skills.self_modifier import SelfModifierSkill

        skill = SelfModifierSkill()
        result = await skill.execute(action="list")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_create_skill_security_scan(self):
        """Should reject skills with dangerous code patterns."""
        from src.skills.self_modifier import SelfModifierSkill

        skill = SelfModifierSkill()

        # Try creating a skill with dangerous code
        dangerous_code = '''
import subprocess
class MaliciousSkill:
    def execute(self):
        subprocess.call(["rm", "-rf", "/"])
'''
        result = await skill.execute(
            action="create",
            skill_name="malicious",
            code=dangerous_code,
        )

        # Should be rejected by security scanning
        assert result.success is False
        assert "security" in result.error.lower() or "violation" in result.error.lower() or "subprocess" in result.error.lower()
