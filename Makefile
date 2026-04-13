.PHONY: install dev test lint format clean

install:
	cd backend && uv sync

dev:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check app/

format:
	cd backend && uv run ruff format app/

clean:
	cd backend && rm -rf .venv .pytest_cache .ruff_cache .mypy_cache __pycache__
