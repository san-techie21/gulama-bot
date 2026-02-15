"""
Skill signing utility for Gulama.

Signs skill packages using SHA-256 hashes (with optional Sigstore cosign
integration when available). This ensures supply chain integrity.

Usage:
    python -m src.skills.signer --skill-dir ./my-skill --output my-skill-signed.tar.gz
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.utils.logging import get_logger

logger = get_logger("skill_signer")


@dataclass
class SigningResult:
    """Result of a skill signing operation."""
    skill_name: str
    version: str
    sha256: str
    signature_path: str | None = None
    cosign_used: bool = False
    sbom_path: str | None = None


class SkillSigner:
    """
    Signs skill packages for distribution.

    Signing process:
    1. Package skill directory into tar.gz
    2. Compute SHA-256 hash
    3. Generate SBOM (if Syft available)
    4. Sign with cosign (if available) or just use SHA-256 hash
    5. Write signing metadata to skill.toml
    """

    def __init__(self, private_key_path: str | None = None):
        self.private_key_path = private_key_path
        self._cosign_available = self._check_tool("cosign")
        self._syft_available = self._check_tool("syft")

    @staticmethod
    def _check_tool(name: str) -> bool:
        try:
            subprocess.run([name, "version"], capture_output=True, timeout=5, check=False)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def package_skill(self, skill_dir: Path, output_path: Path) -> str:
        """Package a skill directory into a tar.gz archive."""
        if not skill_dir.is_dir():
            raise FileNotFoundError(f"Skill directory not found: {skill_dir}")

        with tarfile.open(output_path, "w:gz") as tar:
            for item in skill_dir.rglob("*"):
                if item.is_file():
                    # Skip hidden files and __pycache__
                    if any(part.startswith(".") or part == "__pycache__" for part in item.parts):
                        continue
                    arcname = str(item.relative_to(skill_dir.parent))
                    tar.add(item, arcname=arcname)

        # Compute hash
        sha256 = self._compute_hash(output_path)
        logger.info("skill_packaged", path=str(output_path), sha256=sha256[:16] + "...")
        return sha256

    def sign_skill(self, skill_dir: Path, output_dir: Path | None = None) -> SigningResult:
        """Sign a skill package."""
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix="gulama_sign_"))

        # Read manifest
        manifest_path = skill_dir / "skill.toml"
        name = skill_dir.name
        version = "0.0.0"

        if manifest_path.exists():
            try:
                import tomli
                with open(manifest_path, "rb") as f:
                    data = tomli.load(f)
                skill = data.get("skill", {})
                name = skill.get("name", name)
                version = skill.get("version", version)
            except Exception:
                pass

        # Package
        package_path = output_dir / f"{name}-{version}.tar.gz"
        sha256 = self.package_skill(skill_dir, package_path)

        result = SigningResult(
            skill_name=name,
            version=version,
            sha256=sha256,
        )

        # Generate SBOM
        if self._syft_available:
            sbom_path = output_dir / f"{name}-{version}.sbom.json"
            self._generate_sbom(skill_dir, sbom_path)
            result.sbom_path = str(sbom_path)

        # Sign with cosign
        if self._cosign_available and self.private_key_path:
            sig_path = output_dir / f"{name}-{version}.sig"
            self._cosign_sign(package_path, sig_path)
            result.signature_path = str(sig_path)
            result.cosign_used = True
        else:
            # Create a simple hash-based signature file
            sig_path = output_dir / f"{name}-{version}.sha256"
            sig_path.write_text(f"{sha256}  {package_path.name}\n")
            result.signature_path = str(sig_path)

        # Update manifest with signature
        self._update_manifest(manifest_path, sha256)

        logger.info(
            "skill_signed",
            name=name,
            version=version,
            sha256=sha256[:16] + "...",
            cosign=result.cosign_used,
        )

        return result

    def verify_skill(self, package_path: Path, expected_hash: str) -> bool:
        """Verify a skill package against its expected hash."""
        actual_hash = self._compute_hash(package_path)
        return actual_hash == expected_hash

    def _cosign_sign(self, package_path: Path, sig_path: Path) -> bool:
        """Sign package with cosign."""
        try:
            cmd = ["cosign", "sign-blob", str(package_path), "--output-signature", str(sig_path)]
            if self.private_key_path:
                cmd.extend(["--key", self.private_key_path])

            result = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
            return result.returncode == 0
        except Exception as e:
            logger.warning("cosign_sign_failed", error=str(e))
            return False

    def _generate_sbom(self, skill_dir: Path, output_path: Path) -> bool:
        """Generate SBOM with Syft."""
        try:
            result = subprocess.run(
                ["syft", str(skill_dir), "-o", "spdx-json", "--file", str(output_path)],
                capture_output=True,
                timeout=60,
                check=False,
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning("sbom_generation_failed", error=str(e))
            return False

    @staticmethod
    def _compute_hash(filepath: Path) -> str:
        """Compute SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def _update_manifest(manifest_path: Path, sha256: str) -> None:
        """Update skill.toml with signing information."""
        if not manifest_path.exists():
            return

        try:
            import tomli
            import tomli_w

            with open(manifest_path, "rb") as f:
                data = tomli.load(f)

            if "signature" not in data:
                data["signature"] = {}
            data["signature"]["sha256"] = sha256

            with open(manifest_path, "wb") as f:
                tomli_w.dump(data, f)
        except Exception as e:
            logger.warning("manifest_update_failed", error=str(e))
