.PHONY: install lint typecheck format check

install:
	uv sync
	uv run prek install

lint:
	uv run ruff check --fix --show-fixes

format:
	uv run ruff format

typecheck:
	uv run ty check

check: lint format typecheck
