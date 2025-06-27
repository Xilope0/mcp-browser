# Makefile for MCP Browser
# Created by AI for AI development

.PHONY: test install clean lint docs help run restart stop status

help:
	@echo "MCP Browser Development Commands"
	@echo "================================"
	@echo "make test      - Run all tests (unit + integration)"
	@echo "make install   - Install package in development mode"
	@echo "make run       - Install and restart daemon from home directory"
	@echo "make restart   - Stop and restart daemon (without install)"
	@echo "make stop      - Stop running daemon"
	@echo "make status    - Show daemon status"
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

# Daemon management targets
status:
	@echo "=== MCP Browser Daemon Status ==="
	@if [ -f /tmp/mcp-browser-1004/mcp-browser.pid ]; then \
		pid=$$(cat /tmp/mcp-browser-1004/mcp-browser.pid); \
		echo "PID file exists: $$pid"; \
		if ps -p $$pid > /dev/null 2>&1; then \
			echo "✓ Daemon is running (PID: $$pid)"; \
			ps -fp $$pid; \
		else \
			echo "✗ Daemon not running (stale PID file)"; \
		fi; \
	else \
		echo "✗ No PID file found"; \
	fi

stop:
	@echo "=== Stopping MCP Browser Daemon ==="
	@if [ -f /tmp/mcp-browser-1004/mcp-browser.pid ]; then \
		pid=$$(cat /tmp/mcp-browser-1004/mcp-browser.pid); \
		echo "Stopping daemon (PID: $$pid)..."; \
		if ps -p $$pid > /dev/null 2>&1; then \
			kill -TERM $$pid; \
			sleep 2; \
			if ps -p $$pid > /dev/null 2>&1; then \
				echo "Daemon still running, force killing..."; \
				kill -KILL $$pid; \
			fi; \
			echo "✓ Daemon stopped"; \
		else \
			echo "Daemon was not running"; \
		fi; \
		rm -f /tmp/mcp-browser-1004/mcp-browser.pid; \
	else \
		echo "No PID file found"; \
	fi

restart:
	@echo "=== Restarting MCP Browser Daemon ==="
	$(MAKE) stop
	@echo "Starting daemon from home directory..."
	@cd /mnt/data/claude/claude && nohup /mnt/data/claude/claude/.venv/bin/mcp-browser-daemon > /dev/null 2>&1 &
	@sleep 3
	@echo "Verifying daemon restart..."
	$(MAKE) status

run:
	@echo "=== Installing and Running MCP Browser Daemon ==="
	$(MAKE) install
	$(MAKE) restart