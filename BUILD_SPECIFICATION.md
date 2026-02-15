# PROJECT SPECIFICATION: Secure Open-Source AI Agent Platform

> **Purpose**: This document is the complete build specification for a secure, open-source alternative to OpenClaw. It contains everything needed to build the project end-to-end — architecture, security requirements, tech stack, file structure, implementation details, business model, and go-to-market strategy. Feed this to Claude Code and start building.

> **Author**: Santosh — Founder & Chief Architect, Astra Fintech Labs Pvt. Ltd., Bengaluru, India  
> **Date**: February 15, 2026  
> **Credentials**: CISM, CCNA | 14+ years enterprise IT security (Honeywell, Huawei, Capgemini, Accolite Digital)  
> **Related Projects**: ASTRA HFT (1.05ns latency trading platform), ASTRA SHIELD AI (cybersecurity platform)

---

## TABLE OF CONTENTS

1. [Project Overview](#1-project-overview)
2. [Why This Exists — OpenClaw Security Analysis](#2-why-this-exists--openclaw-security-analysis)
3. [Name Candidates & Branding](#3-name-candidates--branding)
4. [Business Model](#4-business-model)
5. [Architecture Overview](#5-architecture-overview)
6. [Tech Stack](#6-tech-stack)
7. [Security Architecture (Core Differentiator)](#7-security-architecture-core-differentiator)
8. [Component Specifications](#8-component-specifications)
9. [File & Directory Structure](#9-file--directory-structure)
10. [Implementation Plan & Build Order](#10-implementation-plan--build-order)
11. [Security Comparison Matrix](#11-security-comparison-matrix)
12. [Go-To-Market Strategy](#12-go-to-market-strategy)
13. [Reference: OpenClaw CVEs & Vulnerabilities](#13-reference-openclaw-cves--vulnerabilities)
14. [Reference: Industry Verdicts on OpenClaw](#14-reference-industry-verdicts-on-openclaw)

---

## 1. PROJECT OVERVIEW

### What We're Building

An open-source, security-first personal AI agent platform that does everything OpenClaw does — but with enterprise-grade security baked in from day one. It connects to messaging apps (Telegram, WhatsApp, Discord), executes tasks via tools/skills, maintains persistent encrypted memory, and runs on the user's own hardware.

### The One-Liner

**"OpenClaw, but secure."**

OpenClaw (175K+ GitHub stars, fastest-growing repo in GitHub history) proved massive demand for personal AI agents. But it has critical security flaws: 1-click RCE (CVE-2026-25253, CVSS 8.8), 900 malicious skills in its marketplace, plaintext credential storage, no sandboxing by default, and 42,900+ exposed instances. Every major security vendor (Cisco, Palo Alto, Kaspersky, Gartner) has warned against it.

We build the version that security professionals would actually trust.

### Core Principles

1. **Secure by default** — No insecure configuration should be possible without explicit opt-in
2. **Zero-trust tool execution** — Every tool call goes through a policy engine before running
3. **Encrypted everything** — Memory, credentials, audit logs — all encrypted at rest
4. **Mandatory sandboxing** — All tool execution runs in sandboxes, not on the host
5. **Signed skills only** — No unsigned/unverified code runs, ever
6. **Open-source (MIT/Apache 2.0)** — Full transparency, community audit, viral adoption

### Target Users

- Security-conscious developers and sysadmins
- Teams burned by OpenClaw security issues
- Indian developer community (underserved, cost-sensitive)
- Enterprise security teams evaluating personal AI agents
- Anyone who read the Gartner advisory telling them to block OpenClaw

---

## 2. WHY THIS EXISTS — OPENCLAW SECURITY ANALYSIS

### 2.1 Critical Vulnerabilities (CVEs)

#### CVE-2026-25253 — 1-Click Remote Code Execution (CVSS 8.8)

- **Discovery**: Mav Levin, DepthFirst Security
- **Impact**: Full operator.admin access, sandbox bypass, host-level code execution
- **Mechanism**: Control UI trusted `gatewayUrl` without validation. Attacker crafts a malicious link → victim clicks → browser auto-connects to attacker's WebSocket server → auth token exfiltrated → attacker gains full control
- **Additional vector**: Cross-Site WebSocket Hijacking — no origin validation on WebSocket connections. Works even on localhost-only instances because the browser acts as a pivot
- **Patched**: v2026.1.29 (January 30, 2026)
- **Exposure**: 15,200+ instances vulnerable at time of disclosure (35.4% of all exposed instances)

#### CVE-2025-59466 — async_hooks Denial of Service

- **Impact**: Application crash via untrusted input
- **Root cause**: Node.js async_hooks resource exhaustion

#### CVE-2026-21636 — Permission Bypass

- **Impact**: Unauthorized access to restricted functionality
- **Root cause**: Insufficient authorization checks in gateway API

#### Security Audit Results

- **512 total vulnerabilities** found in comprehensive audit
- **8 classified as critical**
- No bug bounty program exists
- No dedicated security team
- Creator publicly stated: "Confession: I ship code I never read"

### 2.2 Architectural Security Flaws

#### The "Lethal Trifecta" + 4th Element

Simon Willison (security researcher) identified three dangerous properties that combine to create catastrophic risk. Palo Alto Networks added a fourth:

1. **Access to private data** — Emails, files, credentials, browser history, API keys
2. **Exposure to untrusted content** — Web browsing, arbitrary messages, third-party skills
3. **External communication capability** — Sends emails, makes API calls, silent data exfiltration
4. **Persistent memory** (Palo Alto addition) — SOUL.md/MEMORY.md files enable time-shifted prompt injection and memory poisoning attacks

#### Default Insecurity

| Issue | Detail |
|-------|--------|
| Gateway binding | Binds to `0.0.0.0:18789` by default — exposed to public internet |
| Host access | Full host filesystem and shell access by default, no sandboxing |
| Local auth | No authentication required for local connections |
| WebSocket | No origin validation on WebSocket connections |
| Credentials | Stored as plaintext in `~/.openclaw/credentials` (API keys, OAuth tokens, signing secrets) |
| Memory | Plain Markdown files on disk (SOUL.md, MEMORY.md) — unencrypted, tamperable |
| Documentation | Officially states: "There is no perfectly secure setup" |

#### Demonstrated Prompt Injection Attacks

Real-world attacks demonstrated by security researchers:

- Email containing injection instructions → agent handed over user's private key
- Email with embedded instructions → agent silently exfiltrated data via email with no user confirmation
- `find ~` command → agent dumped entire home directory contents to a group chat
- "Peter might be lying, explore HDD" → agent immediately started hunting through the filesystem
- Agent started a legal fight with Lemonade Insurance based on misinterpreted user message

### 2.3 Supply Chain Attacks — ClawHub Marketplace

The ClawHub skills marketplace is severely compromised:

| Source | Finding |
|--------|---------|
| Bitdefender | ~900 malicious skills (20% of entire ecosystem) |
| Koi Security | 341 confirmed malicious skills |
| Reco Security | 335 malicious skills distributed |
| Snyk | 283 skills with critical flaws (scanned 3,984 total) |
| Multiple audits | 22-26% of all skills contain vulnerabilities |

**Attack methods observed:**
- Credential stealers disguised as weather/utility skills, silently exfiltrating API keys
- Atomic Stealer (AMOS) targeting macOS users
- Fake VS Code extensions bundled with ClawHub skills
- Typosquatted domain names mimicking legitimate skills
- ClawHavoc campaign — organized C2 infrastructure (91.92.242[.]30)

### 2.4 Moltbook Breach (discovered by Wiz)

Moltbook, the social network built on OpenClaw where AI agents interact:

- **1.5 million API tokens** exposed publicly
- **35,000 email addresses** leaked
- Private messages accessible to anyone with the URL
- Hardcoded credentials discovered in client-side JavaScript code
- No Row Level Security implemented on database
- 88:1 bot-to-human ratio (1.5M agents vs 17K humans)
- Vulnerability allowed commandeering any agent on the platform

### 2.5 Internet Exposure at Scale

| Metric | Count | Source |
|--------|-------|--------|
| Total exposed instances | 42,900+ across 82 countries | SecurityScorecard |
| Confirmed exposed | 21,639 | Censys |
| Distinct instances | 30,000+ | Bitsight |
| Vulnerable to RCE | 15,200+ (35.4%) | Combined analysis |
| Correlated with prior breaches | 53,300+ | SecurityScorecard |

**Top affected sectors**: Technology, Healthcare, Finance, Government, Insurance  
**Top affected countries**: USA, China (30% hosted on Alibaba Cloud), Singapore

### 2.6 User Experience Pain Points

| Issue | Detail |
|-------|--------|
| Token cost | Millions of tokens/day for routine tasks; Federico Viticci burned 180M tokens |
| Context rot | Performance degrades over time as context accumulates |
| Setup difficulty | Users report $300+, 3+ days to get working; config stripped on restart |
| Open issues | 16,900+ open GitHub issues as of Feb 15, 2026 |
| Autonomy problems | Too passive by default (heartbeat off); too unpredictable when autonomous |
| Memory setup | Not automatic, requires complex manual configuration |

---

## 3. NAME CANDIDATES & BRANDING

**The name has NOT been finalized.** Santosh will choose from these candidates. The codebase should use a configurable project name variable throughout so it can be easily changed.

### Top Candidates (domains verified available Feb 15, 2026)

| Name | Meaning | Available Domains | Vibe |
|------|---------|-------------------|------|
| **Sentina** | Latin for guardian/sentinel | sentina.ai, sentina.dev | Elegant, sophisticated |
| **Vylda** | Norse-inspired, meaning shield | vylda.ai, vylda.dev | Unique, striking, memorable |
| **Kavacha** | Sanskrit (कवच) for armor/shield | kavacha.dev | Indian cultural identity |
| **Aegisbot** | Greek aegis (divine shield of Zeus) | aegisbot.ai, aegisbot.dev | Clear purpose, descriptive |

### Branding Guidelines

- **Tagline**: "Your AI. Your Rules. Your Security."
- **Positioning**: "OpenClaw, but secure" — security-first personal AI agent
- **Tone**: Professional, trustworthy, technically credible
- **Logo direction**: Shield/guardian motif; clean, modern; NOT a cute animal mascot (differentiate from OpenClaw's lobster)
- Use `PROJECT_NAME` as a constant/env variable everywhere in code — easy global rename

---

## 4. BUSINESS MODEL

### Strategy: Open Core (Free Open-Source + Paid Services)

The project is **fully open-source (MIT or Apache 2.0 license)**. This is strategic, not charitable:

1. Free open-source → massive GitHub stars → credibility for ASTRA SHIELD AI enterprise sales
2. Security reputation compounds — every researcher who says "this is solid" evangelizes all of Santosh's products
3. Revenue funnel: Free users → discover ASTRA SHIELD AI → enterprise security conversations → consulting
4. OpenClaw's creator gained more influence than companies with 100x his revenue, purely from open-source credibility

### Revenue Tiers

| Tier | What's Included | Price |
|------|----------------|-------|
| **Community Edition** (fully open-source) | Gateway, channels, encrypted memory, sandbox, policy engine, basic skills, audit logs | **Free forever** |
| **Pro Cloud** (future — hosted SaaS) | Managed hosting, auto-updates, dashboard, team collaboration, 99.9% SLA | ₹500-2000/mo ($6-25) |
| **Enterprise** (future) | RBAC, SSO/SAML, compliance reports (SOC2/ISO27001), dedicated support | Custom pricing |
| **Skill Marketplace** (future) | Developer listings, verified badges, featured placements | 15-20% commission |

### Key Principle

**DO NOT add download limits, trial periods, or freemium gates.** These kill open-source adoption. Nobody stars a repo that says "free for 30 days." The project must feel like a movement, not a product.

---

## 5. ARCHITECTURE OVERVIEW

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MESSAGING CHANNELS                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Telegram │ │ WhatsApp │ │ Discord  │ │  Web UI  │      │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘      │
│       │            │            │             │              │
│       └────────────┴─────┬──────┴─────────────┘              │
│                          │                                    │
│  ┌───────────────────────▼────────────────────────────────┐  │
│  │              GATEWAY (FastAPI + WebSocket)              │  │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │  Auth   │ │ Rate     │ │ Session  │ │ Channel  │  │  │
│  │  │ (mTLS/ │ │ Limiter  │ │ Manager  │ │ Router   │  │  │
│  │  │  TOTP)  │ │          │ │          │ │          │  │  │
│  │  └─────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  └───────────────────────┬────────────────────────────────┘  │
│                          │                                    │
│  ┌───────────────────────▼────────────────────────────────┐  │
│  │              POLICY ENGINE (OPA/Cedar)                  │  │
│  │  Every tool call evaluated against security policies    │  │
│  │  before execution. Deny by default, allow by rule.      │  │
│  └───────────────────────┬────────────────────────────────┘  │
│                          │                                    │
│  ┌───────────────────────▼────────────────────────────────┐  │
│  │              AGENT CORE                                 │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐              │  │
│  │  │   LLM    │ │  Memory  │ │  Skill   │              │  │
│  │  │ Provider │ │  Engine  │ │  Loader  │              │  │
│  │  │(Anthropic│ │(Encrypted│ │ (Signed  │              │  │
│  │  │ /Ollama) │ │ SQLite + │ │  only)   │              │  │
│  │  │          │ │ ChromaDB)│ │          │              │  │
│  │  └──────────┘ └──────────┘ └──────────┘              │  │
│  └───────────────────────┬────────────────────────────────┘  │
│                          │                                    │
│  ┌───────────────────────▼────────────────────────────────┐  │
│  │              SANDBOX (gVisor/bubblewrap/nsjail)         │  │
│  │  All tool execution happens here. No host access.       │  │
│  │  Network egress filtered. Filesystem isolated.          │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              SECURITY LAYER                             │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│  │
│  │  │ Canary   │ │ Egress   │ │  Audit   │ │  DLP     ││  │
│  │  │ Tokens   │ │ Filter   │ │  Logs    │ │ Monitor  ││  │
│  │  │(Prompt   │ │(Outbound │ │(Merkle   │ │(Data Loss││  │
│  │  │ Inject   │ │ traffic  │ │ tree     │ │ Prevent) ││  │
│  │  │ Detect)  │ │ control) │ │ chains)  │ │          ││  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘│  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              ENCRYPTED STORAGE                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐│  │
│  │  │ Secrets Vault │  │ Memory DB    │  │ Config Store ││  │
│  │  │ (age/SOPS/   │  │ (AES-256     │  │ (Encrypted   ││  │
│  │  │  keyring)    │  │  SQLite +    │  │  YAML)       ││  │
│  │  │              │  │  ChromaDB)   │  │              ││  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘│  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python (FastAPI) + Rust hot paths | Python for rapid dev + ecosystem; Rust for crypto/sandbox perf |
| Gateway | FastAPI + uvicorn + WebSocket | Async, fast, well-documented, strict origin validation built-in |
| Memory | Encrypted SQLite + ChromaDB vectors | Structured data + semantic search; all encrypted at rest (AES-256) |
| Secrets | age/SOPS + OS keyring | Never plaintext. `age` for file encryption, keyring for runtime |
| Sandboxing | gVisor (preferred) / bubblewrap / nsjail | Mandatory, not optional. All tool calls run sandboxed |
| Auth | mTLS + TOTP + WireGuard | Defense in depth. No single point of auth failure |
| Policy | OPA (Open Policy Agent) or Cedar | Every tool call evaluated against policies before execution |
| Skills | Sigstore cosign signatures + SBOM | No unsigned code runs. Supply chain integrity via transparency logs |
| Channels | Telegram (MVP) → WhatsApp → Discord → Web UI | Start focused, expand based on demand |
| LLM | Anthropic Claude (primary) + Ollama (local fallback) | Best reasoning + privacy-preserving local option |
| Deployment | Docker + Hetzner/DigitalOcean ($5-10/mo) | Cost-optimized for Indian market |

---

## 6. TECH STACK

### Core Dependencies

```toml
# pyproject.toml (Python project)
[project]
name = "project-agent"  # Replace with chosen project name
version = "0.1.0"
requires-python = ">=3.11"

[project.dependencies]
# Gateway
fastapi = ">=0.115"
uvicorn = {version = ">=0.34", extras = ["standard"]}
websockets = ">=14.0"
httpx = ">=0.28"

# LLM
anthropic = ">=0.43"
ollama = ">=0.4"

# Memory & Storage
sqlcipher3 = ">=0.5"  # Encrypted SQLite
chromadb = ">=0.6"     # Vector embeddings
pydantic = ">=2.10"

# Security
cryptography = ">=44.0"
pyotp = ">=2.9"        # TOTP
keyring = ">=25.0"     # OS-level secret storage

# Channels
python-telegram-bot = ">=22.0"

# Policy Engine
opa-python-client = ">=1.0"  # Or Cedar SDK when available

# Utilities
pyyaml = ">=6.0"
rich = ">=13.0"        # Beautiful CLI output
click = ">=8.1"        # CLI framework
structlog = ">=24.0"   # Structured logging
```

### Rust Components (Optional, Phase 2)

```toml
# Cargo.toml — for performance-critical paths
[package]
name = "agent-core"
version = "0.1.0"

[dependencies]
age = "0.10"           # File encryption
sha2 = "0.10"          # Merkle tree hashing
tokio = { version = "1", features = ["full"] }
```

### Infrastructure

| Component | Tool | Notes |
|-----------|------|-------|
| Containerization | Docker + Docker Compose | Single `docker compose up` to run |
| Sandboxing | gVisor (`runsc`) | Kernel-level sandbox for tool execution |
| Reverse proxy | Caddy (auto-HTTPS) or nginx | TLS termination, rate limiting |
| VPN | WireGuard | Secure remote access without exposing ports |
| CI/CD | GitHub Actions | Automated tests, security scanning, releases |
| SBOM | Syft + Grype | Software bill of materials + vulnerability scanning |
| Signing | Sigstore cosign | Cryptographic skill/release signing |

---

## 7. SECURITY ARCHITECTURE (CORE DIFFERENTIATOR)

This is what makes this project fundamentally different from OpenClaw. Every item below is a **requirement**, not a nice-to-have.

### 7.1 Credential Management

**OpenClaw**: Stores API keys, OAuth tokens, and signing secrets as plaintext in `~/.openclaw/credentials`

**Our approach**:
```
Secrets flow:
  User provides API key
    → Encrypted with age (X25519) or OS keyring
    → Stored in encrypted vault file (~/.agent/vault.age)
    → Decrypted only in-memory, only when needed
    → Never written to disk unencrypted
    → Never logged, never in stack traces
```

Implementation:
- Primary: `age` encryption (X25519) for file-based secrets
- Secondary: OS keyring (macOS Keychain, Linux Secret Service, Windows Credential Manager)
- Fallback: SOPS with age backend
- API keys loaded into environment variables at runtime, never passed as CLI args
- `credentials` file DOES NOT EXIST — there is no plaintext credential file, period

### 7.2 Memory Encryption

**OpenClaw**: Plain Markdown files (SOUL.md, MEMORY.md) — readable by anyone with filesystem access, trivially tamperable for memory poisoning attacks

**Our approach**:
- All memory stored in SQLCipher (AES-256 encrypted SQLite)
- Encryption key derived from user's master password via Argon2id
- Vector embeddings stored in ChromaDB with encrypted storage backend
- Per-session encryption keys for ephemeral data
- Memory integrity verification via HMAC on every read

### 7.3 Mandatory Sandboxing

**OpenClaw**: Tools run on the host by default. Sandboxing is optional and rarely enabled.

**Our approach**:
```
Tool execution flow:
  Agent wants to run a tool
    → Policy engine evaluates: is this tool allowed? for this session? with these params?
    → If denied → tool blocked, agent informed
    → If allowed → tool runs inside gVisor/bubblewrap sandbox
    → Sandbox has: limited filesystem (only /workspace), no network by default,
      restricted syscalls, CPU/memory limits, execution timeout
    → Output captured, sanitized, returned to agent
    → Sandbox destroyed after execution
```

Sandbox capabilities matrix:
| Capability | Default | Can be enabled |
|-----------|---------|----------------|
| Filesystem (read /workspace) | Yes | — |
| Filesystem (write /workspace) | Yes | — |
| Filesystem (read host) | **No** | With explicit policy |
| Network (outbound) | **No** | With explicit allowlist |
| Network (inbound) | **No** | Never |
| Shell execution | Sandboxed only | — |
| Browser | Sandboxed Chromium | With policy |
| System calls | Restricted set | — |

### 7.4 WebSocket Security

**OpenClaw**: No origin validation on WebSocket connections, enabling Cross-Site WebSocket Hijacking (CSWSH)

**Our approach**:
- Strict origin validation on all WebSocket connections
- mTLS (mutual TLS) for all gateway connections
- CORS headers properly configured (no wildcard origins)
- WebSocket connections require valid JWT with short expiry
- Rate limiting on connection attempts
- Gateway binds to **loopback only** (127.0.0.1) by default — no `0.0.0.0`

### 7.5 Signed Skills (Supply Chain Security)

**OpenClaw**: ClawHub has no verification. 20-26% of skills are malicious.

**Our approach**:
```
Skill installation flow:
  User wants to install a skill
    → Download skill package
    → Verify Sigstore cosign signature (if signature missing → REJECT)
    → Verify SBOM (Software Bill of Materials)
    → Run automated security scan (Grype for known CVEs)
    → Static analysis for suspicious patterns (credential access, network calls, obfuscation)
    → If all checks pass → install to sandboxed skill directory
    → Skill runs ONLY inside sandbox with declared permissions
```

Skill manifest (required):
```yaml
# skill.yaml
name: weather-lookup
version: 1.0.0
author: verified-author
license: MIT
permissions:
  network:
    - "api.openweathermap.org"  # Explicit allowlist
  filesystem: none
  shell: false
signature: "cosign://..."
sbom: "syft://..."
```

### 7.6 Prompt Injection Defense

**OpenClaw**: Relies entirely on LLM judgment (which fails regularly)

**Our approach** — defense in depth:

1. **Canary tokens**: Invisible markers injected into context. If these appear in agent output or tool calls, injection detected → session terminated
2. **Input sanitization**: All external content (emails, web pages, messages) processed through a sanitizer before reaching the agent
3. **Output filtering**: Agent responses checked for credential leakage, PII exposure, suspicious URLs
4. **Policy engine**: Even if the agent is tricked, the policy engine blocks unauthorized actions
5. **Action confirmation**: High-risk actions (send email, delete files, make API calls) require user confirmation via the messaging channel
6. **Rate limiting**: Agent can only perform N actions per minute — prevents runaway automation

### 7.7 Audit Logging

**OpenClaw**: Basic log files, no integrity guarantees

**Our approach**:
- Structured JSON logs with tamper-proof Merkle tree chains
- Every action logged: tool calls, LLM requests, skill installations, config changes
- Each log entry contains hash of previous entry → any tampering detectable
- Logs encrypted at rest
- Configurable retention policies
- Export to SIEM (future: Elastic, Splunk, etc.)

### 7.8 Egress Filtering & DLP

**OpenClaw**: No outbound traffic control. Agent can silently exfiltrate data.

**Our approach**:
- All outbound network traffic from sandbox goes through egress proxy
- Proxy maintains domain allowlist (only declared skill permissions)
- DLP engine scans outbound data for: API keys, credentials, PII, sensitive file contents
- Blocked exfiltration attempts logged and alerted
- Network access completely disabled by default — must be explicitly granted per-skill

---

## 8. COMPONENT SPECIFICATIONS

### 8.1 Gateway (`src/gateway/`)

The central control plane. All messages flow through here.

```python
# Key responsibilities:
# 1. Accept connections from channels (Telegram, WhatsApp, etc.)
# 2. Authenticate and authorize requests
# 3. Route messages to the agent core
# 4. Manage sessions and conversation state
# 5. Serve WebSocket API for real-time communication
# 6. Serve Control UI (web dashboard)

# Endpoints:
# POST   /api/v1/message          — Receive message from channel
# GET    /api/v1/sessions         — List active sessions
# GET    /api/v1/sessions/{id}    — Get session details
# POST   /api/v1/skills/install   — Install a skill
# GET    /api/v1/health           — Health check
# WS     /ws                      — WebSocket for real-time updates

# Configuration:
# - Bind: 127.0.0.1:18789 (loopback ONLY by default)
# - Auth: mTLS + TOTP required
# - Rate limit: 60 requests/minute per session
# - Max concurrent sessions: configurable (default 5)
```

### 8.2 Agent Core (`src/agent/`)

The "brain" — handles LLM interactions, tool dispatch, and reasoning.

```python
# Key responsibilities:
# 1. Construct prompts with system instructions + memory + conversation
# 2. Send to LLM provider (Anthropic/Ollama)
# 3. Parse tool calls from LLM response
# 4. Route tool calls through policy engine
# 5. Execute approved tools in sandbox
# 6. Return results to user via channel

# Agent configuration (per-user):
# - Persona (system prompt, name, personality)
# - Model preference (claude-sonnet-4-5-20250929, local llama, etc.)
# - Autonomy level (0=passive, 1=suggest, 2=act-with-confirm, 3=autonomous)
# - Memory settings (retention, summarization frequency)
# - Skill allowlist
```

### 8.3 Memory Engine (`src/memory/`)

Persistent, encrypted, semantically searchable memory.

```python
# Storage layers:
# 1. Short-term: In-memory conversation buffer (last N messages)
# 2. Long-term: SQLCipher database (facts, preferences, history)
# 3. Semantic: ChromaDB vectors (for similarity search over memories)

# Key operations:
# - remember(key, value, metadata) → encrypt and store
# - recall(query, top_k=5) → semantic search over memories
# - forget(key) → secure delete (overwrite + remove)
# - summarize() → periodically compress old memories into summaries

# Encryption:
# - Database: SQLCipher with AES-256-CBC
# - Key derivation: Argon2id from master password
# - Vector store: ChromaDB with encrypted persistence directory
# - All operations via encrypted channels — no plaintext on disk ever
```

### 8.4 Policy Engine (`src/policy/`)

Zero-trust access control for every agent action.

```python
# Policy evaluation flow:
# 1. Agent requests tool execution
# 2. Policy engine receives: {tool, params, session, user, skill}
# 3. Evaluates against policy rules
# 4. Returns: ALLOW, DENY, or ASK_USER

# Default policies (deny-by-default):
# - shell_execute: DENY (requires explicit allowlist)
# - file_read: ALLOW for /workspace only
# - file_write: ALLOW for /workspace only
# - network_request: DENY (requires domain allowlist per-skill)
# - send_email: ASK_USER always
# - send_message: ALLOW for current channel only
# - install_skill: ASK_USER always
# - modify_config: ASK_USER always
# - browser_navigate: ALLOW for allowlisted domains

# Policy format (YAML):
# policies:
#   - name: "allow-weather-api"
#     tool: "http_request"
#     conditions:
#       domain: "api.openweathermap.org"
#       method: "GET"
#     action: "allow"
#
#   - name: "block-credential-access"
#     tool: "file_read"
#     conditions:
#       path_pattern: "*/credentials*|*/.ssh/*|*/.aws/*"
#     action: "deny"
```

### 8.5 Sandbox (`src/sandbox/`)

Isolated execution environment for all tools.

```python
# Sandbox implementation priority:
# 1. bubblewrap (bwrap) — lightweight, widely available on Linux
# 2. gVisor (runsc) — stronger isolation, recommended for production
# 3. nsjail — good middle ground
# 4. Docker — fallback for macOS/Windows

# Sandbox configuration per tool execution:
# - Filesystem: bind-mount /workspace (read-write), /tmp (read-write), everything else denied
# - Network: disabled by default, proxy through egress filter if enabled
# - Resources: CPU limit (1 core), memory limit (512MB), time limit (60s)
# - Syscalls: seccomp filter allowing only safe syscalls
# - User: non-root UID inside sandbox
```

### 8.6 Channel Adapters (`src/channels/`)

Each messaging platform gets an adapter.

```python
# Telegram adapter (MVP):
# - Uses python-telegram-bot library
# - Handles: text, images, documents, voice messages
# - Supports: direct messages + group chats with allowlist
# - Auth: Telegram bot token + user allowlist by Telegram user ID
# - Features: inline keyboard for confirmations, file upload/download

# WhatsApp adapter (Phase 2):
# - Uses Baileys (via subprocess/bridge) or WhatsApp Business API
# - Same message format as Telegram adapter

# Discord adapter (Phase 2):
# - Uses discord.py
# - Supports: DMs + server channels with role-based access

# Web UI adapter (Phase 2):
# - React/vanilla JS frontend served by gateway
# - WebSocket connection for real-time chat
# - Accessible via WireGuard or Tailscale only
```

### 8.7 Skill System (`src/skills/`)

Extensible, verified, sandboxed skills.

```python
# Skill structure:
# skills/
#   weather/
#     skill.yaml          # Manifest (name, permissions, signature)
#     __init__.py          # Entry point
#     handler.py           # Main logic
#     tests/
#       test_handler.py    # Required tests
#     SBOM.json            # Software bill of materials

# Skill lifecycle:
# 1. DISCOVER: Browse verified skill registry
# 2. VERIFY: Check cosign signature + SBOM + security scan
# 3. INSTALL: Copy to sandboxed skill directory
# 4. LOAD: Register tool definitions with agent
# 5. EXECUTE: Run in sandbox with declared permissions only
# 6. UPDATE: Re-verify on every update

# Built-in skills (ship with MVP):
# - shell: Execute shell commands (sandboxed)
# - file_manager: Read/write files (sandboxed workspace)
# - web_search: Search the web via API
# - http_request: Make HTTP requests (with domain allowlist)
# - reminder: Set reminders and cron jobs
# - memory_search: Search long-term memory
```

---

## 9. FILE & DIRECTORY STRUCTURE

```
project-root/
├── README.md                     # Project overview, security comparison, quick start
├── LICENSE                       # MIT or Apache 2.0
├── SECURITY.md                   # Security policy, vulnerability reporting
├── CONTRIBUTING.md               # Contribution guidelines
├── pyproject.toml                # Python project configuration
├── Dockerfile                    # Production container
├── docker-compose.yml            # Full stack with sandbox, proxy, etc.
├── Makefile                      # Common commands (install, test, lint, build)
│
├── src/
│   ├── __init__.py
│   ├── main.py                   # Entry point — CLI (click)
│   ├── config.py                 # Configuration management (encrypted YAML)
│   ├── constants.py              # PROJECT_NAME and other constants
│   │
│   ├── gateway/
│   │   ├── __init__.py
│   │   ├── server.py             # FastAPI app, routes, WebSocket
│   │   ├── auth.py               # mTLS, TOTP, JWT validation
│   │   ├── rate_limiter.py       # Request rate limiting
│   │   └── middleware.py         # Security headers, CORS, origin validation
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── core.py               # Agent loop: receive → think → act → respond
│   │   ├── prompt.py             # System prompt construction
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── anthropic.py      # Claude API integration
│   │   │   ├── ollama.py         # Local model integration
│   │   │   └── base.py           # Abstract LLM provider interface
│   │   └── tools.py              # Tool registry and dispatch
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── engine.py             # Memory CRUD operations
│   │   ├── encryption.py         # AES-256 encryption/decryption
│   │   ├── vector_store.py       # ChromaDB integration
│   │   └── summarizer.py         # Memory compression/summarization
│   │
│   ├── policy/
│   │   ├── __init__.py
│   │   ├── engine.py             # Policy evaluation (allow/deny/ask)
│   │   ├── rules.py              # Default security rules
│   │   └── policies/
│   │       └── default.yaml      # Default policy set
│   │
│   ├── sandbox/
│   │   ├── __init__.py
│   │   ├── executor.py           # Sandboxed execution manager
│   │   ├── bubblewrap.py         # bwrap integration
│   │   ├── gvisor.py             # gVisor/runsc integration
│   │   └── docker_fallback.py    # Docker sandbox for macOS/Windows
│   │
│   ├── channels/
│   │   ├── __init__.py
│   │   ├── base.py               # Abstract channel interface
│   │   ├── telegram.py           # Telegram bot adapter
│   │   ├── whatsapp.py           # WhatsApp adapter (Phase 2)
│   │   ├── discord_adapter.py    # Discord adapter (Phase 2)
│   │   └── webui.py              # Web UI adapter (Phase 2)
│   │
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── loader.py             # Skill discovery, verification, loading
│   │   ├── verifier.py           # Cosign signature + SBOM + security scan
│   │   ├── registry.py           # Installed skills registry
│   │   └── builtin/
│   │       ├── shell.py          # Shell execution (sandboxed)
│   │       ├── file_manager.py   # File operations (sandboxed)
│   │       ├── web_search.py     # Web search
│   │       ├── http_request.py   # HTTP requests (allowlisted)
│   │       ├── reminder.py       # Reminders/cron
│   │       └── memory_search.py  # Search long-term memory
│   │
│   ├── security/
│   │   ├── __init__.py
│   │   ├── vault.py              # Secret management (age/SOPS/keyring)
│   │   ├── canary.py             # Canary token injection + detection
│   │   ├── egress.py             # Outbound traffic filtering
│   │   ├── dlp.py                # Data loss prevention scanning
│   │   ├── audit.py              # Tamper-proof audit logging (Merkle chains)
│   │   └── sanitizer.py          # Input/output sanitization
│   │
│   └── cli/
│       ├── __init__.py
│       ├── setup.py              # Interactive setup wizard
│       ├── doctor.py             # Security audit command
│       └── commands.py           # CLI commands (start, stop, status, audit)
│
├── tests/
│   ├── conftest.py
│   ├── test_gateway/
│   ├── test_agent/
│   ├── test_memory/
│   ├── test_policy/
│   ├── test_sandbox/
│   ├── test_security/
│   └── test_channels/
│
├── configs/
│   ├── default.yaml              # Default (secure) configuration
│   ├── policies/
│   │   └── default.yaml          # Default security policies
│   └── examples/
│       ├── personal.yaml         # Example: personal assistant config
│       └── developer.yaml        # Example: developer-focused config
│
├── docs/
│   ├── architecture.md           # Architecture deep-dive
│   ├── security.md               # Security model documentation
│   ├── skills-guide.md           # How to build skills
│   ├── deployment.md             # Deployment options
│   └── openclaw-comparison.md    # Security comparison with OpenClaw
│
└── scripts/
    ├── install.sh                # One-liner install script
    ├── setup-sandbox.sh          # Install gVisor/bubblewrap
    └── generate-keys.sh          # Generate mTLS certificates
```

---

## 10. IMPLEMENTATION PLAN & BUILD ORDER

### Phase 0: Foundation (Week 1)

**Priority: P0 — Must have before anything else**

1. Project scaffolding (pyproject.toml, directory structure, CI/CD)
2. Configuration system (encrypted YAML config with defaults)
3. Secret management (age encryption, OS keyring integration)
4. CLI skeleton (click-based: `agent setup`, `agent start`, `agent status`, `agent audit`)
5. Structured logging framework
6. Basic test infrastructure (pytest, coverage)

### Phase 1: Core MVP (Weeks 2-4)

**Priority: P0 — Minimum viable secure agent**

1. **Gateway** — FastAPI server with WebSocket, loopback-only binding, auth middleware
2. **Agent Core** — LLM integration (Anthropic Claude), prompt construction, tool dispatch
3. **Memory Engine** — SQLCipher encrypted database, basic CRUD, conversation buffer
4. **Policy Engine** — YAML-based rules, deny-by-default, basic evaluation
5. **Sandbox** — bubblewrap (Linux) / Docker (macOS) integration
6. **Telegram Channel** — Bot adapter, message handling, user allowlist
7. **Built-in Skills** — shell (sandboxed), file_manager, web_search, reminder
8. **Setup Wizard** — Interactive CLI that walks user through first-time setup

### Phase 2: Security Hardening (Weeks 4-6)

**Priority: P0 — Security differentiator**

1. **Canary tokens** — Injection + detection system for prompt injection defense
2. **Egress filtering** — Outbound traffic proxy with domain allowlists
3. **Audit logging** — Merkle tree tamper-proof log chains
4. **Skill verification** — Cosign signature verification + SBOM + security scanning
5. **DLP** — Data loss prevention scanning on outbound data
6. **Input sanitization** — Clean external content before agent processing
7. **mTLS** — Mutual TLS for all gateway connections
8. **Security audit CLI** — `agent audit` command that checks configuration security

### Phase 3: Channels & UX (Weeks 6-8)

**Priority: P1 — Expand reach**

1. WhatsApp adapter (via Baileys or Business API)
2. Discord adapter
3. Web UI (simple React frontend served by gateway)
4. Vector memory (ChromaDB semantic search over memories)
5. Memory summarization (periodic compression of old memories)
6. Heartbeat/cron system (proactive agent actions)
7. Cost dashboard (token spend tracking per task/channel/skill)

### Phase 4: Skills Platform (Weeks 8-10)

**Priority: P1 — Ecosystem**

1. Skill packaging format + specification
2. Verified skill registry (GitHub-based initially)
3. Skill development SDK + documentation
4. Automated security scanning pipeline for submitted skills
5. One-click OpenClaw migration tool (import config, memory, skills)

### Phase 5: Enterprise & Advanced (Weeks 10-16)

**Priority: P2/P3 — Revenue features**

1. RBAC (role-based access control)
2. Team/multi-user support
3. SSO/SAML integration
4. Compliance reporting (SOC2, ISO27001 evidence generation)
5. Browser automation (sandboxed Chromium with CDP)
6. Voice integration
7. Advanced autonomy controls with configurable guardrails

---

## 11. SECURITY COMPARISON MATRIX

This table is the project's marketing centerpiece. It should be prominent in the README.

| Security Feature | OpenClaw | This Project |
|-----------------|----------|--------------|
| Credential storage | Plaintext `~/.openclaw/credentials` | Encrypted vault (age/SOPS/keyring) |
| Memory storage | Plain Markdown files (SOUL.md/MEMORY.md) | AES-256 encrypted SQLite + ChromaDB |
| Tool execution | Host access by default, no sandbox | Mandatory gVisor/bubblewrap sandbox |
| WebSocket security | No origin validation (CSWSH vulnerable) | Strict origin validation + mTLS |
| Skills marketplace | No verification — 20% malicious | Signed (cosign) + SBOM + auto-scan |
| Gateway auth | Optional token/password | mTLS + TOTP + device binding |
| Gateway binding | `0.0.0.0` (public internet) by default | `127.0.0.1` (loopback only) by default |
| Network access | Unrestricted outbound | Egress filtering + domain allowlists |
| Audit logs | Basic text files, no integrity | Tamper-proof Merkle tree chains |
| Prompt injection defense | LLM judgment only | Canary tokens + policy engine + sanitization |
| Data exfiltration prevention | None | DLP engine + egress monitoring |
| Bug bounty | None | Yes, from day one |
| Security team | None | Built by CISM-certified security architect |
| Security posture | "No perfectly secure setup" | **Secure by default** |

---

## 12. GO-TO-MARKET STRATEGY

### Phase 1: Launch (Weeks 1-4)

- **GitHub**: Public repo with security comparison table as first thing in README
- **Launch blog post**: Reference every CVE, every exposure stat, every industry warning about OpenClaw
- **Hacker News**: "Show HN" post — community is primed for OpenClaw security concerns
- **ProductHunt**: Launch with security angle
- **Bug bounty**: Announce from day one (OpenClaw has none)

### Phase 2: Community (Weeks 4-8)

- Engage security researchers who reported OpenClaw issues (Mav Levin, Simon Willison, Jamieson O'Reilly)
- Indian community: FOSS United, IndiaHacks, BSides Bangalore
- Comparison videos: show attacks failing on this project that succeed on OpenClaw
- Signed-only skills marketplace as counter to ClawHub chaos

### Phase 3: Expansion (Weeks 8-16)

- One-click OpenClaw migration tool
- Enterprise security guide for CISOs (Gartner told them to block OpenClaw — offer the alternative)
- Partnership outreach: VirusTotal, Snyk, Bitdefender
- Conference talks: BSides, NULLCON, BlackHat Asia

### Growth Levers

- "Secure OpenClaw alternative" is SEO gold — InfoSec community will share organically
- Every OpenClaw CVE disclosure = free marketing for this project
- CISM certification + enterprise experience = unique credibility signal
- Indian market positioning = underserved, cost-sensitive, large developer base

---

## 13. REFERENCE: OPENCLAW CVEs & VULNERABILITIES

### CVE-2026-25253 (CVSS 8.8 — HIGH)
- **Type**: 1-Click Remote Code Execution
- **Vector**: Token exfiltration via malicious gatewayUrl + Cross-Site WebSocket Hijacking
- **Impact**: Full operator.admin access, sandbox bypass, host-level code execution
- **Discoverer**: Mav Levin, DepthFirst Security
- **Patched**: v2026.1.29 (January 30, 2026)
- **Affected**: 15,200+ exposed instances

### CVE-2025-59466 (async_hooks DoS)
- **Type**: Denial of Service
- **Vector**: async_hooks resource exhaustion via untrusted input
- **Impact**: Application crash

### CVE-2026-21636 (Permission Bypass)
- **Type**: Authorization bypass
- **Vector**: Insufficient authorization checks in gateway API
- **Impact**: Unauthorized access to restricted functionality

### Audit Summary
- 512 total vulnerabilities found
- 8 critical severity
- 42,900+ exposed instances across 82 countries
- 53,300+ instances correlated with prior data breaches

---

## 14. REFERENCE: INDUSTRY VERDICTS ON OPENCLAW

| Organization | Verdict |
|-------------|---------|
| **Palo Alto Networks** | "Potential biggest insider threat of 2026" |
| **Cisco** | "Exhibit A in How Not To Do AI Security" |
| **Kaspersky** | "Unsafe for use" |
| **Gartner** | Immediately block downloads, rotate all credentials, isolate existing instances in VMs |
| **SecurityScorecard** | 42,900+ exposed instances, 53,300+ correlated with breaches |
| **Bitdefender** | ~900 malicious skills (20% of ecosystem) |
| **Snyk** | 283 critical-flaw skills out of 3,984 scanned |
| **Wiz** | 1.5M API tokens exposed via Moltbook breach |

### OpenClaw's Own Admissions
- Documentation states: "There is no perfectly secure setup"
- Creator publicly said: "Confession: I ship code I never read"
- No bug bounty program
- No security team
- No budget allocated for security reports

---

## APPENDIX: QUICK START FOR CLAUDE CODE

When starting a Claude Code session with this document, begin with:

1. **Read this entire document first** — understand the architecture, security requirements, and priorities
2. **Start with Phase 0** — project scaffolding, config system, secret management, CLI
3. **Then Phase 1** — gateway, agent core, memory, policy, sandbox, Telegram
4. **Use `PROJECT_NAME = "agent"` as placeholder** — Santosh will rename later
5. **Every component must have tests** — especially security components
6. **Security is not optional** — if a feature can't be built securely, don't build it
7. **Python 3.11+ required** — use modern features (match/case, type hints, etc.)
8. **Follow the file structure exactly** as defined in Section 9
9. **All secrets encrypted** — if you find yourself writing a plaintext credential, stop and fix it
10. **README should lead with the security comparison table** from Section 11

---

*Document version: 1.0 | February 15, 2026 | Astra Fintech Labs Pvt. Ltd.*
