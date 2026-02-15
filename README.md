# Gulama

**Secure, open-source personal AI agent platform.**

Gulama is a security-first AI assistant that works with **any LLM provider** (100+ supported) and runs on **any platform** (macOS, Windows, Linux, Docker, ARM).

## Why Gulama?

Personal AI agents handle sensitive data — your files, emails, credentials, and conversations. Most existing solutions treat security as an afterthought. Gulama is built security-first from the ground up.

### Security Architecture

- **Encrypted at rest** — All credentials stored with AES-256-GCM, never plaintext
- **Sandboxed execution** — Every tool runs in bubblewrap/Docker/OS sandbox
- **Policy engine** — Deterministic authorization for all agent actions
- **Canary tokens** — Detects prompt injection attacks in real-time
- **Tamper-proof audit logs** — Hash-chain audit trail for every action
- **Egress filtering + DLP** — Prevents data exfiltration and credential leaks
- **Signed skills** — Cryptographic verification prevents supply-chain attacks

### Universal LLM Support

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

### Channels

- **CLI** — Interactive terminal chat
- **Telegram** — Bot integration
- **Discord** — Coming soon
- **WhatsApp** — Coming soon
- **Web UI** — Coming soon

## Quick Start

### Install

```bash
pip install gulama
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

# Start the gateway server
gulama start

# Start with Telegram
gulama start --channel telegram
```

### Docker

```bash
docker compose up
```

## Architecture

```
┌─────────────────────────────────────────┐
│              Channels                    │
│  CLI  │  Telegram  │  Discord  │  Web   │
├─────────────────────────────────────────┤
│           Gateway (FastAPI)              │
│    TOTP Auth  │  Rate Limit  │  CORS    │
├─────────────────────────────────────────┤
│            Agent Brain                   │
│  Context Builder (RAG) │ LLM Router     │
├─────────────────────────────────────────┤
│          Security Layer                  │
│ Policy │ Sandbox │ Canary │ Audit │ DLP │
├─────────────────────────────────────────┤
│        Skills (Sandboxed Tools)          │
│  Files │ Shell │ Web │ Notes │ Custom   │
├─────────────────────────────────────────┤
│          Storage Layer                   │
│  Encrypted SQLite  │  ChromaDB (RAG)    │
│  Secrets Vault     │  Audit Logs        │
└─────────────────────────────────────────┘
```

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
make dev

# Run tests
make test

# Run security tests
make test-security

# Lint
make lint
```

## Configuration

Configuration is loaded from:
1. `config/default.toml` (secure defaults)
2. `~/.gulama/config.toml` (user overrides)
3. Environment variables (`GULAMA_*`)

Key security defaults (cannot be disabled without `--i-know-what-im-doing`):
- Gateway binds to `127.0.0.1` only
- Sandbox enabled
- Policy engine enabled
- Audit logging enabled
- Skill signatures required

## License

MIT License. See [LICENSE](LICENSE).

## Security

Found a vulnerability? Please report it responsibly. See [GULAMA_MASTER_SPEC.md](GULAMA_MASTER_SPEC.md) for the full security architecture.
