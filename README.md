# Gulama

**Secure, open-source personal AI agent platform — OpenClaw, but secure.**

Gulama is a security-first AI assistant with **19 skills**, **8 channels**, a **signed skill marketplace**, and support for **100+ LLM providers**. Runs on macOS, Windows, Linux, Docker, and ARM.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-green.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-209%20passing-brightgreen.svg)]()
[![Security](https://img.shields.io/badge/Security-15%2B%20mechanisms-red.svg)]()

## Why Gulama?

Personal AI agents handle sensitive data — your files, emails, credentials, and conversations. Most existing solutions (including OpenClaw with its [341 malicious skills](https://www.securityweek.com/openclaw-vulnerabilities/)) treat security as an afterthought. **Gulama is built security-first from the ground up.**

### Security Architecture (15+ Mechanisms)

- **Encrypted at rest** — AES-256-GCM for all credentials, never plaintext
- **Sandboxed execution** — bubblewrap/Docker/OS sandbox for every tool
- **Policy engine** — Deterministic Cedar-inspired authorization
- **Canary tokens** — Real-time prompt injection detection
- **Tamper-proof audit logs** — Hash-chain audit trail
- **Egress filtering + DLP** — Prevents data exfiltration and credential leaks
- **Signed skills (GulamaHub)** — Ed25519 verification prevents supply-chain attacks
- **TOTP authentication** — Time-based one-time passwords for API access
- **Rate limiting** — Per-IP request throttling
- **Input validation** — Content scanning and sanitization
- **Loopback binding** — Gateway binds 127.0.0.1 only (never 0.0.0.0 without explicit flag)
- **Threat detection** — Brute force, privilege escalation, anomaly detection
- **RBAC** — Role-based access control with team management
- **SSO/API keys** — OIDC, SAML, API key authentication
- **Security headers** — HSTS, CSP, X-Frame-Options, and more

## Quick Start

### One-Line Install

```bash
pip install gulama
```

### With All Features

```bash
pip install gulama[full]
```

### Setup

```bash
gulama setup
```

The setup wizard walks you through:
1. Creating a master password (encrypts all credentials)
2. Choosing your LLM provider and entering your API key
3. Setting your autonomy level
4. Optional channel configuration

### Run

```bash
# Interactive CLI chat
gulama chat

# Start the gateway server (REST API + WebSocket)
gulama start

# Start with specific channel
gulama start --channel telegram
gulama start --channel discord
gulama start --channel matrix

# Start with always-on voice
gulama start --voice-wake

# Security health check
gulama doctor
```

### Docker

```bash
# Standard deployment
docker compose up -d

# With Redis + ChromaDB
docker compose --profile full up -d

# Cloud deployment (auto-TLS via Caddy)
docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d
```

## 19 Built-In Skills

| Skill | Description | API/Service |
|-------|-------------|-------------|
| **File Manager** | Read, write, search files | Local filesystem |
| **Shell Exec** | Execute commands in sandbox | OS shell |
| **Web Search** | Search and fetch web pages | DuckDuckGo/SearXNG |
| **Notes** | Save/recall facts and preferences | Local memory |
| **Code Exec** | Run Python/JS/Bash snippets | Sandboxed runtime |
| **Browser** | Navigate, screenshot, AI browsing | Playwright + browser-use |
| **Email** | Read, compose, send emails | IMAP/SMTP |
| **Calendar** | Manage events and schedules | Google Calendar/CalDAV |
| **MCP Bridge** | Connect to MCP servers | Model Context Protocol |
| **Voice** | Speech-to-text and text-to-speech | Whisper/Deepgram/ElevenLabs |
| **Image Gen** | Generate images from text | DALL-E/Stability AI/Replicate |
| **Smart Home** | Control IoT devices | Home Assistant |
| **GitHub** | Repos, issues, PRs, code search | GitHub API |
| **Notion** | Pages, databases, search | Notion API |
| **Spotify** | Playback, search, playlists | Spotify Web API |
| **Twitter/X** | Tweet search, user info | Twitter API v2 |
| **Google Docs** | Docs, Sheets, Drive | Google Workspace APIs |
| **Productivity** | Trello, Linear, Todoist, Obsidian | Multi-service |
| **Self-Modify** | AI writes its own new skills | Runtime skill authoring |

## 8 Communication Channels

| Channel | Status | Protocol |
|---------|--------|----------|
| **CLI** | Ready | Interactive terminal |
| **Telegram** | Ready | Bot API |
| **Discord** | Ready | discord.py |
| **Slack** | Ready | Slack SDK + Webhooks |
| **WhatsApp** | Ready | Cloud API |
| **Matrix** | Ready | matrix-nio (E2E encrypted) |
| **Microsoft Teams** | Ready | Bot Framework webhooks |
| **Google Chat** | Ready | Workspace webhooks |

Plus: **Web UI** channel and **Voice Wake** (always-on "Hey Gulama" listener).

## Universal LLM Support

Works with **any** LLM provider via LiteLLM:

| Provider | Models |
|----------|--------|
| Anthropic | Claude Sonnet 4.5, Opus 4.6, Haiku 4.5 |
| OpenAI | GPT-4o, o1, o3-mini |
| Google | Gemini 2.0 Flash, Pro |
| DeepSeek | DeepSeek Chat, Reasoner |
| Alibaba | Qwen Plus, Max, Turbo |
| Groq | Llama 3.3, Mixtral |
| Ollama | Any local model |
| Together AI | Llama, Mistral, and more |
| AWS Bedrock | All Bedrock models |
| Azure OpenAI | All Azure models |
| 90+ more | Any OpenAI-compatible endpoint |

## GulamaHub — Secure Skill Marketplace

Unlike other agent platforms, **every community skill must be Ed25519-signed**. No exceptions.

```bash
# Search skills
gulama hub search "weather"

# Install (signature verified automatically)
gulama hub install weather-checker

# Publish your own (signing required)
gulama hub publish my-skill --sign
```

The agent can also **write its own skills** at runtime via the Self-Modify skill — with full sandboxing and security scanning.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Channels (8)                          │
│  CLI │ Telegram │ Discord │ Slack │ WhatsApp │ Matrix    │
│  Teams │ Google Chat │ Web UI │ Voice Wake              │
├──────────────────────────────────────────────────────────┤
│              Gateway (FastAPI) — 29 Routes                │
│  TOTP Auth │ Rate Limit │ CORS │ Security Headers        │
├──────────────────────────────────────────────────────────┤
│                  Agent Brain                              │
│  Context Builder (RAG) │ LLM Router │ Tool Calling Loop  │
│  Sub-Agent Manager │ Task Scheduler                      │
├──────────────────────────────────────────────────────────┤
│                 Security Layer (15+)                      │
│ Policy Engine │ Sandbox │ Canary │ Audit │ DLP │ Egress  │
│ RBAC │ SSO │ Threat Detection │ Input Validation         │
├──────────────────────────────────────────────────────────┤
│              Skills (19 Built-in + Marketplace)           │
│ Files │ Shell │ Web │ Browser │ Email │ Calendar │ Voice │
│ GitHub │ Notion │ Spotify │ Google Docs │ Self-Modify    │
├──────────────────────────────────────────────────────────┤
│                   Storage Layer                           │
│  Encrypted SQLite │ ChromaDB (RAG) │ Secrets Vault       │
│  Hash-Chain Audit │ Disk Cache                           │
├──────────────────────────────────────────────────────────┤
│                   Debug & Monitoring                      │
│  WebSocket Debug Stream │ Cost Tracking │ Token Budgets  │
└──────────────────────────────────────────────────────────┘
```

## REST API (29 Endpoints)

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/chat` | Send message to agent |
| `GET /api/v1/status` | Agent status and stats |
| `GET /api/v1/skills` | List all registered skills |
| `GET /api/v1/agents` | List background sub-agents |
| `POST /api/v1/agents/spawn` | Spawn background agent |
| `GET /api/v1/scheduler/tasks` | List scheduled tasks |
| `GET /api/v1/hub/search` | Search skill marketplace |
| `GET /api/v1/conversations` | List conversations |
| `GET /api/v1/audit` | View audit log |
| `GET /api/v1/cost/today` | Token usage and cost |
| `GET /api/v1/debug/events` | Debug event stream |
| `ws://localhost:18789/ws/chat` | Real-time WebSocket chat |
| `ws://localhost:18789/ws/debug` | Live debug inspector |

## Autonomy Levels

| Level | Name | Behavior |
|-------|------|----------|
| 0 | Observer | Ask before every action |
| 1 | Assistant | Auto-read, ask before writes |
| 2 | Co-pilot | Auto safe actions, ask before shell/network |
| 3 | Autopilot-cautious | Auto most things, ask before destructive |
| 4 | Autopilot | Auto everything except financial/credential |

## Development

```bash
# Clone
git clone https://github.com/san-techie21/gulama-bot.git
cd gulama-bot

# Setup dev environment
pip install -e ".[dev]"

# Run tests (209 tests)
python -m pytest tests/ -v

# Security health check
gulama doctor --json-output

# Lint
ruff check src/
```

## Configuration

Configuration is loaded from:
1. `config/default.toml` (secure defaults)
2. `~/.gulama/config.toml` (user overrides)
3. Environment variables (`GULAMA_*`)
4. `.env` file (for secrets — see `.env.example`)

Key security defaults (cannot be disabled without `--i-know-what-im-doing`):
- Gateway binds to `127.0.0.1` only
- Sandbox enabled
- Policy engine enabled
- Audit logging enabled
- Skill signatures required

## Deployment

| Method | Command | Use Case |
|--------|---------|----------|
| **pip install** | `pip install gulama` | Local development |
| **Docker** | `docker compose up -d` | Self-hosted server |
| **Cloud** | `docker compose -f ... up -d` | DigitalOcean/AWS/GCP |
| **Docker + TLS** | With `docker-compose.cloud.yml` | Production with auto-HTTPS |

## vs OpenClaw

| Feature | Gulama | OpenClaw |
|---------|--------|----------|
| Security mechanisms | 15+ | ~0 |
| Memory encryption | AES-256-GCM | None |
| Skill signing | Ed25519 mandatory | None (341 malicious skills found) |
| LLM providers | 100+ (LiteLLM) | ~5 |
| Policy engine | Cedar-inspired | None |
| Sandbox | bubblewrap/Docker | Container-only |
| Audit trail | Hash-chain | Basic logs |
| Cost controls | Per-day budgets | None |
| Self-modifying skills | Yes (sandboxed) | No |
| License | MIT | MIT |

## License

MIT License. See [LICENSE](LICENSE).

## Security

Found a vulnerability? Please report it responsibly via [GitHub Issues](https://github.com/san-techie21/gulama-bot/issues) with the `security` label.

---

**Built with security as the #1 priority by [Astra Fintech Labs](https://astrafintechlabs.com).**
