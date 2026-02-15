#!/usr/bin/env bash
# Gulama Bot — Linux/macOS Install Script
# Usage: curl -fsSL https://gulama.ai/install.sh | bash
# Or:    bash scripts/install.sh
set -euo pipefail

GULAMA_VERSION="0.1.0"
GULAMA_MIN_PYTHON="3.12"
INSTALL_DIR="${HOME}/.local"
VENV_DIR="${HOME}/.gulama/venv"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

echo ""
echo -e "${GREEN}╔══════════════════════════════════╗${NC}"
echo -e "${GREEN}║    Gulama Bot Installer v${GULAMA_VERSION}   ║${NC}"
echo -e "${GREEN}║    Secure AI Agent Platform      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════╝${NC}"
echo ""

# --- Check OS ---
OS="$(uname -s)"
ARCH="$(uname -m)"
info "Detected: ${OS} ${ARCH}"

case "${OS}" in
    Linux*)  PLATFORM="linux" ;;
    Darwin*) PLATFORM="macos" ;;
    *)       error "Unsupported OS: ${OS}. Use Docker instead: docker compose up" ;;
esac

# --- Check Python ---
check_python() {
    for cmd in python3.13 python3.12 python3; do
        if command -v "${cmd}" &> /dev/null; then
            version=$("${cmd}" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)
            if [ "$major" -ge 3 ] && [ "$minor" -ge 12 ]; then
                PYTHON_CMD="${cmd}"
                ok "Python ${version} found: $(command -v "${cmd}")"
                return 0
            fi
        fi
    done
    return 1
}

if ! check_python; then
    error "Python >= ${GULAMA_MIN_PYTHON} required. Install from https://python.org"
fi

# --- Install system dependencies ---
install_deps() {
    if [ "${PLATFORM}" = "linux" ]; then
        if command -v apt-get &> /dev/null; then
            info "Installing bubblewrap (sandbox) via apt..."
            sudo apt-get update -qq && sudo apt-get install -y -qq bubblewrap
        elif command -v dnf &> /dev/null; then
            info "Installing bubblewrap (sandbox) via dnf..."
            sudo dnf install -y bubblewrap
        elif command -v pacman &> /dev/null; then
            info "Installing bubblewrap (sandbox) via pacman..."
            sudo pacman -S --noconfirm bubblewrap
        else
            warn "Could not install bubblewrap automatically. Install it manually for sandbox support."
        fi
    fi
}

# Only install system deps if running as installer (not from source)
if [ ! -f "pyproject.toml" ]; then
    install_deps
fi

# --- Create virtual environment ---
info "Creating virtual environment at ${VENV_DIR}..."
mkdir -p "$(dirname "${VENV_DIR}")"
"${PYTHON_CMD}" -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"
ok "Virtual environment created"

# --- Install Gulama ---
info "Installing Gulama..."
pip install --upgrade pip --quiet
pip install gulama --quiet 2>/dev/null || {
    # If PyPI package not available, install from source
    if [ -f "pyproject.toml" ]; then
        info "Installing from source..."
        pip install -e ".[dev]" --quiet
    else
        error "Could not install gulama. Package not yet published to PyPI."
    fi
}
ok "Gulama installed"

# --- Add to PATH ---
SHELL_RC=""
if [ -n "${ZSH_VERSION:-}" ] || [ -f "${HOME}/.zshrc" ]; then
    SHELL_RC="${HOME}/.zshrc"
elif [ -f "${HOME}/.bashrc" ]; then
    SHELL_RC="${HOME}/.bashrc"
elif [ -f "${HOME}/.bash_profile" ]; then
    SHELL_RC="${HOME}/.bash_profile"
fi

VENV_BIN="${VENV_DIR}/bin"
if [ -n "${SHELL_RC}" ]; then
    if ! grep -q "gulama/venv/bin" "${SHELL_RC}" 2>/dev/null; then
        echo "" >> "${SHELL_RC}"
        echo "# Gulama Bot" >> "${SHELL_RC}"
        echo "export PATH=\"${VENV_BIN}:\$PATH\"" >> "${SHELL_RC}"
        info "Added ${VENV_BIN} to PATH in ${SHELL_RC}"
    fi
fi

# --- Verify ---
if command -v gulama &> /dev/null || "${VENV_BIN}/gulama" --version &> /dev/null; then
    ok "Gulama installed successfully!"
else
    warn "Gulama installed but may not be in PATH. Run: source ${SHELL_RC}"
fi

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Run initial setup:  gulama setup"
echo "  2. Start chatting:     gulama chat"
echo "  3. Start the server:   gulama start"
echo ""
echo "For Docker:  docker compose up -d"
echo "For help:    gulama --help"
echo ""
