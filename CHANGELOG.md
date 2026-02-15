# Changelog

All notable changes to Gulama will be documented in this file.

## [0.2.0] - 2025-02-15

### Added
- **19 built-in skills**: File Manager, Shell Exec, Web Search, Notes, Code Exec, Browser, Email, Calendar, MCP Bridge, Voice, Image Gen, Smart Home, GitHub, Notion, Spotify, Twitter/X, Google Docs, Productivity (Trello/Linear/Todoist/Obsidian), Self-Modify
- **8 communication channels**: CLI, Telegram, Discord, Slack, WhatsApp, Matrix (E2E encrypted), Microsoft Teams, Google Chat
- **GulamaHub marketplace**: Ed25519-signed skill marketplace with search, install, publish
- **Self-modifying skills**: AI can create/test/register its own skills at runtime with security scanning
- **Voice wake word**: "Hey Gulama" via Picovoice Porcupine with energy-based fallback
- **WebSocket debug tools**: Real-time tool call, policy decision, token usage streaming
- **Docker production deployment**: Multi-stage build, Caddy auto-TLS, Watchtower
- **Sub-agent manager**: Spawn background agents for parallel tasks
- **Task scheduler**: Cron, interval, and one-shot task scheduling
- **29 REST API endpoints**: Full gateway API with TOTP authentication
- **CI/CD pipeline**: GitHub Actions with lint, test, security scan, Docker build, PyPI publish
- **Integration tests**: Brain flow, gateway endpoints, skill execution, security pipeline

### Security
- **15+ security mechanisms**: Policy engine, sandbox, canary tokens, audit, DLP, egress filter, RBAC, SSO, threat detection, input validation, security headers
- **Signed marketplace**: Ed25519 mandatory verification for all community skills
- **Self-modifier scanning**: Blocks dangerous code patterns (subprocess, eval, exec, ctypes)

## [0.1.0] - 2025-02-10

### Added
- Initial release with core agent brain
- LiteLLM universal LLM support (100+ providers)
- Encrypted SQLite memory store
- AES-256-GCM secrets vault
- Cedar-inspired policy engine
- bubblewrap sandbox
- Canary token system
- Hash-chain audit logger
- TOTP authentication gateway
- CLI and Telegram channels
- 4 core skills: File Manager, Shell Exec, Web Search, Notes
