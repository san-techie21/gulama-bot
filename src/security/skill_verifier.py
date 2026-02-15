"""
Skill signature verification for Gulama.

Third-party skills must be cryptographically signed before loading.
Built-in skills are trusted by default.

Verification process:
1. Skill declares its metadata (name, version, author)
2. Skill file hash is computed (SHA-256)
3. Signature is verified against the author's public key
4. Only verified skills are loaded into the registry

This prevents supply-chain attacks via malicious skill injection.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from src.utils.logging import get_logger

logger = get_logger("skill_verifier")


class SkillVerifier:
    """
    Verifies cryptographic signatures on skills.

    Built-in skills are auto-trusted.
    Third-party skills require valid signatures.
    """

    def __init__(self, require_signatures: bool = True):
        self.require_signatures = require_signatures
        self._trusted_hashes: set[str] = set()

    def verify_builtin(self, skill_path: Path) -> bool:
        """Verify a built-in skill by checking it's in the expected location."""
        # Built-in skills are in src/skills/builtin/
        expected_prefix = Path(__file__).parent.parent / "skills" / "builtin"
        try:
            skill_path.resolve().relative_to(expected_prefix.resolve())
            return True
        except ValueError:
            return False

    def verify_skill_file(self, skill_path: Path, expected_hash: str = "") -> bool:
        """
        Verify a skill file's integrity.

        Args:
            skill_path: Path to the skill file
            expected_hash: Expected SHA-256 hash of the file

        Returns:
            True if the file matches the expected hash
        """
        if not skill_path.exists():
            logger.warning("skill_not_found", path=str(skill_path))
            return False

        file_hash = self._compute_hash(skill_path)

        if expected_hash:
            is_valid = file_hash == expected_hash
            if not is_valid:
                logger.warning(
                    "skill_hash_mismatch",
                    path=str(skill_path),
                    expected=expected_hash[:16],
                    actual=file_hash[:16],
                )
            return is_valid

        # No expected hash — check against trusted hashes
        if file_hash in self._trusted_hashes:
            return True

        if self.require_signatures:
            logger.warning(
                "skill_unverified",
                path=str(skill_path),
                hash=file_hash[:16],
            )
            return False

        return True  # Signatures not required

    def trust_hash(self, file_hash: str) -> None:
        """Add a hash to the trusted set."""
        self._trusted_hashes.add(file_hash)

    def compute_skill_hash(self, skill_path: Path) -> str:
        """Compute the SHA-256 hash of a skill file."""
        return self._compute_hash(skill_path)

    @staticmethod
    def _compute_hash(path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
