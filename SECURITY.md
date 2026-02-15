# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Gulama, please report it responsibly:

1. **DO NOT** open a public GitHub issue for security vulnerabilities
2. Create a [GitHub Issue](https://github.com/san-techie21/gulama-bot/issues/new?template=security.md) with the `security` label
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 1 week
- **Fix release**: Based on severity

## Security Architecture

Gulama implements 15+ security mechanisms:

- AES-256-GCM encryption at rest
- bubblewrap/Docker sandbox for tool execution
- Cedar-inspired deterministic policy engine
- Canary tokens for prompt injection detection
- Hash-chain tamper-proof audit logs
- Egress filtering and DLP
- Ed25519 signed skill marketplace
- TOTP authentication
- Rate limiting
- Input validation and sanitization
- Loopback-only gateway binding
- Threat detection (brute force, privilege escalation)
- RBAC with team management
- SSO/OIDC/SAML support
- Security headers (HSTS, CSP, X-Frame-Options)

## Responsible Disclosure

We appreciate security researchers who help keep Gulama safe. We will:

- Credit you in the release notes (unless you prefer anonymity)
- Work with you to understand and fix the issue
- Not take legal action against good-faith security research
