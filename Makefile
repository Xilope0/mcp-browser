# Makefile for MCP Browser
# Created by AI for AI development

.PHONY: test install clean lint docs help

help:
	@echo "MCP Browser Development Commands"
	@echo "================================"
	@echo "make test      - Run all tests (unit + integration)"
	@echo "make install   - Install package in development mode"
	@echo "make lint      - Run code quality checks"
	@echo "make docs      - Generate AI-friendly documentation"
	@echo "make clean     - Remove build artifacts"

test:
	python setup.py test

install:
	pip install -e .[dev]

lint:
	@echo "Running code quality checks..."
	@python -m ruff check mcp_browser/ mcp_servers/ || true
	@python -m mypy mcp_browser/ --ignore-missing-imports || true
	@python -m black --check mcp_browser/ mcp_servers/ || true

docs:
	python setup.py aidocs

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -f .tags *.html

# Quick test targets
test-unit:
	pytest tests/ -v --ignore=tests/test_integration.py

test-integration:
	python tests/test_integration.py

# Development helpers
format:
	black mcp_browser/ mcp_servers/ tests/

typecheck:
	mypy mcp_browser/ --ignore-missing-imports