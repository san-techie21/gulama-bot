.PHONY: setup install dev test lint format run clean audit docker

# Default target
help:
	@echo "Gulama Bot - Secure Personal AI Agent"
	@echo ""
	@echo "Usage:"
	@echo "  make setup      - First-time setup (install deps + generate keys)"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Install with dev dependencies"
	@echo "  make run        - Start Gulama"
	@echo "  make test       - Run all tests"
	@echo "  make test-security - Run security test suite"
	@echo "  make lint       - Run linter"
	@echo "  make format     - Auto-format code"
	@echo "  make audit      - Run security self-audit"
	@echo "  make docker     - Build and run with Docker"
	@echo "  make clean      - Clean build artifacts"

setup: install
	python -m src.cli.commands setup

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

run:
	python -m src.main

test:
	pytest tests/ -v --tb=short

test-security:
	pytest tests/security/ -v --tb=long

lint:
	ruff check src/ tests/
	mypy src/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

audit:
	python -m src.cli.commands doctor

docker:
	docker compose up -d

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
