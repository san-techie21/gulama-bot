<p align="center">
  <img src="media/Gulama.png" alt="Gulama" width="180"/>
</p>

<h1 align="center">Gulama</h1>

<p align="center">
  <strong>Your personal AI agent — that actually keeps your data safe.</strong>
</p>

<p align="center">
  <a href="https://github.com/san-techie21/gulama-bot/actions"><img src="https://github.com/san-techie21/gulama-bot/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="https://pypi.org/project/gulama/"><img src="https://img.shields.io/pypi/v/gulama.svg" alt="PyPI"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"/></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.12+-green.svg" alt="Python 3.12+"/></a>
  <img src="https://img.shields.io/badge/Security-15%2B%20mechanisms-red.svg" alt="Security"/>
  <img src="https://img.shields.io/badge/Skills-19%20built--in-orange.svg" alt="19 Skills"/>
  <img src="https://img.shields.io/badge/LLM_Providers-100%2B-purple.svg" alt="100+ LLM Providers"/>
</p>

<p align="center">
  <a href="#-get-started-in-60-seconds">Quick Start</a> •
  <a href="#-19-built-in-skills">Skills</a> •
  <a href="#-10-communication-channels">Channels</a> •
  <a href="#-security-architecture">Security</a> •
  <a href="#-gulama-vs-openclaw">Compare</a> •
  <a href="https://pypi.org/project/gulama/">PyPI</a> •
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

---

https://github.com/user-attachments/assets/62e4d1b3-ed0c-4302-9fb9-f4cecf201833

---

Personal AI agents handle your files, emails, credentials, and conversations. Most treat security as an afterthought. **Gulama is built security-first from the ground up** — with 15+ security mechanisms, 19 skills, 10 communication channels, and support for 100+ LLM providers.

> **One agent. Any LLM. Actually secure.**

### Why Gulama?

- 🔒 **Security-first** — AES-256-GCM encryption, sandboxed execution, prompt injection detection, and 12 more mechanisms baked into the core, not bolted on later
- 🧩 **Any LLM** — Anthropic, OpenAI, Google, DeepSeek, Ollama (local), and 100+ more via LiteLLM. Never locked to one vendor
- 🛠 **19 skills** — Files, shell, web, browser, email, calendar, voice, GitHub, Notion, Spotify, and more. Plus a signed skill marketplace
- 📡 **10 channels** — CLI, Telegram, Discord, Slack, WhatsApp, Matrix (E2E), Teams, Google Chat, Web UI, Voice Wake
- 🎛 **Your rules** — 5 autonomy levels from "ask before everything" to "autopilot"
- 🏠 **Self-hosted** — Runs on your machine. Your data never leaves your infrastructure
- 🐧 **Cross-platform** — macOS, Windows, Linux, Docker, ARM (Raspberry Pi)

---

## 🚀 Get Started in 60 Seconds

### Prerequisites

- **Python 3.12+** ([download](https://python.org))
- An API key from any LLM provider (OpenAI, Anthropic, DeepSeek, etc.) — or use [Ollama](https://ollama.ai) for free local models

### Install

```bash
pip install gulama
```

Or install with all optional features (voice, browser automation, image generation):

```bash
pip install gulama[full]
```

### First-Time Setup

```bash
gulama setup
```

The interactive setup wizard walks you through:

1. **Create a master password** — All your credentials are encrypted with AES-256-GCM. This password unlocks them. Choose something strong.
2. **Pick your LLM provider** — Choose from Anthropic, OpenAI, Google, DeepSeek, Qwen, Groq, Together AI, Ollama, or any OpenAI-compatible endpoint.
3. **Enter your API key** — Encrypted and stored in the local secrets vault. Never stored in plaintext.
4. **Set your autonomy level** — How much freedom should Gulama have? (Default: Level 2 — Co-pilot)
5. **Optional: Connect channels** — Set up Telegram, Discord, or other messaging channels.

### Start Chatting

```bash
gulama chat
```

That's it. You now have a secure AI assistant with access to 19 skills.

### Other Commands

```bash
gulama start                     # Start the gateway server (REST API + WebSocket)
gulama start --channel telegram  # Start with a specific channel
gulama start --channel discord
gulama start --voice-wake        # Always-on voice mode ("Hey Gulama")
gulama status                    # Show agent health and status
gulama doctor                    # Run security health check
gulama config                    # Show or edit configuration
gulama vault list                # List stored secrets
gulama version                   # Show version info
```

### Docker

```bash
# Standard deployment
docker compose up -d

# With Redis (caching) + ChromaDB (vector search)
docker compose --profile full up -d

# Cloud deployment with auto-TLS via Caddy
docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d
```

---

## 🛠 19 Built-In Skills

Gulama ships with 19 skills out of the box. Each skill runs in a security sandbox with policy-engine authorization.

| | Skill | What it does | Service / API |
|---|-------|-------------|---------------|
| 📁 | **File Manager** | Read, write, search, and organize files | Local filesystem |
| 💻 | **Shell Exec** | Execute shell commands in a sandboxed environment | OS shell (bubblewrap/Docker) |
| 🌐 | **Web Search** | Search the web and fetch page content | DuckDuckGo / SearXNG |
| 🧠 | **Notes** | Save and recall facts, preferences, and context | Encrypted local memory |
| ⚡ | **Code Exec** | Run Python, JavaScript, or Bash code snippets | Sandboxed runtime |
| 🖥️ | **Browser** | Navigate websites, take screenshots, AI-assisted browsing | Playwright + browser-use |
| 📧 | **Email** | Read inbox, compose, and send emails | IMAP / SMTP |
| 📅 | **Calendar** | Create, view, and manage events and schedules | Google Calendar / CalDAV |
| 🔌 | **MCP Bridge** | Connect to any Model Context Protocol server | MCP |
| 🎤 | **Voice** | Speech-to-text and text-to-speech | Whisper / Deepgram / ElevenLabs |
| 🎨 | **Image Gen** | Generate images from text descriptions | DALL-E / Stability AI / Replicate |
| 🏠 | **Smart Home** | Control lights, switches, and IoT devices | Home Assistant |
| 🐙 | **GitHub** | Manage repos, issues, PRs, and search code | GitHub API |
| 📝 | **Notion** | Create and search pages, manage databases | Notion API |
| 🎵 | **Spotify** | Play music, search tracks, manage playlists | Spotify Web API |
| 🐦 | **Twitter/X** | Search tweets, view user profiles and trends | Twitter API v2 |
| 📊 | **Google Docs** | Read and write Docs, Sheets, and Drive files | Google Workspace APIs |
| ✅ | **Productivity** | Manage tasks and notes across multiple tools | Trello, Linear, Todoist, Obsidian |
| 🤖 | **Self-Modify** | The AI writes its own new skills at runtime | Runtime skill authoring (sandboxed) |

> 💡 **Need more?** Install community skills from [GulamaHub](#-gulamahub--skill-marketplace), or let Gulama write its own.

---

## 📡 10 Communication Channels

Talk to Gulama from wherever you already are:

| Channel | Protocol | Notes |
|---------|----------|-------|
| **CLI** | Interactive terminal | Zero setup — works immediately |
| **Telegram** | Bot API | Create a bot via @BotFather, add token to vault |
| **Discord** | discord.py | Create an app on Discord Developer Portal |
| **Slack** | Slack SDK + Webhooks | Create a Slack app, add bot/app tokens |
| **WhatsApp** | Cloud API | Requires Meta Business account |
| **Matrix** | matrix-nio | End-to-end encrypted by default |
| **Microsoft Teams** | Bot Framework | Register bot in Azure portal |
| **Google Chat** | Workspace webhooks | Google Workspace admin required |
| **Web UI** | React + WebSocket | Built-in web interface (in `web/` directory) |
| **Voice Wake** | Picovoice + STT/TTS | Always-on "Hey Gulama" wake word listener |

### Connecting a Channel

Channels are configured by adding tokens to the secrets vault:

```bash
# Example: Connect Telegram
gulama vault set TELEGRAM_BOT_TOKEN "your-bot-token-here"
gulama start --channel telegram

# Example: Connect Discord
gulama vault set DISCORD_BOT_TOKEN "your-bot-token-here"
gulama start --channel discord
```

See `.env.example` for all supported environment variables and token names.

---

## 🧩 100+ LLM Providers

Gulama uses [LiteLLM](https://github.com/BerriAI/litellm) under the hood, giving you access to any LLM:

| Provider | Example Models | Notes |
|----------|---------------|-------|
| **Anthropic** | Claude Sonnet 4, Opus, Haiku | Default provider |
| **OpenAI** | GPT-4o, o1, o3-mini | Most popular |
| **Google** | Gemini 2.0 Flash, Pro | Free tier available |
| **DeepSeek** | DeepSeek Chat, Reasoner | Cost-effective |
| **Alibaba** | Qwen Plus, Max, Turbo | Chinese LLM support |
| **Groq** | Llama 3.3, Mixtral | Fastest inference |
| **Ollama** | Llama, Mistral, Phi, Qwen | **Free, runs locally** |
| **Together AI** | Llama, Mistral, and more | GPU cloud |
| **AWS Bedrock** | All Bedrock models | Enterprise AWS |
| **Azure OpenAI** | All Azure-hosted models | Enterprise Azure |
| **90+ more** | Any OpenAI-compatible endpoint | Custom API base URL |

### Switching Providers

```bash
# During setup
gulama setup    # Select provider interactively

# Or edit config directly
gulama config
```

In `~/.gulama/config.toml`:

```toml
[llm]
provider = "openai"          # or "anthropic", "deepseek", "ollama", etc.
model = "gpt-4o"
api_key_name = "LLM_API_KEY" # Key stored in encrypted vault

[llm.fallback]
provider = "deepseek"        # Automatic fallback when primary fails
model = "deepseek-chat"
```

### Using Local Models (Ollama)

Run LLMs completely offline — no API key needed:

```bash
# Install Ollama (https://ollama.ai)
ollama pull llama3.3

# Configure Gulama to use it
# In config.toml:
# [llm]
# provider = "ollama"
# model = "llama3.3"

gulama chat
```

---

## 🔒 Security Architecture

This is where Gulama is fundamentally different. Security isn't a feature — it's the foundation. **15+ mechanisms are built into the core:**

| Mechanism | What it does | Why it matters |
|-----------|-------------|----------------|
| **AES-256-GCM encryption** | All credentials and memories encrypted at rest | Your API keys and conversations are never stored in plaintext |
| **Sandboxed execution** | Every tool runs in bubblewrap/Docker/OS sandbox | A malicious skill can't access your filesystem or network |
| **Policy engine** | Cedar-inspired deterministic authorization rules | Fine-grained control over what each skill can do |
| **Canary tokens** | Invisible markers detect prompt injection attacks | Catches manipulated prompts before they execute |
| **Hash-chain audit** | Every action logged with cryptographic chain | Tamper-proof audit trail — detect if logs are modified |
| **Egress filtering + DLP** | Controls outbound network and prevents data leaks | Stops credential exfiltration and sensitive data exposure |
| **Signed skills** | Ed25519 signature verification for all GulamaHub skills | Prevents supply-chain attacks (no unsigned code runs) |
| **TOTP authentication** | Time-based one-time passwords for API access | Two-factor auth for the gateway API |
| **Rate limiting** | Per-IP request throttling | Prevents brute-force and DoS attacks |
| **Input validation** | Content scanning and sanitization | Blocks injection attacks and malformed input |
| **Loopback binding** | Gateway binds `127.0.0.1` only by default | Never accidentally exposed to the internet |
| **Threat detection** | Monitors for brute force, privilege escalation, anomalies | Active protection against ongoing attacks |
| **RBAC** | Role-based access control with team management | Different permissions for different users |
| **SSO/API keys** | OIDC, SAML, API key authentication | Enterprise-grade identity management |
| **Security headers** | HSTS, CSP, X-Frame-Options on all responses | Protection against web-based attacks |

### Security Health Check

```bash
gulama doctor
```

Runs a comprehensive security audit and reports on encryption status, sandbox health, policy engine, and potential vulnerabilities.

```bash
gulama doctor --json-output    # Machine-readable output for CI/CD
```

---

## 🏪 GulamaHub — Skill Marketplace

Install community-built skills from GulamaHub. Unlike other agent platforms, **every skill must be Ed25519-signed**. No exceptions — no unsigned code runs on your machine.

```bash
# Search for skills
gulama hub search "weather"

# Install a skill (signature verified automatically)
gulama hub install weather-checker

# Publish your own skill (signing required)
gulama hub publish my-skill --sign
```

The agent can also **write its own skills** at runtime via the Self-Modify skill. New skills are automatically sandboxed and security-scanned before activation.

---

## 🎛 Autonomy Levels

Control how much independence Gulama has. Set during `gulama setup` or change anytime in config:

| Level | Name | What it does | Best for |
|:-----:|------|-------------|----------|
| 0 | **Observer** | Asks permission before every single action | Maximum control, learning the tool |
| 1 | **Assistant** | Auto-reads files/web, asks before any writes | Cautious daily use |
| 2 | **Co-pilot** | Auto-reads and writes safe actions, asks before shell/network | **Default — recommended for most users** |
| 3 | **Autopilot-cautious** | Auto-executes most tasks, asks before destructive operations | Power users who trust the security layer |
| 4 | **Autopilot** | Auto-executes everything except financial/credential operations | Unattended automation |

```toml
# In ~/.gulama/config.toml
[autonomy]
default_level = 2    # Change this to your preferred level
```

---

## ⚙️ Configuration

Gulama loads configuration from multiple sources (in priority order):

| Priority | Source | Purpose |
|:--------:|--------|---------|
| 1 | `config/default.toml` | Secure defaults (ships with Gulama) |
| 2 | `~/.gulama/config.toml` | Your personal overrides |
| 3 | Environment variables (`GULAMA_*`) | Container/CI overrides |
| 4 | `.env` file | Secrets (see `.env.example`) |

### Key Settings

```toml
# ~/.gulama/config.toml

[gateway]
host = "127.0.0.1"     # Loopback only — safe default
port = 18789

[llm]
provider = "anthropic"
model = "claude-sonnet-4-5-20250929"
max_tokens = 4096
temperature = 0.7
daily_token_budget = 500000    # ~$2.50/day at Sonnet pricing

[security]
sandbox_enabled = true          # Requires --i-know-what-im-doing to disable
policy_engine_enabled = true
canary_tokens_enabled = true
egress_filtering_enabled = true
audit_logging_enabled = true
skill_signature_required = true

[memory]
encryption_algorithm = "aes-256-gcm"
vector_store = "chromadb"
max_context_tokens = 8000

[cost]
daily_budget_usd = 2.50
alert_threshold_percent = 80   # Alert at 80% of daily budget

[autonomy]
default_level = 2
```

### Security Defaults

These settings are **enabled by default** and require `--i-know-what-im-doing` flag to disable:

- Gateway binds to `127.0.0.1` only (never `0.0.0.0`)
- Sandbox execution for all tools
- Policy engine authorization
- Canary token injection detection
- Egress filtering and DLP
- Audit logging with hash-chain
- Skill signature verification

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Channels (10)                           │
│  CLI · Telegram · Discord · Slack · WhatsApp · Matrix    │
│  Teams · Google Chat · Web UI · Voice Wake               │
├──────────────────────────────────────────────────────────┤
│              Gateway (FastAPI) — 29 Routes                │
│  TOTP Auth · Rate Limit · CORS · Security Headers        │
├──────────────────────────────────────────────────────────┤
│                    Agent Brain                            │
│  Context Builder (RAG) · LLM Router · Tool Calling       │
│  Sub-Agent Manager · Task Scheduler                      │
├──────────────────────────────────────────────────────────┤
│               Security Layer (15+)                        │
│  Policy · Sandbox · Canary · Audit · DLP · Egress        │
│  RBAC · SSO · Threat Detection · Input Validation        │
├──────────────────────────────────────────────────────────┤
│            Skills (19 Built-in + GulamaHub)               │
├──────────────────────────────────────────────────────────┤
│                   Storage Layer                           │
│  Encrypted SQLite · ChromaDB (RAG) · Secrets Vault       │
│  Hash-Chain Audit · Disk Cache                           │
├──────────────────────────────────────────────────────────┤
│                 Debug & Monitoring                         │
│  WebSocket Debug Stream · Cost Tracking · Token Budgets  │
└──────────────────────────────────────────────────────────┘
```

### REST API

Gulama exposes **29 REST endpoints** and **2 WebSocket channels** via the FastAPI gateway:

<details>
<summary><b>View all endpoints</b></summary>

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/chat` | POST | Send a message to the agent |
| `/api/v1/status` | GET | Agent status, health, and statistics |
| `/api/v1/skills` | GET | List all registered skills |
| `/api/v1/agents` | GET | List running background sub-agents |
| `/api/v1/agents/spawn` | POST | Spawn a new background agent |
| `/api/v1/scheduler/tasks` | GET | List scheduled/cron tasks |
| `/api/v1/hub/search` | GET | Search the skill marketplace |
| `/api/v1/conversations` | GET | List conversation history |
| `/api/v1/audit` | GET | View the tamper-proof audit log |
| `/api/v1/cost/today` | GET | Today's token usage and cost |
| `/api/v1/debug/events` | GET | Debug event stream |
| `/ws/chat` | WebSocket | Real-time chat (bidirectional) |
| `/ws/debug` | WebSocket | Live debug inspector |

**Base URL:** `http://localhost:18789`

</details>

---

## 🆚 Gulama vs OpenClaw

| Feature | Gulama | OpenClaw |
|---------|--------|----------|
| Security mechanisms | **15+ built into core** | ~0 (security as afterthought) |
| Memory encryption | **AES-256-GCM** | None (plaintext) |
| Skill signing | **Ed25519 mandatory** | None (341 malicious skills found) |
| LLM providers | **100+** via LiteLLM | ~5 |
| Policy engine | **Cedar-inspired** | None |
| Sandbox | **bubblewrap/Docker/OS** | Container-only |
| Audit trail | **Cryptographic hash-chain** | Basic logs |
| Prompt injection defense | **Canary tokens** | None |
| Cost controls | **Per-day budgets + alerts** | None |
| Self-modifying skills | **Yes (sandboxed + scanned)** | No |
| Egress filtering | **Built-in DLP** | None |
| License | MIT | MIT |

---

## 📦 Deployment

| Method | Command | Use Case |
|--------|---------|----------|
| **pip install** | `pip install gulama` | Local development, personal use |
| **pip (full)** | `pip install gulama[full]` | All features (voice, browser, images) |
| **Docker** | `docker compose up -d` | Self-hosted server |
| **Docker (full)** | `docker compose --profile full up -d` | With Redis + ChromaDB |
| **Cloud** | `docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d` | DigitalOcean / AWS / GCP |

The cloud deployment includes auto-TLS via Caddy reverse proxy.

---

## 🧑‍💻 Development

```bash
# Clone the repo
git clone https://github.com/san-techie21/gulama-bot.git
cd gulama-bot

# Install in development mode
pip install -e ".[dev]"

# Run the test suite (277 tests)
python -m pytest tests/ -v

# Run security-specific tests
python -m pytest tests/security/ -v

# Lint
ruff check src/

# Security health check
gulama doctor --json-output
```

### Project Structure

```
src/
├── agent/       # Brain, LLM router, context builder, tool executor
├── channels/    # CLI, Telegram, Discord, Slack, WhatsApp, Matrix, Teams
├── cli/         # Click commands, setup wizard
├── gateway/     # FastAPI app, auth, middleware, WebSocket, routes
├── memory/      # Encrypted store, schema, vector search
├── security/    # Policy engine, sandbox, canary, audit, DLP, egress
├── skills/      # Registry + 19 built-in skills
└── utils/       # Logging, platform detection
config/          # Default TOML configuration
deploy/          # Docker Compose, Caddy, cloud configs
tests/           # 277 tests (unit + integration + security)
web/             # React + Vite web UI
```

---

## 📜 License

MIT — see [LICENSE](LICENSE).

## 🔐 Security Policy

Found a vulnerability? Please report it responsibly via [GitHub Issues](https://github.com/san-techie21/gulama-bot/issues) with the `security` label.

---

<p align="center">
  Built with 15+ years of security industry expertise.<br/><br/>
  <a href="https://github.com/san-techie21/gulama-bot">⭐ Star on GitHub</a> ·
  <a href="https://pypi.org/project/gulama/">📦 PyPI</a> ·
  <a href="https://www.linkedin.com/in/santechie21">💼 LinkedIn</a> ·
  <a href="CONTRIBUTING.md">🤝 Contribute</a>
</p>
