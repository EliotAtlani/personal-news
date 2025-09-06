# Personal News - Development Commands

.PHONY: help install lint format fix check test clean

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync

lint: ## Run ruff linter (check only)
	uv run ruff check src/

format: ## Format code with black
	uv run black src/

fix: ## Auto-fix linting issues with ruff
	uv run ruff check --fix src/

check: ## Run all checks (lint + format check)
	uv run ruff check src/
	uv run black --check src/

test: ## Run tests
	uv run pytest

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete

# Newsletter commands
run-tech: ## Run tech newsletter
	uv run python run.py run --profile tech

run-geo: ## Run geopolitics newsletter  
	uv run python run.py run --profile geopolitics

run-ai: ## Run AI newsletter
	uv run python run.py run --profile ai

test-email: ## Send test email
	uv run python run.py test

# Development workflow
dev-setup: install ## Set up development environment
	@echo "Development environment ready!"
	@echo "Run 'make help' to see available commands"

dev-check: fix format check ## Complete development check (fix, format, check)
	@echo "Development checks completed!"