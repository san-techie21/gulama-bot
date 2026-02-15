# Contributing to Gulama

Thank you for your interest in contributing to Gulama! This guide will help you get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/san-techie21/gulama-bot.git
cd gulama-bot

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Verify installation
python -m pytest tests/ -v
gulama doctor
```

## Project Structure

```
src/
  agent/        # Brain, LLM router, context builder, tool executor
  channels/     # CLI, Telegram, Discord, Slack, WhatsApp, Matrix, Teams, Google Chat
  cli/          # CLI commands and setup wizard
  gateway/      # FastAPI server, auth, middleware, health, WebSocket
  memory/       # Encrypted SQLite storage, schema, encryption
  security/     # Policy engine, sandbox, canary, audit, DLP, egress filter
  skills/       # All 19 built-in skills + marketplace + self-modifier
  utils/        # Logging, platform detection
tests/
  integration/  # End-to-end pipeline tests
  security/     # Security-specific tests
  unit/         # Unit tests
```

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Integration tests only
python -m pytest tests/integration/ -v

# Security tests only
python -m pytest tests/security/ -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# Single test file
python -m pytest tests/integration/test_agent_flow.py -v
```

## Code Style

We use **Ruff** for linting and formatting:

```bash
# Check lint
ruff check src/ tests/

# Auto-fix
ruff check --fix src/ tests/

# Format
ruff format src/ tests/
```

Configuration is in `pyproject.toml`.

## Creating a New Skill

All skills implement the `BaseSkill` interface:

```python
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.security.policy_engine import ActionType

class MySkill(BaseSkill):
    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="my_skill",
            description="What my skill does",
            version="1.0.0",
            author="your-name",
            required_actions=[ActionType.NETWORK_REQUEST],
            is_builtin=True,
        )

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        # Your logic here
        return SkillResult(success=True, output="Result")

    def get_tool_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "my_skill",
                "description": "What my skill does",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "Action to perform"},
                    },
                    "required": ["action"],
                },
            },
        }
```

Register it in `src/skills/registry.py`:

```python
optional_skills = [
    # ...existing skills...
    ("my_skill", "src.skills.builtin.my_skill", "MySkill"),
]
```

## Security Guidelines

Gulama's #1 priority is security. All contributions must:

1. **Never log secrets** — API keys, tokens, passwords must never appear in logs
2. **Use the policy engine** — All actions go through `PolicyEngine.check()`
3. **Sandbox execution** — Tool calls run inside the security sandbox
4. **Validate input** — Use `InputValidator` for all user-provided data
5. **Audit everything** — Log actions via `AuditLogger`
6. **Sign community skills** — Ed25519 signatures are mandatory for marketplace

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Add tests for new functionality
5. Run the full test suite: `python -m pytest tests/ -v`
6. Run linting: `ruff check src/ tests/`
7. Commit with a descriptive message
8. Push and open a PR

### PR Checklist

- [ ] Tests pass (`python -m pytest tests/ -v`)
- [ ] Linting passes (`ruff check src/ tests/`)
- [ ] New features have tests
- [ ] Security implications considered
- [ ] Documentation updated if needed

## Reporting Issues

- **Bug reports**: Use the "Bug Report" issue template
- **Feature requests**: Use the "Feature Request" issue template
- **Security vulnerabilities**: Use the "Security" label — we treat these with highest priority

## Code of Conduct

Be respectful, constructive, and collaborative. We're building security-first software — that philosophy extends to how we treat each other.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
