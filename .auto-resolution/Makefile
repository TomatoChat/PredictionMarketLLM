.PHONY: lint typecheck format check

lint:
	uv run ruff check --fix --show-fixes

format:
	uv run ruff format

typecheck:
	uv run ty check

check: lint format typecheck
