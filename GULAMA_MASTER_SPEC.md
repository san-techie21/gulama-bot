# GULAMA BOT — MASTER SPECIFICATION

## The Absolute Source of Truth for Building Gulama

> **Project**: Gulama Bot — Secure, Open-Source Personal AI Agent Platform
> **Author**: Santosh — Founder & Chief Architect, Astra Fintech Labs Pvt. Ltd., Bengaluru, India
> **Credentials**: CISM, CCNA | 14+ years enterprise IT security (Honeywell, Huawei, Capgemini, Accolite Digital)
> **Date**: February 15, 2026
> **Version**: 1.0
> **License**: MIT (open-source, free forever)
> **Repository**: https://github.com/san-techie21/gulama-bot

---

## TABLE OF CONTENTS

1. [What Gulama Is](#1-what-gulama-is)
2. [Core Requirements (Non-Negotiable)](#2-core-requirements-non-negotiable)
3. [Market Context & Research Findings](#3-market-context--research-findings)
4. [Competitive Analysis](#4-competitive-analysis)
5. [Architecture Overview](#5-architecture-overview)
6. [Tech Stack (Final)](#6-tech-stack-final)
7. [Security Architecture (Core Differentiator)](#7-security-architecture-core-differentiator)
8. [Universal LLM Support](#8-universal-llm-support)
9. [Cross-Platform Support](#9-cross-platform-support)
10. [Component Specifications](#10-component-specifications)
11. [Directory Structure](#11-directory-structure)
12. [Build Order & Milestones](#12-build-order--milestones)
13. [Security Comparison Matrix](#13-security-comparison-matrix)
14. [OWASP Agentic Top 10 Compliance](#14-owasp-agentic-top-10-compliance)
15. [Business Model](#15-business-model)
16. [Branding & Domains](#16-branding--domains)
17. [Go-To-Market Strategy](#17-go-to-market-strategy)
18. [Reference: OpenClaw Vulnerabilities](#18-reference-openclaw-vulnerabilities)
19. [Reference: Industry Verdicts](#19-reference-industry-verdicts)
20. [Implementation Rules](#20-implementation-rules)

---

## 1. WHAT GULAMA IS

### The One-Liner

**A full-featured, open-source personal AI agent — like OpenClaw — but built security-first, model-agnostic, and cross-platform from day one.**

### What It Does

Gulama is a self-hosted personal AI assistant that:

- Connects to messaging channels (Telegram, WhatsApp, Discord, Slack, Web UI, CLI)
- Runs AI-powered agents that can execute tasks, browse the web, manage files, run code, handle emails/calendars
- Maintains persistent encrypted memory across conversations
- Supports extensible skills/plugins (all cryptographically signed)
- Works with ANY LLM API — Claude, GPT, Gemini, DeepSeek, Qwen, Ollama, or any OpenAI-compatible endpoint
- Runs on ANY platform — macOS, Windows, Linux, Docker, ARM, servers, cloud VMs
- Is secure by default — encrypted credentials, mandatory sandboxing, policy engine, tamper-proof audit logs

### What It Is NOT

- NOT tied to any single LLM provider (not a "Claude bot" or "GPT bot")
- NOT platform-restricted (not macOS-only or Linux-only)
- NOT freemium/trial-limited (fully open-source, MIT license, free forever)
- NOT a workflow automation tool (not n8n/Zapier — it's a personal AI agent)
- NOT a document chatbot (not AnythingLLM — it takes actions, not just answers)

### Core Principles

1. **Secure by default** — No insecure configuration possible without explicit opt-in
2. **Model-agnostic** — Works with any LLM provider, including Chinese APIs and local models
3. **Cross-platform** — macOS, Windows, Linux, Docker, ARM, any server
4. **Zero-trust tool execution** — Every tool call goes through a policy engine before running
5. **Encrypted everything** — Memory, credentials, audit logs — all encrypted at rest
6. **Mandatory sandboxing** — All tool execution runs in sandboxes, not on the host
7. **Signed skills only** — No unsigned/unverified code runs, ever
8. **Open-source (MIT)** — Full transparency, community audit, no restrictions on use
9. **Cost-aware** — Built-in token tracking, budgets, and cost dashboards
10. **Feature parity + more** — Everything OpenClaw does, plus security, plus better UX

---

## 2. CORE REQUIREMENTS (NON-NEGOTIABLE)

These requirements are absolute. Every implementation decision must satisfy ALL of these.

### 2.1 Universal LLM Support

Gulama MUST work with ANY of these LLM providers out of the box:

| Category | Providers |
|----------|-----------|
| **US Cloud** | Anthropic (Claude), OpenAI (GPT/o-series), Google (Gemini), Mistral, Cohere |
| **Chinese APIs** | DeepSeek, Qwen (Alibaba/DashScope), Zhipu (GLM/ChatGLM), Baichuan, Moonshot (Kimi), Yi (01.AI), MiniMax |
| **Local Models** | Ollama, llama.cpp, vLLM, LM Studio, LocalAI |
| **Inference Platforms** | Groq, Together AI, Fireworks AI, Anyscale, Replicate, Perplexity |
| **Custom Endpoints** | Any OpenAI-compatible REST API, corporate self-hosted models |

Implementation: Use **LiteLLM** as the universal adapter layer. It supports 100+ providers including all Chinese APIs. For any provider LiteLLM doesn't cover, provide a clean adapter interface.

No provider gets preferential treatment in the codebase. The user picks their provider in config.

### 2.2 Cross-Platform Support

Gulama MUST run flawlessly on:

| Platform | Minimum Version |
|----------|----------------|
| **macOS** | 12+ (Monterey), Intel and Apple Silicon |
| **Windows** | 10 21H2+, Windows 11, Windows Server 2019+ |
| **Linux** | Ubuntu 22.04+, Debian 12+, Fedora 38+, Arch (rolling) |
| **Docker** | Any platform with Docker Engine 24+ |
| **ARM** | Raspberry Pi 4+, ARM64 servers |
| **Cloud** | Any VPS/VM — Hetzner, DigitalOcean, AWS, Azure, GCP, Alibaba Cloud |

No platform-specific code in the core. Platform-specific functionality (sandboxing, keyring) uses runtime detection and adapters.

### 2.3 Full Feature Parity with OpenClaw (and More)

Everything OpenClaw does, Gulama must also do:

| Feature | OpenClaw | Gulama |
|---------|----------|--------|
| Messaging channels | Telegram, WhatsApp, Slack, Discord, Signal, iMessage, Teams, Web | Telegram (MVP), WhatsApp, Discord, Web UI, CLI — expandable |
| Shell command execution | Yes (host access) | Yes (sandboxed, policy-checked) |
| File management | Yes (unrestricted) | Yes (sandboxed, path-restricted) |
| Web browsing | Yes (unrestricted) | Yes (sandboxed Playwright) |
| Email management | Yes | Yes (with DLP) |
| Calendar integration | Yes | Yes |
| Persistent memory | Yes (plain Markdown) | Yes (AES-256 encrypted SQLite + ChromaDB vectors) |
| Skills/plugins | Yes (ClawHub, 20% malicious) | Yes (signed-only marketplace) |
| Voice input/output | Yes | Yes (Phase 4) |
| Heartbeat/cron | Yes | Yes |
| Browser automation | Yes | Yes (sandboxed) |
| Multiple LLM support | Yes (model-agnostic) | Yes (100+ providers via LiteLLM) |
| Code execution | Yes | Yes (sandboxed) |

**Plus Gulama adds:**
- Encrypted credential vault (age/SOPS/keyring)
- Mandatory sandboxing (cross-platform)
- Cedar policy engine (zero-trust tool execution)
- Canary token system (prompt injection detection)
- Egress filtering + DLP (data exfiltration prevention)
- Tamper-proof Merkle audit logs
- Signed skills verification (Sigstore cosign + SBOM)
- Cost tracking + budget controls
- Security self-audit CLI
- OWASP Agentic Top 10 compliance
- One-command setup
- OpenClaw migration tool

### 2.4 Security (Non-Negotiable)

- **NEVER** store any credential in plaintext — not in config, memory, logs, or env files
- **NEVER** bind to 0.0.0.0 by default — loopback only (127.0.0.1)
- **EVERY** tool call goes through the policy engine — no exceptions
- **EVERY** skill must have a valid signature — unsigned = rejected
- **EVERY** action is audit-logged with Merkle chain integrity
- **Memory is ALWAYS encrypted** at rest (AES-256-GCM via SQLCipher)
- **WebSocket connections ALWAYS validate origin** — cross-origin = rejected
- **Sandbox is MANDATORY** — no "disable sandbox" without extreme friction
- **Cost tracking is ALWAYS on** — users see exactly what they spend

### 2.5 Open Source & Free

- MIT License — anyone can use, modify, distribute, even commercially
- No download limits, trial periods, or freemium gates
- Full platform free forever in Community Edition
- Revenue comes from services (hosting, support, enterprise features), not code restrictions
- The project must feel like a movement, not a product

---

## 3. MARKET CONTEXT & RESEARCH FINDINGS

### 3.1 OpenClaw Current State (As of February 15, 2026)

| Metric | Value | Source |
|--------|-------|--------|
| GitHub Stars | 145,000+ | Wikipedia, GitHub |
| Open Issues | 16,900+ | GitHub |
| Latest Release | v2026.2.12 (Feb 12, 2026) | GitHub Releases |
| Exposed Instances | 42,900+ across 82 countries | SecurityScorecard |
| RCE-Vulnerable Instances | 15,200+ (35.4%) | Combined analysis |
| Malicious Skills | ~900 (20% of marketplace) | Bitdefender, Koi Security, Reco |
| Total Vulnerabilities Found | 512 (8 critical) | Security audit Jan 2026 |
| CVEs | 3 high-severity with public exploits | SecurityScorecard STRIKE |
| Bug Bounty | None | — |
| Security Team | None | — |

**OpenClaw v2026.2.12 Improvements** (Feb 12, 2026):
- SSRF deny policy + hostname allowlists added
- Browser output now "untrusted by default"
- Auth token auto-generated on install
- Hooks reject session key overrides
- 40+ vulnerabilities patched

**Fundamental flaws STILL present:**
- Credentials still in plaintext config files
- No mandatory sandboxing
- No skill signing or verification
- No policy engine for tool execution
- No prompt injection defense beyond LLM judgment
- No tamper-proof audit logging

### 3.2 OWASP Top 10 for Agentic Applications 2026

Released December 2025, developed by 100+ experts. The definitive security framework for AI agents:

| # | Risk | Description |
|---|------|-------------|
| ASI01 | Agent Goal Hijack | Manipulation of instructions/inputs to redirect agent objectives |
| ASI02 | Tool Misuse & Exploitation | Agents misusing tools due to prompt manipulation or unsafe delegation |
| ASI03 | Identity & Privilege Abuse | Exploiting inherited credentials, cached tokens, delegated permissions |
| ASI04 | Supply Chain Vulnerabilities | Compromised tools, models, or personas influencing agent behavior |
| ASI05 | Unexpected Code Execution | Agents executing untrusted or attacker-controlled code |
| ASI06 | Memory & Context Poisoning | Persistent corruption of agent memory, RAG stores, embeddings |
| ASI07 | Insecure Inter-Agent Communication | Spoofed/intercepted communication between agents |
| ASI08 | Cascading Failures | False signals cascading through automated pipelines |
| ASI09 | Human-Agent Trust Exploitation | Polished explanations misleading humans into approving harmful actions |
| ASI10 | Rogue Agents | Misaligned or compromised agents diverging from intended behavior |

**Gulama addresses ALL 10.** This is a major marketing and technical differentiator.

### 3.3 AI Agent Security Best Practices (OWASP Cheat Sheet)

Key recommendations from the OWASP AI Agent Security Cheat Sheet:

1. **Tool Security**: Minimal necessary access, allowlists, blocked patterns
2. **Input Validation**: Treat ALL external data as potentially malicious
3. **Memory Protection**: Validate before storage, isolate between users, checksums for integrity
4. **Human-in-the-Loop**: Classify actions by risk, require approval for sensitive operations
5. **Output Validation**: Schema validation, PII filtering, exfiltration pattern detection
6. **Monitoring**: Log all decisions, anomaly detection, cost tracking
7. **Data Classification**: Automatic sensitivity classification, tiered protections

### 3.4 Sandbox Landscape (Feb 2026)

Industry consensus: shared-kernel containers (Docker/runc) are NOT sufficient for untrusted AI agent code execution.

| Tier | Technology | Isolation | Platform |
|------|-----------|-----------|----------|
| Tier 1 (Strongest) | Firecracker microVMs | Separate kernel | Linux only |
| Tier 2 | gVisor (runsc) | User-space kernel | Linux only |
| Tier 3 | bubblewrap (bwrap) | Namespace isolation | Linux (Anthropic uses for Claude Code) |
| Tier 3 | Apple sandbox-exec | Seatbelt profiles | macOS only |
| Tier 3 | Windows Sandbox | Hyper-V isolation | Windows Pro/Enterprise |
| Tier 4 (Fallback) | Docker containers | Shared kernel | Any OS |

**Gulama strategy**: Auto-detect OS, use best available. Docker as universal fallback.

### 3.5 Policy Engine: Cedar vs OPA

Research conclusion for AI agent authorization:

| Attribute | OPA (Rego) | Cedar |
|-----------|-----------|-------|
| Determinism | Non-deterministic, runtime exceptions possible | **Deterministic, guaranteed** |
| Safety | Expressive but error-prone | **Safe, strong validation** |
| Purpose | General-purpose policy | **Built for authorization decisions** |
| For AI Agents | Dynamic evaluation, situational context | **Impermeable guardrails** |

**Decision: Use Cedar.** For security-critical allow/deny decisions on tool execution, determinism is essential.

---

## 4. COMPETITIVE ANALYSIS

### Direct Competitors

| Feature | OpenClaw | NanoClaw | Nanobot | **Gulama** |
|---------|----------|----------|---------|-----------|
| **Stars** | 145K+ | 7K+ | ~2K | New |
| **Language** | TypeScript | TypeScript | Python | **Python + Rust hot paths** |
| **LOC** | 430,000+ | ~500 | ~4,000 | Target: lean core |
| **LLM Support** | Model-agnostic | Claude only (Agent SDK) | Multi | **100+ providers (LiteLLM)** |
| **Platform** | macOS/Linux primary | macOS/Linux | Cross-platform | **macOS/Windows/Linux/Docker/ARM** |
| **Credential Storage** | Plaintext | Config files | Config files | **age-encrypted vault** |
| **Memory** | Plain Markdown | Basic memory | Basic | **AES-256 SQLCipher + ChromaDB RAG** |
| **Sandbox** | Optional | Container isolation | None | **Mandatory, cross-platform, auto-detect** |
| **Policy Engine** | None | None | None | **Cedar (deterministic, zero-trust)** |
| **Skill Verification** | None (20% malicious) | None | None | **Sigstore cosign + SBOM + Grype** |
| **Audit Logs** | Basic files | None | None | **Tamper-proof Merkle chains** |
| **Prompt Injection Defense** | LLM judgment | None | None | **Canary tokens + sanitization + policy** |
| **Egress/DLP** | None | None | None | **Outbound filtering + credential detection** |
| **Cost Control** | None | None | None | **Built-in budgets + per-task tracking** |
| **OWASP Top 10** | 0/10 | 2/10 | 0/10 | **10/10** |
| **Bug Bounty** | None | None | None | **Day one** |
| **Channels** | 10+ | WhatsApp only | CLI | **Telegram + WhatsApp + Discord + Web + CLI** |

### Gulama's Unfair Advantages

1. **Security credibility** — Built by CISM-certified architect with 14+ years enterprise security
2. **OWASP compliance** — Only agent addressing all 10 Agentic Top 10 risks
3. **Truly universal** — Any LLM, any OS, any server
4. **Cross-platform sandbox** — Auto-detects and uses best available isolation per OS
5. **No vendor lock-in** — Works with Chinese APIs, local models, corporate endpoints
6. **Indian market positioning** — Underserved, cost-sensitive, large developer base

---

## 5. ARCHITECTURE OVERVIEW

```
+----------------------------------------------------------------------+
|                         CHANNELS LAYER                                 |
|  +----------+ +----------+ +----------+ +----------+ +----------+     |
|  | Telegram | | WhatsApp | | Discord  | |  Web UI  |   | CLI    |     |
|  +----+-----+ +----+-----+ +----+-----+ +----+-----+ +----+-----+    |
|       |            |            |             |            |           |
|       +------------+------+-----+-------------+------------+          |
|                           |                                           |
|  +------------------------v-----------------------------------------+ |
|  |                  GATEWAY (FastAPI + WebSocket)                    | |
|  |  +--------+ +-----------+ +-----------+ +----------+            | |
|  |  | Auth   | | Rate      | | Session   | | Channel  |            | |
|  |  | (TOTP/ | | Limiter   | | Manager   | | Router   |            | |
|  |  |  JWT)  | |           | |           | |          |            | |
|  |  +--------+ +-----------+ +-----------+ +----------+            | |
|  +------------------------+-----------------------------------------+ |
|                           |                                           |
|  +------------------------v-----------------------------------------+ |
|  |              SECURITY LAYER (Defense in Depth)                    | |
|  |  +----------+ +----------+ +----------+ +----------+            | |
|  |  | Cedar    | | Canary   | | Egress   | | Audit    |            | |
|  |  | Policy   | | Tokens   | | Filter   | | Logger   |            | |
|  |  | Engine   | | (Inject  | | + DLP    | | (Merkle  |            | |
|  |  | (zero-   | |  Detect) | | (Data    | |  Tree)   |            | |
|  |  |  trust)  | |          | |  Loss    | |          |            | |
|  |  |          | |          | |  Prev.)  | |          |            | |
|  |  +----------+ +----------+ +----------+ +----------+            | |
|  |  +----------+ +----------+ +----------+                         | |
|  |  | Input    | | Skill    | | Secrets  |                         | |
|  |  | Sanitizer| | Verifier | | Vault    |                         | |
|  |  |          | | (cosign) | | (age/    |                         | |
|  |  |          | |          | |  keyring)|                         | |
|  |  +----------+ +----------+ +----------+                         | |
|  +------------------------+-----------------------------------------+ |
|                           |                                           |
|  +------------------------v-----------------------------------------+ |
|  |                    AGENT LAYER                                    | |
|  |  +----------+ +----------+ +----------+ +----------+            | |
|  |  | Universal| | Tool     | | Context  | | Autonomy |            | |
|  |  | LLM      | | Executor | | Builder  | | Control  |            | |
|  |  | Router   | | (Sand-   | | (RAG)    | | (0-5     |            | |
|  |  | (LiteLLM)| |  boxed)  | |          | |  levels) |            | |
|  |  +----------+ +----------+ +----------+ +----------+            | |
|  +------------------------+-----------------------------------------+ |
|                           |                                           |
|  +------------------------v-----------------------------------------+ |
|  |                CROSS-PLATFORM SANDBOX                             | |
|  |  +----------+ +----------+ +----------+ +----------+            | |
|  |  | bwrap    | | gVisor   | | Apple    | | Docker   |            | |
|  |  | (Linux)  | | (Linux)  | | Sandbox  | | (Any OS  |            | |
|  |  |          | |          | | (macOS)  | |  fallback)|           | |
|  |  +----------+ +----------+ +----------+ +----------+            | |
|  |  +-------------------+                                           | |
|  |  | Windows Sandbox / |                                           | |
|  |  | WSL2 (Windows)    |                                           | |
|  |  +-------------------+                                           | |
|  +------------------------------------------------------------------+ |
|                                                                        |
|  +------------------------------------------------------------------+ |
|  |                 ENCRYPTED PERSISTENCE LAYER                       | |
|  |  +-------------+ +-------------+ +-------------+ +-----------+  | |
|  |  | Secrets     | | Memory DB   | | Vector DB   | | Config    |  | |
|  |  | Vault       | | (SQLCipher  | | (ChromaDB)  | | Store     |  | |
|  |  | (age/SOPS/  | |  AES-256)   | |             | | (TOML)    |  | |
|  |  |  keyring)   | |             | |             | |           |  | |
|  |  +-------------+ +-------------+ +-------------+ +-----------+  | |
|  |  +-----------+                                                   | |
|  |  | Audit     |                                                   | |
|  |  | Merkle    |                                                   | |
|  |  | Chain     |                                                   | |
|  |  +-----------+                                                   | |
|  +------------------------------------------------------------------+ |
+------------------------------------------------------------------------+
```

### Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary Language | **Python 3.12+** | AI ecosystem, rapid dev, cross-platform |
| Hot Paths | **Rust** (via PyO3/maturin) | Policy eval, canary detection, Merkle trees |
| Gateway | **FastAPI + uvicorn** | Async, WebSocket native, well-documented |
| LLM Abstraction | **LiteLLM** | 100+ providers, OpenAI-compatible wire protocol |
| Policy Engine | **Cedar** | Deterministic, safe, built for authorization |
| Sandbox | **Cross-platform auto-detect** | bwrap/gVisor (Linux), sandbox-exec (macOS), Docker (fallback) |
| Memory DB | **SQLCipher** | AES-256 encrypted SQLite, zero-config, embedded |
| Vector DB | **ChromaDB** | Embedded, persistent, semantic search |
| Secrets | **age + SOPS + OS keyring** | Never plaintext, cross-platform |
| Skill Signing | **Sigstore cosign** | Keyless signing, transparency logs |
| Audit Logs | **Merkle tree** (Rust impl) | Tamper-proof, verifiable |
| Config Format | **TOML** | Human-readable, typed, standard |
| Package Manager | **uv** | Fast, modern Python |
| Container | **Docker + docker-compose** | Universal deployment |

---

## 6. TECH STACK (FINAL)

### 6.1 Python Dependencies

```toml
[project]
name = "gulama"
version = "0.1.0"
description = "Secure, open-source personal AI agent platform"
requires-python = ">=3.12"
license = "MIT"

[project.dependencies]
# Gateway
fastapi = ">=0.115"
uvicorn = {version = ">=0.34", extras = ["standard"]}
websockets = ">=14.0"
httpx = ">=0.28"
pydantic = ">=2.10"
pydantic-settings = ">=2.7"

# LLM (Universal — supports 100+ providers)
litellm = ">=1.56"

# Memory & Storage
sqlcipher3 = ">=0.5"
chromadb = ">=0.6"
sentence-transformers = ">=3.3"

# Security
cryptography = ">=44.0"
pyotp = ">=2.9"
keyring = ">=25.0"

# Channels
python-telegram-bot = ">=22.0"

# CLI & Utilities
click = ">=8.1"
rich = ">=13.9"
tomli = ">=2.2"
tomli-w = ">=1.1"
structlog = ">=24.4"
diskcache = ">=5.6"

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.24", "ruff>=0.8", "mypy>=1.13"]
whatsapp = ["whatsapp-web.js-bridge>=1.0"]
discord = ["discord.py>=2.4"]
rust = ["maturin>=1.7"]
```

### 6.2 Rust Components (Hot Paths)

```toml
[package]
name = "gulama-core"
version = "0.1.0"
edition = "2021"

[dependencies]
pyo3 = { version = "0.22", features = ["extension-module"] }
sha2 = "0.10"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

### 6.3 Infrastructure

| Component | Tool |
|-----------|------|
| Containerization | Docker + Docker Compose |
| Reverse Proxy | Caddy (auto-HTTPS) |
| VPN (optional) | WireGuard / Tailscale |
| CI/CD | GitHub Actions |
| SBOM | Syft + Grype |
| Signing | Sigstore cosign |

---

## 7. SECURITY ARCHITECTURE (CORE DIFFERENTIATOR)

### 7.1 Threat Model

**Adversaries:**
1. Remote attacker scanning for exposed instances
2. Malicious skill author uploading backdoored skills
3. Prompt injection via emails, websites, messages
4. Local attacker with physical/network access
5. Supply chain attack via compromised dependency

**Assets to protect:**
- API keys and credentials (ALL providers)
- Personal memory/context
- Host system (filesystem, network, processes)
- Outbound communications (prevent silent exfiltration)

### 7.2 Credential Management

```
User provides API key
  -> Encrypted with age (X25519) or OS keyring
  -> Stored in encrypted vault file (~/.gulama/vault.age)
  -> Decrypted only in-memory, only when needed
  -> Never written to disk unencrypted
  -> Never logged, never in stack traces
  -> Auto-wiped on session end or timeout
```

Cross-platform keyring support:
- macOS: Keychain
- Linux: Secret Service (GNOME Keyring / KDE Wallet)
- Windows: Windows Credential Manager

### 7.3 Memory Encryption

- All memory in SQLCipher (AES-256 encrypted SQLite)
- Encryption key derived from master password via Argon2id
- Vector embeddings in ChromaDB with encrypted storage
- Per-session encryption keys for ephemeral data
- HMAC integrity verification on every memory read

### 7.4 Mandatory Sandboxing (Cross-Platform)

```
Agent wants to run a tool
  -> Policy engine evaluates: allowed? with these params? at this autonomy level?
  -> If denied -> blocked, agent informed, logged
  -> If allowed -> tool runs in platform-appropriate sandbox
  -> Sandbox has: limited filesystem, no network by default,
     restricted syscalls, CPU/memory/time limits
  -> Output captured, sanitized, returned to agent
  -> Sandbox destroyed after execution
```

Platform detection and sandbox selection:

```python
def get_sandbox_backend():
    system = platform.system()
    if system == "Linux":
        if shutil.which("bwrap"):
            return BubblewrapSandbox()
        elif shutil.which("runsc"):
            return GVisorSandbox()
        elif shutil.which("docker"):
            return DockerSandbox()
    elif system == "Darwin":  # macOS
        if shutil.which("sandbox-exec"):
            return AppleSandbox()
        elif shutil.which("docker"):
            return DockerSandbox()
    elif system == "Windows":
        if is_windows_sandbox_available():
            return WindowsSandbox()
        elif shutil.which("docker"):
            return DockerSandbox()
    # Ultimate fallback: subprocess with resource limits
    return ProcessSandbox()
```

### 7.5 Cedar Policy Engine

Every tool call evaluated before execution:

```
# Cedar policy example:
permit(
  principal == User::"owner",
  action == Action::"tool_execute",
  resource == Tool::"web_search"
);

forbid(
  principal,
  action == Action::"tool_execute",
  resource == Tool::"shell_exec"
) when { context.autonomy_level < 3 };

forbid(
  principal,
  action == Action::"file_read",
  resource
) when { resource.path like "*.ssh*" || resource.path like "*.env*" };
```

### 7.6 Canary Token System

- Inject invisible markers into sensitive context
- Task-consistency canaries: verify agent objective pre/post tool call
- If markers appear in output/tool calls -> prompt injection detected
- Session terminated, user alerted, incident logged

### 7.7 Egress Filtering + DLP

- All outbound traffic from sandbox goes through egress proxy
- Domain allowlist (only declared skill permissions)
- DLP scans outbound for: API keys, credentials, PII, sensitive files
- Blocked exfiltration attempts logged and alerted
- Network disabled by default — must be explicitly granted per-skill

### 7.8 Tamper-Proof Audit Logs

- Structured JSON logs with Merkle tree chain integrity
- Every action logged: tool calls, LLM requests, skill installs, config changes
- Each entry contains hash of previous entry -> tampering detectable
- Logs encrypted at rest
- `gulama audit --verify` validates entire chain

### 7.9 Signed Skills (Supply Chain Security)

```
User wants to install a skill
  -> Download skill package
  -> Verify Sigstore cosign signature (missing = REJECT)
  -> Verify SBOM (Software Bill of Materials)
  -> Run Grype vulnerability scan
  -> Static analysis for suspicious patterns
  -> If all pass -> install to sandboxed skill directory
  -> Skill runs ONLY in sandbox with declared permissions
```

---

## 8. UNIVERSAL LLM SUPPORT

### 8.1 Architecture

```python
# LiteLLM handles all provider differences
# User just sets provider + model in config

# config/default.toml
[llm]
provider = "anthropic"          # or "openai", "deepseek", "ollama", etc.
model = "claude-sonnet-4-5-20250929"  # or "gpt-4o", "deepseek-chat", etc.
api_base = ""                   # optional: custom endpoint URL
api_key_name = "ANTHROPIC_API_KEY"  # key name in secrets vault
max_tokens = 4096
temperature = 0.7
daily_token_budget = 500000     # approx $2.50/day at Sonnet pricing

# Fallback chain (optional)
[llm.fallback]
provider = "ollama"
model = "llama3.2"
api_base = "http://localhost:11434"
```

### 8.2 Supported Provider Configuration Examples

```toml
# Anthropic Claude
[llm]
provider = "anthropic"
model = "claude-sonnet-4-5-20250929"

# OpenAI GPT
[llm]
provider = "openai"
model = "gpt-4o"

# DeepSeek
[llm]
provider = "deepseek"
model = "deepseek-chat"
api_base = "https://api.deepseek.com"

# Qwen (Alibaba DashScope)
[llm]
provider = "dashscope"
model = "qwen-max"

# Zhipu GLM
[llm]
provider = "zhipuai"
model = "glm-4"

# Moonshot (Kimi)
[llm]
provider = "moonshot"
model = "moonshot-v1-8k"

# Ollama (local)
[llm]
provider = "ollama"
model = "llama3.2"
api_base = "http://localhost:11434"

# Any OpenAI-compatible endpoint
[llm]
provider = "openai"
model = "my-custom-model"
api_base = "https://my-corp-llm.internal.company.com/v1"

# Groq
[llm]
provider = "groq"
model = "llama-3.3-70b-versatile"
```

### 8.3 LLM Router Implementation

```python
class LLMRouter:
    """
    Universal LLM router using LiteLLM.
    Supports 100+ providers including all Chinese APIs.
    Handles tool use, streaming, fallback chains.
    """

    async def complete(self, messages, tools=None, **kwargs):
        """Send completion request to configured provider."""
        try:
            response = await litellm.acompletion(
                model=f"{self.provider}/{self.model}",
                messages=messages,
                tools=tools,
                api_base=self.api_base,
                api_key=self.vault.get(self.api_key_name),
                **kwargs
            )
            await self.cost_tracker.record(response.usage)
            return response
        except Exception:
            if self.fallback:
                return await self.fallback.complete(messages, tools, **kwargs)
            raise
```

---

## 9. CROSS-PLATFORM SUPPORT

### 9.1 Platform-Specific Modules

| Module | Linux | macOS | Windows |
|--------|-------|-------|---------|
| Sandbox | bubblewrap/gVisor/Docker | sandbox-exec/Docker | Windows Sandbox/Docker/WSL2 |
| Keyring | Secret Service (GNOME/KDE) | macOS Keychain | Windows Credential Manager |
| File paths | ~/.gulama/ | ~/.gulama/ | %APPDATA%/gulama/ |
| Process isolation | Linux namespaces | seatbelt profiles | Job objects |
| Service | systemd | launchd | Windows Service |

### 9.2 Installation Methods

```bash
# Universal (any OS with Python 3.12+)
pip install gulama
gulama setup

# macOS (Homebrew)
brew install gulama

# Linux (one-liner)
curl -fsSL https://gulama.ai/install.sh | bash

# Windows (winget)
winget install gulama

# Docker (any OS)
docker compose up -d

# From source
git clone https://github.com/san-techie21/gulama-bot.git
cd gulama-bot
make setup
```

### 9.3 Data Directory Structure

```
~/.gulama/                      # Linux/macOS: ~/.gulama/
                                # Windows: %APPDATA%/gulama/
├── config.toml                 # User configuration
├── vault.age                   # Encrypted credentials vault
├── memory.db                   # SQLCipher encrypted memory database
├── chroma/                     # ChromaDB vector store
├── audit/                      # Merkle tree audit logs
│   └── chain.jsonl             # Append-only audit chain
├── skills/                     # Installed skills directory
│   └── builtin/                # Built-in skills
├── logs/                       # Application logs (no secrets)
│   └── gulama.log
└── cache/                      # Disk cache
```

---

## 10. COMPONENT SPECIFICATIONS

### 10.1 Gateway (src/gateway/)

Central hub. All messages flow through here.

- FastAPI application with WebSocket support
- Binds to 127.0.0.1:18789 by default (NEVER 0.0.0.0)
- WebSocket origin validation (reject cross-origin)
- TOTP + JWT authentication
- Rate limiting per channel/user
- Health check endpoint (/health)
- Graceful shutdown with session cleanup

API Endpoints:
```
GET  /health                    # Health check
POST /api/v1/message            # Send message (REST)
WS   /api/v1/ws                 # WebSocket connection
GET  /api/v1/sessions           # List active sessions
GET  /api/v1/cost               # Token usage & cost report
POST /api/v1/skills/install     # Install a skill
GET  /api/v1/audit              # View audit logs
POST /api/v1/config             # Update configuration
```

### 10.2 Agent Brain (src/agent/)

Core agent loop: perceive -> think -> act -> respond

```python
async def agent_turn(self, message):
    # 1. BUILD CONTEXT (RAG, not full memory dump)
    context = await self.context_builder.build(message, max_tokens=8000)

    # 2. INJECT CANARY TOKENS
    context = self.canary.inject(context, session_id=message.session_id)

    # 3. CALL LLM (via universal router)
    response = await self.llm_router.complete(
        messages=context.messages,
        tools=self.get_available_tools(message.autonomy_level),
    )

    # 4. PROCESS TOOL CALLS
    while response.has_tool_calls:
        for tool_call in response.tool_calls:
            # 4a. Check canary tokens in tool args
            if leak := self.canary.check_output(str(tool_call)):
                await self.alert_injection(leak, message)
                continue

            # 4b. Cedar policy engine check
            decision = await self.policy.evaluate(tool_call, message)
            if decision.denied:
                await self.notify_user(f"Blocked: {decision.reason}")
                continue

            # 4c. Execute in cross-platform sandbox
            result = await self.sandbox.execute_tool(tool_call)

            # 4d. Egress filter on result
            result = await self.egress_filter.inspect(result)

            # 4e. Log to Merkle audit trail
            await self.audit.log(tool_call, result, decision)

        # 4f. Continue conversation with tool results
        response = await self.llm_router.continue_with_results(results)

    # 5. FINAL OUTPUT CHECK (canary + DLP)
    if leak := self.canary.check_output(response.text):
        await self.alert_injection(leak, message)
        return Response(text="Security alert: potential prompt injection detected.")

    # 6. UPDATE MEMORY (encrypted)
    await self.memory.store(message, response)

    # 7. TRACK COST
    await self.cost_tracker.record(response.usage)

    return Response(text=response.text)
```

### 10.3 Context Builder (RAG Approach)

```python
class ContextBuilder:
    """
    Builds context using RAG, not full memory dump.

    OpenClaw problem: Loads entire SOUL.md + MEMORY.md = thousands of wasted tokens.
    Gulama approach: Retrieve only relevant memory chunks via vector similarity.

    Context budget allocation:
    - System prompt: ~500 tokens
    - Relevant memories: ~2000 tokens (RAG retrieved)
    - Recent conversation: ~3000 tokens (sliding window)
    - User preferences: ~500 tokens
    - Tool descriptions: ~2000 tokens
    - Total: ~8000 tokens (vs OpenClaw's 10,000+ for basic queries)
    """
```

### 10.4 Memory System (src/memory/)

```sql
-- All tables encrypted at rest via SQLCipher (AES-256)
-- Key derived from master password via Argon2id

CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    channel TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    summary TEXT,
    token_count INTEGER DEFAULT 0
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT REFERENCES conversations(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    token_count INTEGER DEFAULT 0,
    embedding_id TEXT
);

CREATE TABLE facts (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    source_message_id TEXT REFERENCES messages(id),
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    embedding_id TEXT
);

CREATE TABLE cost_tracking (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    channel TEXT,
    skill TEXT,
    conversation_id TEXT REFERENCES conversations(id)
);
```

### 10.5 Skills System (src/skills/)

Skill manifest (skill.toml):
```toml
[skill]
name = "web_search"
version = "1.0.0"
description = "Search the web using DuckDuckGo"
author = "Gulama Team"
license = "MIT"

[permissions]
network = ["duckduckgo.com", "html.duckduckgo.com"]
filesystem = []
shell = false
max_memory_mb = 128
max_runtime_seconds = 30

[dependencies]
python = ["duckduckgo-search>=6.0"]

[signature]
cosign_bundle = "..."
```

### 10.6 Autonomy Levels

```toml
[autonomy]
default_level = 2

# Level 0: Ask before every action (observer mode)
# Level 1: Auto-read, ask before writes (assistant mode)
# Level 2: Auto-read/write safe, ask before shell/network (co-pilot mode)
# Level 3: Auto most things, ask before destructive (autopilot-cautious)
# Level 4: Auto everything except financial/credential (autopilot)
# Level 5: Full autonomous — requires explicit opt-in + --i-know-what-im-doing
```

---

## 11. DIRECTORY STRUCTURE

```
gulama-bot/
├── README.md                          # Security-first pitch, comparison table, quick start
├── LICENSE                            # MIT
├── SECURITY.md                        # Security policy, vulnerability reporting
├── CONTRIBUTING.md                    # Contribution guidelines
├── GULAMA_MASTER_SPEC.md             # This document — source of truth
├── pyproject.toml                     # Python project config (uv)
├── Cargo.toml                         # Rust workspace
├── Dockerfile                         # Production container
├── docker-compose.yml                 # Full stack
├── Makefile                           # Common commands
├── .env.example                       # Template (never .env in repo)
│
├── docs/
│   ├── SECURITY.md                    # Security architecture, threat model
│   ├── CONTRIBUTING.md                # Contributor guide
│   ├── SKILLS_DEVELOPMENT.md          # How to build and sign skills
│   ├── DEPLOYMENT.md                  # Production deployment guide
│   ├── COMPARISON_OPENCLAW.md         # Detailed security comparison
│   ├── API.md                         # Gateway API reference
│   └── LLM_PROVIDERS.md              # Supported LLM providers guide
│
├── src/
│   ├── __init__.py
│   ├── main.py                        # Entry point
│   ├── constants.py                   # PROJECT_NAME = "gulama"
│   │
│   ├── gateway/                       # GATEWAY LAYER
│   │   ├── __init__.py
│   │   ├── app.py                     # FastAPI application factory
│   │   ├── config.py                  # Configuration (pydantic-settings)
│   │   ├── router.py                  # Message routing
│   │   ├── websocket.py               # WebSocket server (strict origin)
│   │   ├── auth.py                    # Authentication (TOTP + JWT)
│   │   ├── session.py                 # Session management
│   │   ├── middleware.py              # Rate limiting, CORS, security headers
│   │   └── health.py                  # Health check endpoints
│   │
│   ├── channels/                      # CHANNELS LAYER
│   │   ├── __init__.py
│   │   ├── base.py                    # Abstract channel interface
│   │   ├── telegram.py                # Telegram bot
│   │   ├── whatsapp.py                # WhatsApp adapter
│   │   ├── discord_adapter.py         # Discord bot
│   │   ├── web.py                     # Web UI channel
│   │   └── cli.py                     # CLI channel (dev/testing)
│   │
│   ├── agent/                         # AGENT LAYER
│   │   ├── __init__.py
│   │   ├── brain.py                   # Core agent loop
│   │   ├── llm_router.py             # Universal LLM router (LiteLLM)
│   │   ├── context_builder.py         # RAG-based context assembly
│   │   ├── tool_executor.py           # Sandboxed tool execution
│   │   ├── persona.py                 # Agent personality management
│   │   └── autonomy.py                # Autonomy level controls
│   │
│   ├── security/                      # SECURITY LAYER
│   │   ├── __init__.py
│   │   ├── policy_engine.py           # Cedar policy evaluation
│   │   ├── canary.py                  # Canary token injection & detection
│   │   ├── egress_filter.py           # Outbound traffic monitoring + DLP
│   │   ├── audit_logger.py            # Tamper-proof Merkle tree audit logs
│   │   ├── skill_verifier.py          # Cosign signature verification + SBOM
│   │   ├── secrets_vault.py           # Encrypted credential storage
│   │   ├── sandbox.py                 # Cross-platform sandbox manager
│   │   ├── sandbox_bwrap.py           # bubblewrap backend (Linux)
│   │   ├── sandbox_apple.py           # Apple sandbox backend (macOS)
│   │   ├── sandbox_docker.py          # Docker backend (any OS fallback)
│   │   ├── sandbox_windows.py         # Windows Sandbox backend
│   │   ├── input_validator.py         # Input sanitization
│   │   └── threat_detector.py         # Anomaly detection
│   │
│   ├── memory/                        # PERSISTENCE LAYER
│   │   ├── __init__.py
│   │   ├── store.py                   # Encrypted SQLite memory store
│   │   ├── vector_store.py            # ChromaDB vector storage
│   │   ├── encryption.py              # AES-256-GCM encryption
│   │   ├── schema.py                  # Database schema definitions
│   │   └── migration.py               # Schema migration manager
│   │
│   ├── skills/                        # SKILLS SYSTEM
│   │   ├── __init__.py
│   │   ├── registry.py                # Local skill registry
│   │   ├── loader.py                  # Skill loading with signature verification
│   │   ├── marketplace.py             # Remote marketplace client
│   │   ├── signer.py                  # Skill signing utilities
│   │   ├── scanner.py                 # SBOM + vulnerability scanning
│   │   └── builtin/                   # Built-in skills
│   │       ├── __init__.py
│   │       ├── web_search.py          # Web search (DuckDuckGo/SearXNG)
│   │       ├── file_manager.py        # File operations (sandboxed)
│   │       ├── shell_exec.py          # Shell commands (sandboxed)
│   │       ├── browser.py             # Web browsing (Playwright, sandboxed)
│   │       ├── calendar.py            # Calendar integration
│   │       ├── email.py               # Email (sandboxed)
│   │       ├── notes.py               # Note-taking
│   │       └── code_exec.py           # Code execution (sandboxed)
│   │
│   ├── cli/                           # CLI INTERFACE
│   │   ├── __init__.py
│   │   ├── commands.py                # CLI commands (start, stop, status, audit)
│   │   ├── setup_wizard.py            # Interactive first-time setup
│   │   └── doctor.py                  # Security self-audit
│   │
│   └── utils/                         # SHARED UTILITIES
│       ├── __init__.py
│       ├── crypto.py                  # Cryptographic utilities
│       ├── logging.py                 # Structured logging (JSON, no secrets)
│       ├── cost_tracker.py            # Token usage & cost tracking
│       ├── platform.py                # Cross-platform detection utilities
│       └── telemetry.py               # Anonymous usage metrics (opt-in only)
│
├── rust/                              # RUST HOT PATHS
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs
│       ├── policy_eval.rs             # Fast policy evaluation
│       ├── canary_detect.rs           # Fast canary token detection
│       └── merkle.rs                  # Merkle tree operations
│
├── policies/                          # CEDAR POLICIES
│   ├── default.cedar                  # Default security policy
│   ├── tools.cedar                    # Tool execution policies
│   ├── egress.cedar                   # Outbound traffic policies
│   ├── skills.cedar                   # Skill permission policies
│   └── autonomy.cedar                 # Autonomy level policies
│
├── web/                               # WEB UI (Phase 3)
│   ├── index.html
│   ├── src/
│   │   ├── App.tsx
│   │   ├── Chat.tsx
│   │   ├── Dashboard.tsx
│   │   └── Settings.tsx
│   └── package.json
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_policy_engine.py
│   │   ├── test_canary.py
│   │   ├── test_encryption.py
│   │   ├── test_audit_logger.py
│   │   ├── test_skill_verifier.py
│   │   ├── test_sandbox.py
│   │   ├── test_llm_router.py
│   │   └── test_cost_tracker.py
│   ├── integration/
│   │   ├── test_gateway.py
│   │   ├── test_telegram_channel.py
│   │   ├── test_agent_loop.py
│   │   └── test_memory_store.py
│   └── security/
│       ├── test_prompt_injection.py
│       ├── test_credential_leak.py
│       ├── test_sandbox_escape.py
│       ├── test_websocket_hijack.py
│       └── test_skill_tampering.py
│
├── scripts/
│   ├── install.sh                     # Linux/macOS install script
│   ├── install.ps1                    # Windows install script
│   ├── generate_keys.py               # Generate encryption keys
│   ├── sign_skill.py                  # Sign a skill package
│   ├── migrate_openclaw.py            # OpenClaw migration tool
│   └── security_audit.py              # Self-audit tool
│
└── config/
    ├── default.toml                   # Default configuration (secure)
    └── example.toml                   # Example with comments
```

---

## 12. BUILD ORDER & MILESTONES

### Phase 0: Foundation (Week 1-2) — "It Runs and Talks"

| # | Task | Files | Exit Criteria |
|---|------|-------|---------------|
| 0.1 | Project scaffold | All dirs, pyproject.toml, Makefile | `make setup` works |
| 0.2 | Constants & platform utils | constants.py, utils/platform.py | OS detection works |
| 0.3 | Configuration system | gateway/config.py, config/default.toml | TOML + env override |
| 0.4 | Structured logging | utils/logging.py | JSON logs, secret redaction |
| 0.5 | Secrets vault | security/secrets_vault.py | age encrypt/decrypt, keyring, auto-wipe |
| 0.6 | Encrypted memory store | memory/store.py, encryption.py, schema.py | SQLCipher CRUD |
| 0.7 | Gateway (FastAPI) | gateway/app.py, router.py, websocket.py, auth.py | Starts on 127.0.0.1 |
| 0.8 | CLI skeleton | cli/commands.py, setup_wizard.py | `gulama start/stop/status` |
| 0.9 | Universal LLM router | agent/llm_router.py | Any provider via LiteLLM |
| 0.10 | Basic agent brain | agent/brain.py, context_builder.py | Message -> LLM -> response |
| 0.11 | CLI channel | channels/cli.py | Terminal chat works |
| 0.12 | Telegram channel | channels/telegram.py | Bot receives/sends messages |

**Milestone**: `gulama start` -> Telegram bot responds via user's chosen LLM, memory encrypted

### Phase 1: Security Layer (Week 2-4) — "Try to Hack It"

| # | Task | Files | Exit Criteria |
|---|------|-------|---------------|
| 1.1 | Cedar policy engine | security/policy_engine.py, policies/*.cedar | Deny blocks tool execution |
| 1.2 | Cross-platform sandbox | security/sandbox*.py | Auto-detects OS, isolates tools |
| 1.3 | Sandboxed tool executor | agent/tool_executor.py | Policy -> sandbox -> output |
| 1.4 | Canary token system | security/canary.py | Inject, detect, alert |
| 1.5 | Egress filter + DLP | security/egress_filter.py | Block credential exfiltration |
| 1.6 | Merkle audit logger | security/audit_logger.py, rust/src/merkle.rs | verify_chain() passes |
| 1.7 | Input validator | security/input_validator.py | Injection patterns blocked |
| 1.8 | Skill signing | security/skill_verifier.py, skills/signer.py | Unsigned = rejected |
| 1.9 | Built-in skills | skills/builtin/*.py | web_search, file_manager, shell, notes |
| 1.10 | Threat detector | security/threat_detector.py | Anomaly detection for unusual patterns |
| 1.11 | Rate limiter + circuit breakers | gateway/middleware.py | Action rate limits prevent cascading |
| 1.12 | Security test suite | tests/security/*.py | ALL OpenClaw attacks fail |
| 1.13 | Security audit CLI | cli/doctor.py | `gulama doctor` gives clean report |

**Milestone**: Full security test suite passes. Prompt injection, credential leak, sandbox escape, CSWSH all blocked.

### Phase 2: Memory + UX Polish (Week 4-6) — "Daily Driver"

| # | Task |
|---|------|
| 2.1 | Vector memory (ChromaDB RAG) — semantic retrieval |
| 2.2 | Smart context builder — RAG-based, within 8K token budget |
| 2.3 | Autonomy levels (0-5 with policy enforcement) |
| 2.4 | Cost tracker + dashboard endpoint |
| 2.5 | Persona system (custom system prompts) |
| 2.6 | Memory summarization (periodic compression) |
| 2.7 | Docker setup (docker compose up works end-to-end) |
| 2.8 | Documentation (README, security docs, API docs, LLM providers guide) |
| 2.9 | One-command setup script (install.sh + install.ps1) |
| 2.10 | OpenClaw migration tool |

### Phase 3: Channels + Web UI (Week 6-8)

| # | Task |
|---|------|
| 3.1 | WhatsApp channel |
| 3.2 | Discord channel |
| 3.3 | Web UI (React + Tailwind + WebSocket) |
| 3.4 | Dashboard (cost, usage, audit viewer) |
| 3.5 | Cron/scheduled tasks + heartbeat |
| 3.6 | Slack channel |

### Phase 4: Skills Platform + Advanced (Week 8-12)

| # | Task |
|---|------|
| 4.1 | Skill marketplace (signed-only, auto-scan) |
| 4.2 | SBOM scanner (Syft + Grype) |
| 4.3 | Browser automation (sandboxed Playwright) |
| 4.4 | Voice input/output |
| 4.5 | Email/calendar integration |
| 4.6 | One-click deployment scripts |
| 4.7 | Homebrew formula, winget manifest |

### Phase 5: Enterprise (Week 12-18)

| # | Task |
|---|------|
| 5.1 | RBAC (multi-user) |
| 5.2 | SSO/SAML |
| 5.3 | Team collaboration |
| 5.4 | Compliance reports (SOC2/ISO27001) |
| 5.5 | Pro Cloud SaaS infrastructure |
| 5.6 | Billing system |

---

## 13. SECURITY COMPARISON MATRIX

This table is Gulama's marketing centerpiece. Prominent in README.

| Security Feature | OpenClaw | NanoClaw | **Gulama** |
|-----------------|----------|----------|-----------|
| Credential storage | Plaintext | Config files | **age-encrypted vault + OS keyring** |
| Memory storage | Plain Markdown | Basic | **AES-256 SQLCipher + ChromaDB** |
| Tool execution | Host access default | Container | **Mandatory cross-platform sandbox** |
| WebSocket security | No origin validation | N/A | **Strict origin + JWT** |
| Skills marketplace | No verification (20% malicious) | None | **Cosign signed + SBOM + Grype** |
| Gateway auth | Optional | Basic | **TOTP + JWT + device binding** |
| Gateway binding | 0.0.0.0 (public) | Localhost | **127.0.0.1 (loopback only)** |
| Policy engine | None | None | **Cedar (deterministic zero-trust)** |
| Network access | Unrestricted | Container-limited | **Egress filtering + domain allowlists** |
| Audit logs | Basic files | None | **Tamper-proof Merkle tree chains** |
| Prompt injection defense | LLM judgment | None | **Canary tokens + policy + sanitization** |
| Data exfiltration prevention | None | None | **DLP engine + egress monitoring** |
| LLM support | Multi-provider | Claude only | **100+ providers (LiteLLM)** |
| Platform support | macOS/Linux primary | macOS/Linux | **macOS + Windows + Linux + Docker + ARM** |
| Bug bounty | None | None | **Day one** |
| OWASP Agentic Top 10 | 0/10 | 2/10 | **10/10** |
| Cost control | None | None | **Built-in budgets + tracking** |

---

## 14. OWASP AGENTIC TOP 10 COMPLIANCE

| OWASP Risk | Gulama Mitigation |
|-----------|-------------------|
| **ASI01 — Agent Goal Hijack** | Canary tokens + task-consistency verification + input sanitization |
| **ASI02 — Tool Misuse** | Cedar policy engine (zero-trust, every tool call evaluated) |
| **ASI03 — Identity & Privilege Abuse** | Per-tool scoped permissions, TOTP auth, session isolation |
| **ASI04 — Supply Chain** | Sigstore cosign signing + SBOM + Grype vulnerability scanning |
| **ASI05 — Code Execution** | Mandatory cross-platform sandbox with resource limits |
| **ASI06 — Memory Poisoning** | Encrypted memory + HMAC integrity verification on every read |
| **ASI07 — Inter-Agent Comms** | Signed message passing (when multi-agent added) |
| **ASI08 — Cascading Failures** | Circuit breakers + action rate limits + autonomy levels |
| **ASI09 — Human Trust Exploitation** | Reasoning traces for high-risk actions + confirmation UI |
| **ASI10 — Rogue Agents** | Behavioral anomaly detection + policy engine guardrails |

---

## 15. BUSINESS MODEL

### Open-Core Strategy

| Tier | What's Included | Price |
|------|----------------|-------|
| **Community Edition** | EVERYTHING — gateway, all channels, encrypted memory, sandbox, policy engine, skills, audit logs, cost tracking | **Free forever (MIT)** |
| **Pro Cloud** (future) | Managed hosting, auto-updates, dashboard, team features, 99.9% SLA | ~₹500-2000/mo ($6-25) |
| **Enterprise** (future) | RBAC, SSO/SAML, compliance reports, dedicated support | Custom pricing |
| **Skill Marketplace** (future) | Verified developer listings, featured placements | 15-20% commission |

### Rules

- NO download limits, trial periods, or freemium gates
- The project must feel like a movement, not a product
- Revenue comes from services, not code restrictions
- Open-source credibility fuels ASTRA SHIELD AI enterprise sales

---

## 16. BRANDING & DOMAINS

### Name: Gulama Bot

### Domains (Verified Available Feb 15, 2026)

| Domain | Status | Priority |
|--------|--------|----------|
| **gulama.ai** | AVAILABLE | Primary (secure ASAP) |
| **gulama.dev** | AVAILABLE | Developer docs |
| **gulamabot.com** | AVAILABLE | Backup/redirect |
| **gulama.io** | AVAILABLE | Alternative |
| gulama.com | Taken | — |

### Tagline

**"Your AI. Your Rules. Your Security."**

### Positioning

"OpenClaw, but secure — and works with any LLM, on any platform."

---

## 17. GO-TO-MARKET STRATEGY

| Week | Action |
|------|--------|
| 1 | Secure domains (gulama.ai, gulama.dev, gulamabot.com) |
| 2 | GitHub repo live, README with security comparison |
| 3 | Show HN: "I built the secure, cross-platform alternative to OpenClaw" |
| 4 | YouTube: "10 attacks that work on OpenClaw but FAIL on Gulama" |
| 5 | Security researcher outreach |
| 6 | Indian community launch (FOSS United, BSides Bangalore) |
| 7 | Blog series: "How Gulama stops every OpenClaw CVE" |
| 8 | OpenClaw migration tool launch |
| 10 | Signed skills marketplace |
| 12 | Conference talk submissions (NULLCON, BlackHat Asia) |

### Growth Levers

- "Secure OpenClaw alternative" = SEO gold
- Every OpenClaw CVE disclosure = free marketing for Gulama
- CISM certification = unique credibility
- Works with Chinese APIs = access to massive Chinese developer market
- Works on Windows = access to 75%+ of desktop developers
- Indian market positioning = underserved, cost-sensitive

---

## 18. REFERENCE: OPENCLAW VULNERABILITIES

### CVE-2026-25253 (CVSS 8.8 — HIGH)
- 1-Click RCE via gatewayUrl token exfiltration + CSWSH
- 15,200+ instances vulnerable
- Patched in v2026.1.29

### CVE-2025-59466 — async_hooks DoS
### CVE-2026-21636 — Permission Bypass

### Security Audit: 512 vulnerabilities, 8 critical
### ClawHub: ~900 malicious skills (20% of ecosystem)
### Moltbook: 1.5M API tokens exposed, 35K emails leaked
### Exposed Instances: 42,900+ across 82 countries

---

## 19. REFERENCE: INDUSTRY VERDICTS

| Organization | Verdict |
|-------------|---------|
| Palo Alto Networks | "Potential biggest insider threat of 2026" |
| Cisco | "Exhibit A in How Not To Do AI Security" |
| Kaspersky | "Unsafe for use" |
| Gartner | "Immediately block downloads" |
| SecurityScorecard | 42,900+ exposed instances |
| Bitdefender | ~900 malicious skills (20% of ecosystem) |
| Wiz | 1.5M API tokens exposed via Moltbook |
| Fortune | "Security experts on edge" (Feb 12, 2026) |

---

## 20. IMPLEMENTATION RULES

These rules MUST be followed during ALL implementation:

1. **NEVER store any credential in plaintext** — not in config, memory, logs, or env
2. **NEVER bind to 0.0.0.0** unless user explicitly runs `--bind-public --i-know-what-im-doing`
3. **EVERY tool call goes through the policy engine** — no exceptions
4. **EVERY skill must have a valid cosign signature** — unsigned = refused
5. **EVERY action is audit-logged** with Merkle chain integrity
6. **Context is built via RAG**, not full memory dump — stay within 8K token budget
7. **Security test suite must pass** before any commit to main
8. **WebSocket connections validate origin** — cross-origin = rejected
9. **Sandbox is mandatory** — no disable flag without extreme friction
10. **Cost tracking is always on** — users see exactly what they spend
11. **No platform-specific code in core** — use adapters and runtime detection
12. **No LLM provider preference** — LiteLLM for universal support
13. **Python 3.12+ features** — modern type hints, match/case, etc.
14. **Tests for every component** — especially security components
15. **If it can't be built securely, don't build it**

---

## APPENDIX: QUICK START FOR DEVELOPMENT

When starting implementation:

1. Read this ENTIRE document first
2. Start with Phase 0 — scaffold, config, secrets, memory, gateway, LLM router
3. Use `GULAMA` as the constant everywhere
4. Every component must have tests
5. Security is not optional
6. Follow the directory structure EXACTLY as defined in Section 11
7. All secrets encrypted — if you see a plaintext credential, stop and fix it
8. README leads with the security comparison table from Section 13

---

*Document version: 1.0 | February 15, 2026 | Astra Fintech Labs Pvt. Ltd.*
*Repository: https://github.com/san-techie21/gulama-bot*
