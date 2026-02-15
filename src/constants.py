"""Project-wide constants for Gulama."""

import platform
import sys
from pathlib import Path

PROJECT_NAME = "gulama"
PROJECT_DISPLAY_NAME = "Gulama"
PROJECT_DESCRIPTION = "Secure, open-source personal AI agent platform"
PROJECT_VERSION = "0.1.0"
PROJECT_URL = "https://gulama.ai"
PROJECT_REPO = "https://github.com/san-techie21/gulama-bot"
PROJECT_LICENSE = "MIT"

# Default network config — LOOPBACK ONLY, never 0.0.0.0
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18789

# Platform detection
SYSTEM = platform.system()  # "Linux", "Darwin", "Windows"
IS_LINUX = SYSTEM == "Linux"
IS_MACOS = SYSTEM == "Darwin"
IS_WINDOWS = SYSTEM == "Windows"
IS_ARM = platform.machine() in ("aarch64", "arm64", "armv7l")

# Data directories (cross-platform)
if IS_WINDOWS:
    _appdata = Path(platform.os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    DATA_DIR = _appdata / PROJECT_NAME
else:
    DATA_DIR = Path.home() / f".{PROJECT_NAME}"

CONFIG_FILE = DATA_DIR / "config.toml"
VAULT_FILE = DATA_DIR / "vault.age"
MEMORY_DB = DATA_DIR / "memory.db"
CHROMA_DIR = DATA_DIR / "chroma"
AUDIT_DIR = DATA_DIR / "audit"
SKILLS_DIR = DATA_DIR / "skills"
LOGS_DIR = DATA_DIR / "logs"
CACHE_DIR = DATA_DIR / "cache"

# Security constants
MAX_CONTEXT_TOKENS = 8000
DEFAULT_AUTONOMY_LEVEL = 2
DEFAULT_DAILY_TOKEN_BUDGET = 500_000

# Sensitive path patterns — NEVER allow access
SENSITIVE_PATHS = [
    ".ssh",
    ".gnupg",
    ".aws",
    ".azure",
    ".gcloud",
    ".env",
    "credentials",
    ".gitconfig",
    "vault.age",
    "id_rsa",
    "id_ed25519",
    ".npmrc",
    ".pypirc",
]

# Sensitive content patterns — NEVER log or expose
SENSITIVE_PATTERNS = [
    r"sk-[a-zA-Z0-9\-]{20,}",          # OpenAI keys (including sk-proj-...)
    r"sk-ant-[a-zA-Z0-9\-]{20,}",     # Anthropic keys
    r"AIza[a-zA-Z0-9\-_]{35}",        # Google API keys
    r"ghp_[a-zA-Z0-9]{36}",           # GitHub tokens
    r"glpat-[a-zA-Z0-9\-]{20}",       # GitLab tokens
    r"xox[bpas]-[a-zA-Z0-9\-]+",      # Slack tokens
    r"-----BEGIN.*PRIVATE KEY-----",    # Private keys
    r"[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}",  # Credit cards
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Emails (for DLP)
    r"AKIA[0-9A-Z]{16}",              # AWS access key IDs
    r"AWS_SECRET_ACCESS_KEY\s*=\s*\S+",  # AWS secret access keys
    r"AWS_ACCESS_KEY_ID\s*=\s*\S+",    # AWS access key ID in env format
    r"AZURE_[A-Z_]*KEY\s*=\s*\S+",    # Azure keys
    r"gcp_[a-zA-Z0-9\-_]{20,}",       # GCP credentials
]
