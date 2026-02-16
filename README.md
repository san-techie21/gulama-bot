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
</p>

<p align="center">
  <a href="#-get-started-in-60-seconds">Quick Start</a> •
  <a href="#-skills">Skills</a> •
  <a href="#-channels">Channels</a> •
  <a href="#-security">Security</a> •
  <a href="#-gulama-vs-openclaw">Compare</a> •
  <a href="https://pypi.org/project/gulama/">PyPI</a> •
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

---

<p align="center">
  <a href="media/Gulama_Bot_AI_Video.mp4">
    <img src="media/Gulama.png" alt="Watch Gulama in action" width="400"/>
  </a>
  <br/>
  <em>▶ Click to watch Gulama's intro video</em>
</p>

---

Personal AI agents handle your files, emails, credentials, and conversations. Most treat security as an afterthought. **Gulama is built security-first from the ground up** — with 15+ security mechanisms, 19 skills, 8 communication channels, and support for 100+ LLM providers.

> **One agent. Any LLM. Actually secure.**

## 🚀 Get Started in 60 Seconds

```bash
pip install gulama
gulama setup      # Guided wizard — encrypts credentials, picks your LLM
gulama chat       # Start chatting
```

Or with Docker:

```bash
docker compose up -d
```

<details>
<summary><b>More install options</b></summary>

```bash
# Install with all optional features
pip install gulama[full]

# Start the gateway server (REST API + WebSocket)
gulama start

# Connect a channel
gulama start --channel telegram
gulama start --channel discord
gulama start --channel matrix

# Always-on voice mode
gulama start --voice-wake

# Security health check
gulama doctor
```

**Docker (advanced):**
```bash
# With Redis + ChromaDB
docker compose --profile full up -d

# Cloud deployment (auto-TLS via Caddy)
docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d
```

</details>

## 🛠 Skills

Gulama ships with **19 built-in skills** — and you can install more from **GulamaHub** or let the agent write its own at runtime.

| | Skill | What it does |
|---|-------|-------------|
| 📁 | **File Manager** | Read, write, search files |
| 💻 | **Shell Exec** | Execute commands (sandboxed) |
| 🌐 | **Web Search** | Search & fetch web pages |
| 🧠 | **Notes** | Save/recall facts & preferences |
| ⚡ | **Code Exec** | Run Python/JS/Bash snippets |
| 🖥️ | **Browser** | Navigate, screenshot, AI browsing |
| 📧 | **Email** | Read, compose, send (IMAP/SMTP) |
| 📅 | **Calendar** | Google Calendar / CalDAV |
| 🔌 | **MCP Bridge** | Connect to MCP servers |
| 🎤 | **Voice** | STT & TTS (Whisper/Deepgram/ElevenLabs) |
| 🎨 | **Image Gen** | DALL-E / Stability AI / Replicate |
| 🏠 | **Smart Home** | Home Assistant IoT control |
| 🐙 | **GitHub** | Repos, issues, PRs, code search |
| 📝 | **Notion** | Pages, databases, search |
| 🎵 | **Spotify** | Playback, search, playlists |
| 🐦 | **Twitter/X** | Tweet search, user info |
| 📊 | **Google Docs** | Docs, Sheets, Drive |
| ✅ | **Productivity** | Trello, Linear, Todoist, Obsidian |
| 🤖 | **Self-Modify** | AI writes its own new skills |

## 📡 Channels

Talk to Gulama from anywhere:

**CLI** · **Telegram** · **Discord** · **Slack** · **WhatsApp** · **Matrix** (E2E encrypted) · **Microsoft Teams** · **Google Chat** · **Web UI** · **Voice Wake** ("Hey Gulama")

## 🧩 Any LLM, Your Choice

Works with **100+ providers** via LiteLLM — never locked to one vendor:

**Anthropic** · **OpenAI** · **Google Gemini** · **DeepSeek** · **Alibaba Qwen** · **Groq** · **Ollama** (local) · **Together AI** · **AWS Bedrock** · **Azure OpenAI** · and 90+ more

## 🔒 Security

This is where Gulama is different. **15+ security mechanisms**, not as add-ons, but as the foundation:

| Mechanism | What it does |
|-----------|-------------|
| **AES-256-GCM encryption** | All credentials encrypted at rest |
| **Sandboxed execution** | bubblewrap/Docker/OS sandbox for every tool |
| **Policy engine** | Cedar-inspired deterministic authorization |
| **Canary tokens** | Real-time prompt injection detection |
| **Hash-chain audit** | Tamper-proof audit trail |
| **Egress filtering + DLP** | Prevents data exfiltration |
| **Signed skills** | Ed25519 verification on GulamaHub |
| **TOTP auth** | Time-based OTP for API access |
| **Rate limiting** | Per-IP throttling |
| **Input validation** | Content scanning & sanitization |
| **Loopback binding** | `127.0.0.1` only by default |
| **Threat detection** | Brute force & anomaly detection |
| **RBAC** | Role-based access control |
| **SSO/API keys** | OIDC, SAML, API key auth |
| **Security headers** | HSTS, CSP, X-Frame-Options |

## 🏪 GulamaHub — Skill Marketplace

Every community skill must be **Ed25519-signed**. No exceptions.

```bash
gulama hub search "weather"           # Search skills
gulama hub install weather-checker    # Install (signature verified)
gulama hub publish my-skill --sign    # Publish your own
```

The agent can also **write its own skills** at runtime — with full sandboxing and security scanning.

## 🎛 Autonomy Levels

Choose how much freedom Gulama has:

| Level | Name | Behavior |
|:-----:|------|----------|
| 0 | **Observer** | Asks before every action |
| 1 | **Assistant** | Auto-reads, asks before writes |
| 2 | **Co-pilot** | Auto safe actions, asks before shell/network |
| 3 | **Autopilot-cautious** | Auto most things, asks before destructive |
| 4 | **Autopilot** | Auto everything except financial/credential |

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Channels (8+)                         │
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
└──────────────────────────────────────────────────────────┘
```

<details>
<summary><b>REST API (29 endpoints)</b></summary>

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/chat` | Send message to agent |
| `GET /api/v1/status` | Agent status and stats |
| `GET /api/v1/skills` | List registered skills |
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

</details>

## 🆚 Gulama vs OpenClaw

| Feature | Gulama | OpenClaw |
|---------|--------|----------|
| Security mechanisms | **15+** | ~0 |
| Memory encryption | **AES-256-GCM** | None |
| Skill signing | **Ed25519 mandatory** | None (341 malicious found) |
| LLM providers | **100+** (LiteLLM) | ~5 |
| Policy engine | **Cedar-inspired** | None |
| Sandbox | **bubblewrap/Docker** | Container-only |
| Audit trail | **Hash-chain** | Basic logs |
| Cost controls | **Per-day budgets** | None |
| Self-modifying skills | **Yes (sandboxed)** | No |

## 🧑‍💻 Development

```bash
git clone https://github.com/san-techie21/gulama-bot.git
cd gulama-bot
pip install -e ".[dev]"
python -m pytest tests/ -v    # 277 tests
ruff check src/               # Lint
gulama doctor --json-output   # Security health check
```

## ⚙️ Configuration

Configuration loads from (in priority order):
1. `config/default.toml` — secure defaults
2. `~/.gulama/config.toml` — user overrides
3. Environment variables (`GULAMA_*`)
4. `.env` file (see `.env.example`)

Security defaults that require `--i-know-what-im-doing` to override:
- Gateway binds `127.0.0.1` only
- Sandbox, policy engine, audit logging enabled
- Skill signatures required

## 📦 Deployment

| Method | Command | Use Case |
|--------|---------|----------|
| **pip** | `pip install gulama` | Local / dev |
| **Docker** | `docker compose up -d` | Self-hosted |
| **Cloud** | `docker compose -f ... up -d` | AWS / GCP / DO |
| **Docker + TLS** | With `docker-compose.cloud.yml` | Production |

## 📜 License

MIT — see [LICENSE](LICENSE).

## 🔐 Security Policy

Found a vulnerability? Report it via [GitHub Issues](https://github.com/san-techie21/gulama-bot/issues) with the `security` label.

---

<p align="center">
  Built with 15+ years of security industry expertise.<br/>
  <a href="https://github.com/san-techie21/gulama-bot">GitHub</a> ·
  <a href="https://pypi.org/project/gulama/">PyPI</a> ·
  <a href="CONTRIBUTING.md">Contribute</a>
</p>
