"""Cross-platform detection utilities for Gulama."""

import os
import platform
import shutil
from enum import Enum


class OSType(str, Enum):
    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


class SandboxBackend(str, Enum):
    BUBBLEWRAP = "bubblewrap"
    GVISOR = "gvisor"
    APPLE_SANDBOX = "apple_sandbox"
    WINDOWS_SANDBOX = "windows_sandbox"
    DOCKER = "docker"
    PROCESS = "process"  # Fallback: subprocess with resource limits


def detect_os() -> OSType:
    """Detect the current operating system."""
    system = platform.system()
    match system:
        case "Linux":
            return OSType.LINUX
        case "Darwin":
            return OSType.MACOS
        case "Windows":
            return OSType.WINDOWS
        case _:
            return OSType.UNKNOWN


def detect_architecture() -> str:
    """Detect CPU architecture."""
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "x86_64"
    elif machine in ("aarch64", "arm64"):
        return "arm64"
    elif machine.startswith("arm"):
        return "arm"
    return machine


def detect_best_sandbox() -> SandboxBackend:
    """Detect the best available sandbox backend for the current OS."""
    current_os = detect_os()

    match current_os:
        case OSType.LINUX:
            if shutil.which("bwrap"):
                return SandboxBackend.BUBBLEWRAP
            if shutil.which("runsc"):
                return SandboxBackend.GVISOR
            if shutil.which("docker"):
                return SandboxBackend.DOCKER
            return SandboxBackend.PROCESS

        case OSType.MACOS:
            if shutil.which("sandbox-exec"):
                return SandboxBackend.APPLE_SANDBOX
            if shutil.which("docker"):
                return SandboxBackend.DOCKER
            return SandboxBackend.PROCESS

        case OSType.WINDOWS:
            # Check for Windows Sandbox (only on Pro/Enterprise)
            if _is_windows_sandbox_available():
                return SandboxBackend.WINDOWS_SANDBOX
            if shutil.which("docker"):
                return SandboxBackend.DOCKER
            return SandboxBackend.PROCESS

        case _:
            if shutil.which("docker"):
                return SandboxBackend.DOCKER
            return SandboxBackend.PROCESS


def _is_windows_sandbox_available() -> bool:
    """Check if Windows Sandbox feature is available."""
    if detect_os() != OSType.WINDOWS:
        return False
    try:
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command", "Get-WindowsOptionalFeature -Online -FeatureName Containers-DisposableClientVM"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return "Enabled" in result.stdout
    except Exception:
        return False


def get_data_dir() -> str:
    """Get the platform-appropriate data directory path."""
    from src.constants import DATA_DIR
    return str(DATA_DIR)


def is_wsl() -> bool:
    """Check if running in Windows Subsystem for Linux."""
    if detect_os() != OSType.LINUX:
        return False
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except Exception:
        return False


def get_keyring_backend() -> str:
    """Detect the best keyring backend for the current OS."""
    current_os = detect_os()
    match current_os:
        case OSType.MACOS:
            return "macOS Keychain"
        case OSType.LINUX:
            return "Secret Service (GNOME Keyring / KDE Wallet)"
        case OSType.WINDOWS:
            return "Windows Credential Manager"
        case _:
            return "file-based (encrypted)"
