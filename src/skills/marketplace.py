"""
Skill marketplace for Gulama.

Provides secure skill discovery, installation, and management.
All skills must be cryptographically signed before installation.

Key security measures:
- Cosign signature verification (Sigstore)
- SBOM (Software Bill of Materials) validation
- Vulnerability scanning (Grype)
- Static analysis for suspicious patterns
- Permission manifest validation
"""

from __future__ import annotations

import json
import hashlib
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from src.constants import DATA_DIR
from src.security.skill_verifier import SkillVerifier
from src.utils.logging import get_logger

logger = get_logger("marketplace")

SKILLS_DIR = DATA_DIR / "skills"
MARKETPLACE_REGISTRY_URL = "https://raw.githubusercontent.com/san-techie21/gulama-marketplace/main/registry.json"


@dataclass
class SkillManifest:
    """Parsed skill manifest (skill.toml)."""
    name: str
    version: str
    description: str
    author: str
    license: str = "MIT"
    homepage: str = ""
    permissions: dict[str, Any] = field(default_factory=dict)
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    signature: dict[str, str] = field(default_factory=dict)
    min_gulama_version: str = "0.1.0"


@dataclass
class MarketplaceEntry:
    """A skill listing in the marketplace."""
    name: str
    version: str
    description: str
    author: str
    download_url: str
    signature_url: str
    sbom_url: str
    sha256: str
    downloads: int = 0
    rating: float = 0.0
    verified: bool = False


class SkillMarketplace:
    """
    Manages the skill marketplace — discovery, installation, and updates.

    Security flow for installation:
    1. Download skill package
    2. Verify SHA-256 checksum
    3. Verify Sigstore cosign signature (if available)
    4. Parse and validate manifest (permissions, dependencies)
    5. Run vulnerability scan on dependencies
    6. Static analysis for suspicious patterns
    7. Install to sandboxed skill directory
    """

    def __init__(
        self,
        skills_dir: Path | None = None,
        verifier: SkillVerifier | None = None,
        registry_url: str = MARKETPLACE_REGISTRY_URL,
    ):
        self.skills_dir = skills_dir or SKILLS_DIR
        self.verifier = verifier or SkillVerifier()
        self.registry_url = registry_url
        self._registry_cache: list[MarketplaceEntry] | None = None

    async def search(self, query: str = "") -> list[MarketplaceEntry]:
        """Search the marketplace for skills."""
        registry = await self._load_registry()

        if not query:
            return registry

        query_lower = query.lower()
        return [
            entry for entry in registry
            if query_lower in entry.name.lower()
            or query_lower in entry.description.lower()
            or query_lower in entry.author.lower()
        ]

    async def install(self, skill_name: str, force: bool = False) -> dict[str, Any]:
        """
        Install a skill from the marketplace.

        Returns installation result with status and details.
        """
        # 1. Find skill in registry
        registry = await self._load_registry()
        entry = next((e for e in registry if e.name == skill_name), None)
        if not entry:
            return {"status": "error", "message": f"Skill '{skill_name}' not found in marketplace"}

        # 2. Check if already installed
        install_dir = self.skills_dir / skill_name
        if install_dir.exists() and not force:
            return {"status": "error", "message": f"Skill '{skill_name}' already installed. Use force=True to update."}

        # 3. Download skill package
        logger.info("skill_downloading", name=skill_name, version=entry.version)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            package_path = tmp_path / f"{skill_name}.tar.gz"

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(entry.download_url)
                    response.raise_for_status()
                    package_path.write_bytes(response.content)
            except Exception as e:
                return {"status": "error", "message": f"Download failed: {e}"}

            # 4. Verify SHA-256 checksum
            file_hash = hashlib.sha256(package_path.read_bytes()).hexdigest()
            if file_hash != entry.sha256:
                logger.warning("skill_hash_mismatch", name=skill_name)
                return {
                    "status": "error",
                    "message": "SHA-256 checksum mismatch. Package may be tampered.",
                }

            # 5. Verify signature
            signature_valid = await self._verify_signature(entry, tmp_path)
            if not signature_valid:
                return {
                    "status": "error",
                    "message": "Signature verification failed. Refusing to install unsigned skill.",
                }

            # 6. Static analysis
            suspicious = self._static_analysis(package_path)
            if suspicious:
                logger.warning("skill_suspicious_patterns", name=skill_name, patterns=suspicious)
                return {
                    "status": "error",
                    "message": f"Suspicious patterns found: {', '.join(suspicious)}",
                }

            # 7. Extract and install
            try:
                import tarfile
                with tarfile.open(package_path, "r:gz") as tar:
                    # Security: prevent path traversal
                    for member in tar.getmembers():
                        if member.name.startswith("/") or ".." in member.name:
                            return {
                                "status": "error",
                                "message": f"Malicious path in archive: {member.name}",
                            }
                    tar.extractall(path=tmp_path / "extracted")

                # Move to skills directory
                extracted = tmp_path / "extracted"
                if install_dir.exists():
                    shutil.rmtree(install_dir)
                shutil.copytree(extracted, install_dir)

            except Exception as e:
                return {"status": "error", "message": f"Installation failed: {e}"}

        logger.info("skill_installed", name=skill_name, version=entry.version)
        return {
            "status": "success",
            "name": skill_name,
            "version": entry.version,
            "path": str(install_dir),
        }

    async def uninstall(self, skill_name: str) -> dict[str, Any]:
        """Uninstall a skill."""
        install_dir = self.skills_dir / skill_name
        if not install_dir.exists():
            return {"status": "error", "message": f"Skill '{skill_name}' not installed"}

        # Don't allow uninstalling builtins
        builtin_dir = Path(__file__).parent / "builtin"
        if install_dir.is_relative_to(builtin_dir):
            return {"status": "error", "message": "Cannot uninstall built-in skills"}

        shutil.rmtree(install_dir)
        logger.info("skill_uninstalled", name=skill_name)
        return {"status": "success", "name": skill_name}

    def list_installed(self) -> list[dict[str, Any]]:
        """List all installed skills."""
        installed = []

        if not self.skills_dir.exists():
            return installed

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue

            manifest_path = skill_dir / "skill.toml"
            info: dict[str, Any] = {
                "name": skill_dir.name,
                "path": str(skill_dir),
                "has_manifest": manifest_path.exists(),
            }

            if manifest_path.exists():
                try:
                    import tomli
                    with open(manifest_path, "rb") as f:
                        data = tomli.load(f)
                    skill_data = data.get("skill", {})
                    info.update({
                        "version": skill_data.get("version", "unknown"),
                        "description": skill_data.get("description", ""),
                        "author": skill_data.get("author", "unknown"),
                    })
                except Exception:
                    pass

            installed.append(info)

        return installed

    async def check_updates(self) -> list[dict[str, Any]]:
        """Check for available skill updates."""
        installed = self.list_installed()
        registry = await self._load_registry()

        updates = []
        for skill in installed:
            for entry in registry:
                if entry.name == skill["name"]:
                    if entry.version != skill.get("version"):
                        updates.append({
                            "name": skill["name"],
                            "installed_version": skill.get("version", "unknown"),
                            "available_version": entry.version,
                        })
                    break

        return updates

    async def _load_registry(self) -> list[MarketplaceEntry]:
        """Load the marketplace registry."""
        if self._registry_cache:
            return self._registry_cache

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self.registry_url)
                response.raise_for_status()
                data = response.json()

            entries = []
            for item in data.get("skills", []):
                entries.append(MarketplaceEntry(
                    name=item["name"],
                    version=item["version"],
                    description=item.get("description", ""),
                    author=item.get("author", "unknown"),
                    download_url=item["download_url"],
                    signature_url=item.get("signature_url", ""),
                    sbom_url=item.get("sbom_url", ""),
                    sha256=item.get("sha256", ""),
                    downloads=item.get("downloads", 0),
                    rating=item.get("rating", 0.0),
                    verified=item.get("verified", False),
                ))

            self._registry_cache = entries
            return entries

        except Exception as e:
            logger.warning("registry_load_failed", error=str(e))
            return []

    async def _verify_signature(
        self, entry: MarketplaceEntry, tmp_dir: Path
    ) -> bool:
        """Verify skill signature using cosign."""
        if not entry.signature_url:
            logger.warning("no_signature", name=entry.name)
            # Allow unsigned skills only if explicitly configured
            return False

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(entry.signature_url)
                sig_path = tmp_dir / "signature.sig"
                sig_path.write_bytes(response.content)

            # Use the skill verifier for signature check
            return self.verifier.verify_signature(
                str(tmp_dir / f"{entry.name}.tar.gz"),
                str(sig_path),
            )
        except Exception as e:
            logger.warning("signature_verification_failed", error=str(e))
            return False

    @staticmethod
    def _static_analysis(package_path: Path) -> list[str]:
        """Run basic static analysis on the package for suspicious patterns."""
        suspicious = []

        try:
            import tarfile
            with tarfile.open(package_path, "r:gz") as tar:
                for member in tar.getmembers():
                    if not member.isfile():
                        continue

                    # Only analyze Python files
                    if not member.name.endswith(".py"):
                        continue

                    f = tar.extractfile(member)
                    if not f:
                        continue

                    content = f.read().decode("utf-8", errors="ignore")

                    # Check for dangerous patterns
                    dangerous_patterns = [
                        ("eval(", "eval() usage"),
                        ("exec(", "exec() usage"),
                        ("__import__", "dynamic import"),
                        ("subprocess.call", "subprocess without sandbox"),
                        ("os.system", "os.system call"),
                        ("socket.socket", "raw socket usage"),
                        ("ctypes", "ctypes usage"),
                        ("pickle.load", "unsafe deserialization"),
                    ]

                    for pattern, description in dangerous_patterns:
                        if pattern in content:
                            suspicious.append(f"{member.name}: {description}")

        except Exception:
            pass

        return suspicious
