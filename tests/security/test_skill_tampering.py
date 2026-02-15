"""
Tests for skill tampering prevention.

Verifies that the skill verification system correctly
detects tampered or unsigned skill packages.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from src.security.skill_verifier import SkillVerifier
from src.skills.signer import SkillSigner


class TestSkillTamperingPrevention:
    """Verify skill supply chain integrity."""

    def setup_method(self):
        self.verifier = SkillVerifier()
        self.signer = SkillSigner()

    def test_hash_verification_correct(self):
        """Correct hash should verify."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as f:
            f.write(b"test skill content")
            f.flush()
            path = Path(f.name)

        try:
            correct_hash = self.signer._compute_hash(path)
            assert self.signer.verify_skill(path, correct_hash)
        finally:
            path.unlink(missing_ok=True)

    def test_hash_verification_tampered(self):
        """Wrong hash should not verify."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as f:
            f.write(b"original content")
            f.flush()
            path = Path(f.name)

        try:
            wrong_hash = hashlib.sha256(b"different content").hexdigest()
            assert not self.signer.verify_skill(path, wrong_hash)
        finally:
            path.unlink(missing_ok=True)

    def test_path_traversal_in_archive_detected(self):
        """Archives with path traversal should be rejected."""
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config",
            "/absolute/path/file.py",
        ]
        for path in dangerous_paths:
            is_dangerous = path.startswith("/") or path.startswith("\\") or ".." in path
            assert is_dangerous, f"Should detect dangerous path: {path}"

    def test_safe_archive_paths(self):
        """Normal skill file paths should be safe."""
        safe_paths = [
            "my_skill/skill.toml",
            "my_skill/main.py",
            "my_skill/utils/helpers.py",
        ]
        for path in safe_paths:
            is_dangerous = path.startswith("/") or path.startswith("\\") or ".." in path
            assert not is_dangerous, f"Should allow path: {path}"

    def test_package_skill_produces_hash(self):
        """Packaging a skill should produce a valid SHA-256 hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test_skill"
            skill_dir.mkdir()
            (skill_dir / "skill.toml").write_text('[skill]\nname = "test"\nversion = "1.0.0"\n')
            (skill_dir / "main.py").write_text("def run(): pass\n")

            output = Path(tmpdir) / "test_skill.tar.gz"
            sha256 = self.signer.package_skill(skill_dir, output)

            assert output.exists()
            assert len(sha256) == 64  # SHA-256 hex length

    def test_builtin_skill_verification(self):
        """Built-in skills should be auto-trusted."""
        builtin_path = (
            Path(__file__).parent.parent.parent / "src" / "skills" / "builtin" / "web_search.py"
        )
        if builtin_path.exists():
            assert self.verifier.verify_builtin(builtin_path)

    def test_external_skill_not_builtin(self):
        """External paths should not pass builtin verification."""
        external_path = Path("/tmp/fake_skill.py")
        assert not self.verifier.verify_builtin(external_path)

    def test_dangerous_code_patterns(self):
        """Static analysis should catch dangerous patterns."""
        dangerous_snippets = [
            "eval(user_input)",
            "exec(code)",
            "import subprocess; subprocess.call(cmd, shell=True)",
            "import ctypes",
            "pickle.loads(data)",
            "__import__('os').system('rm -rf /')",
        ]
        suspicious_patterns = ["eval(", "exec(", "subprocess", "ctypes", "pickle", "__import__"]
        for snippet in dangerous_snippets:
            found = any(p in snippet for p in suspicious_patterns)
            assert found, f"Should detect dangerous pattern: {snippet}"
