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

<div align="center">

https://github.com/user-attachments/assets/62e4d1b3-ed0c-4302-9fb9-f4cecf201833

</div>

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

### Built for the Modern AI Stack

- 🔌 **MCP Server & Client** — Full [Model Context Protocol](https://modelcontextprotocol.io/) support. Connect Gulama to Claude Desktop, Cursor, Windsurf, or any MCP-compatible tool — and expose Gulama's skills as an MCP server for other agents to use
- 🤖 **Multi-Agent Orchestration** — Spawn background sub-agents for parallel task execution. Each sub-agent gets its own brain, memory, and tools. Real multi-agent, not just parallel tool calls
- ⏰ **Built-in Task Scheduler** — Native cron scheduling with interval and one-time tasks. Run daily summaries, periodic cleanups, health checks — no external cron system needed
- 🎤 **Voice Wake Word** — Always-on "Hey Gulama" listening via Picovoice. Detects the wake word, captures speech, processes via STT, responds via TTS — a true voice assistant
- 🧠 **RAG-Powered Memory** — ChromaDB vector search retrieves only relevant memories (not full conversation dumps). Semantic similarity across messages, facts, and conversations — respects token budgets
- 🌐 **AI-Powered Browser** — Dual-mode web automation: low-level Playwright control + high-level natural language browsing via browser-use. "Research this topic" just works
- ✍️ **Self-Modifying Agent** — Gulama writes its own new skills at runtime. Code is security-scanned, sandboxed, and persisted across restarts. The agent evolves with your needs
- 🔍 **Live Debug Stream** — Real-time WebSocket inspector shows tool calls, policy decisions, token usage, memory operations, and sub-agent activity as they happen

---

## 🚀 Get Started in 60 Seconds

### Step 1: Install Python

You need Python 3.12 or newer. Check if you already have it:

```bash
python --version
```

If you see `Python 3.12.x` or higher, you're good — skip to Step 2. Otherwise:

<details>
<summary><b>How to install Python (click to expand)</b></summary>

**Windows:**
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the latest Python 3.12+ installer
3. **Important:** Check the box that says **"Add Python to PATH"** before clicking Install
4. Open a new Command Prompt or PowerShell window after installation

**macOS:**
```bash
brew install python@3.12
```
Or download from [python.org/downloads](https://www.python.org/downloads/)

**Linux (Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install python3.12 python3.12-venv python3-pip
```

</details>

### Step 2: Install Gulama

Open a terminal (Command Prompt, PowerShell, or Terminal) and run:

```bash
pip install gulama
```

> **Troubleshooting:** If `pip` is not recognized, try `python -m pip install gulama` instead.

Or install with all optional features (voice, browser automation, image generation):

```bash
pip install gulama[full]
```

### Step 3: Get an API Key

Gulama needs an API key from an LLM provider to work. Here are your options:

| Provider | Cost | How to get a key |
|----------|------|------------------|
| **DeepSeek** | ~$0.001/chat (cheapest) | Sign up at [platform.deepseek.com](https://platform.deepseek.com/) → API Keys → Create |
| **Groq** | Free tier available | Sign up at [console.groq.com](https://console.groq.com/) → API Keys → Create |
| **OpenAI** | ~$0.01/chat | Sign up at [platform.openai.com](https://platform.openai.com/) → API Keys → Create |
| **Anthropic** | ~$0.01/chat | Sign up at [console.anthropic.com](https://console.anthropic.com/) → API Keys → Create |
| **Google** | Free tier available | Sign up at [aistudio.google.com](https://aistudio.google.com/) → Get API Key |
| **Ollama** | **Free (runs locally)** | Install [Ollama](https://ollama.ai) → `ollama pull llama3.3` → No API key needed |

> **New to AI?** Start with **Groq** (free) or **DeepSeek** (cheapest). You can always switch later.

### Step 4: Run Setup

```bash
gulama setup
```

The interactive setup wizard walks you through everything:

1. **Create a master password** — All your credentials are encrypted with AES-256-GCM. This password unlocks them. Choose something strong.
2. **Pick your LLM provider** — Select from the list (Anthropic, OpenAI, Google, DeepSeek, Groq, Ollama, etc.)
3. **Paste your API key** — It's encrypted and stored in a local vault. Never stored in plaintext.
4. **Set your autonomy level** — How much freedom should Gulama have? (Default: Level 2 — Co-pilot)
5. **Optional: Connect channels** — Set up Telegram, Discord, or other messaging channels.

### Step 5: Start Chatting

```bash
gulama chat
```

That's it. You now have a secure AI assistant with access to 19 skills.

> **Try these first commands:**
> - `"What can you do?"` — See all available skills
> - `"Search the web for latest AI news"` — Test web search
> - `"Remember that my name is [your name]"` — Test memory
> - `"Read the file README.md"` — Test file access

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

### Docker (alternative)

Don't want to install Python? You can run Gulama in a Docker container instead:

<details>
<summary><b>What is Docker? (click to expand)</b></summary>

Docker lets you run apps in isolated containers — like lightweight virtual machines. You don't need Python installed on your system. Install Docker from [docker.com/get-docker](https://www.docker.com/get-docker/).

</details>

```bash
# Start Gulama in a container
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
| 🔌 | **MCP Bridge** | Connect to any MCP server or expose Gulama as one | Model Context Protocol |
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

Each channel just needs a token stored in the encrypted vault. Here's how to set up the most popular ones:

<details>
<summary><b>📱 Telegram (step-by-step)</b></summary>

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts to name your bot
3. BotFather gives you a **token** (looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
4. Store it in Gulama:
   ```bash
   gulama vault set TELEGRAM_BOT_TOKEN "your-token-here"
   ```
5. Start Gulama with Telegram:
   ```bash
   gulama start --channel telegram
   ```
6. Open your bot in Telegram and send it a message!

</details>

<details>
<summary><b>🎮 Discord (step-by-step)</b></summary>

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Click **New Application** → give it a name → click **Create**
3. Go to **Bot** tab → click **Reset Token** → copy the token
4. Go to **OAuth2 → URL Generator** → check **bot** scope → check **Send Messages** + **Read Messages** → copy the invite URL → open it to add the bot to your server
5. Store the token in Gulama:
   ```bash
   gulama vault set DISCORD_BOT_TOKEN "your-token-here"
   ```
6. Start Gulama with Discord:
   ```bash
   gulama start --channel discord
   ```

</details>

> 💡 See `.env.example` for all supported channels and token names.

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

Think of autonomy levels like a trust dial — from "ask me before touching anything" to "handle it yourself." You pick the level during `gulama setup`, and you can change it anytime:

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

### Security

| Feature | Gulama | OpenClaw |
|---------|--------|----------|
| Security mechanisms | **15+ built into core** | ~0 (security as afterthought) |
| Memory encryption | **AES-256-GCM** | None (plaintext) |
| Skill signing | **Ed25519 mandatory** | None (341 malicious skills found) |
| Policy engine | **Cedar-inspired deterministic** | None |
| Sandbox | **bubblewrap/Docker/OS** | Container-only |
| Audit trail | **Cryptographic hash-chain** | Basic logs |
| Prompt injection defense | **Canary tokens** | None |
| Egress filtering + DLP | **Built-in** | None |

### Modern AI Capabilities

| Feature | Gulama | OpenClaw |
|---------|--------|----------|
| MCP support | **Full server + client** | None |
| Multi-agent orchestration | **Background sub-agents** | None |
| Task scheduler | **Built-in cron + intervals** | None |
| Voice wake word | **Always-on "Hey Gulama"** | None |
| RAG memory | **ChromaDB vector search** | Full history dump |
| AI browser automation | **Playwright + browser-use** | Basic browser |
| Self-modifying skills | **Runtime authoring (sandboxed)** | No |
| Live debug stream | **WebSocket real-time inspector** | None |

### Platform

| Feature | Gulama | OpenClaw |
|---------|--------|----------|
| LLM providers | **100+** via LiteLLM | ~5 |
| Communication channels | **10** (CLI to Voice Wake) | CLI-focused |
| Cost controls | **Per-day budgets + alerts** | None |
| REST API | **29 endpoints + 2 WebSockets** | Limited |
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

Want to contribute or build your own skills? Here's how to set up the development environment:

```bash
# 1. Clone the repo
git clone https://github.com/san-techie21/gulama-bot.git
cd gulama-bot

# 2. Install in development mode (includes test tools)
pip install -e ".[dev]"

# 3. Run the test suite (277 tests)
python -m pytest tests/ -v

# 4. Run security-specific tests
python -m pytest tests/security/ -v

# 5. Lint
ruff check src/

# 6. Security health check
gulama doctor --json-output
```

> **First time contributing?** Check out [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines, or open an issue to say hi!

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

Found a bug or security issue? Please report it via [GitHub Issues](https://github.com/san-techie21/gulama-bot/issues) with the `security` label. We take every report seriously and will respond within 48 hours.

---

<p align="center">
  Built with 15+ years of security industry expertise.<br/><br/>
  <a href="https://github.com/san-techie21/gulama-bot">⭐ Star on GitHub</a> ·
  <a href="https://pypi.org/project/gulama/">📦 PyPI</a> ·
  <a href="https://www.linkedin.com/in/santechie21">💼 LinkedIn</a> ·
  <a href="CONTRIBUTING.md">🤝 Contribute</a>
</p>
