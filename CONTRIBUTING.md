# Contributing

Thanks for your interest in PredictionMarketLLM. This guide covers the workflow for getting a change merged.

## Getting set up

See [README.md](README.md) for the full setup. Quick version:

```bash
uv sync
uv run prek install
docker compose up postgres -d
cd backend/apis/llm && uv sync && uv run alembic -c ../../db/alembic.ini upgrade head
```

Drop a `.env` at the repo root with DB / OpenAI / Qdrant creds. The full variable list is in [CLAUDE.md](CLAUDE.md#local-dev).

## Conventions

These are enforced by review, not tooling — please follow them.

- **One definition per file.** Every `.py` under `backend/` holds exactly one function/class/model; the filename matches the symbol's capitalization (e.g. `PredictorLLM.py`, `get_active_market_ids.py`). The only exceptions are `backend/db/schema.py` and `backend/qdrant/schema.py`, where all schema definitions live together.
- **Deterministic IDs.** Domain rows use `<prefix>_<uuid v5>` derived from stable inputs so re-runs upsert in place. Prefixes live in `backend/db/consts/`.
- **Idempotent writes.** Upserts use `ON CONFLICT DO UPDATE`. `LLMPrediction` is append-only — do not add update logic.
- **No mypy.** [`ty`](https://github.com/astral-sh/ty) is the only type checker.
- **No comments unless the *why* is non-obvious.** Well-named identifiers explain the *what*.

See [CLAUDE.md](CLAUDE.md) for the deeper architecture guide, gotchas, and the rationale behind these conventions.

## Making a change

1. **Branch off `main`.**
2. **Edit code.** If you touch [`backend/db/schema.py`](backend/db/schema.py), generate a migration:
   ```bash
   cd backend/apis/llm
   uv run alembic -c ../../db/alembic.ini revision --autogenerate -m "describe the change"
   ```
   Review the generated revision under [`backend/db/alembic/versions/`](backend/db/alembic/) — autogen misses renames, enum value adds, and expression indexes. Commit the revision alongside the schema change.
3. **Adding an LLM config?** Edit `PredictorLLM.canonical_configs()` and push — the `seed_llm_configs` job reconciles on every deploy. See the [`add-model-config`](.claude/skills/add-model-config/) skill for the recipe.
4. **Run the checks.**
   ```bash
   make check        # ruff lint+format + ty typecheck
   ```
   These also run in CI ([lint.yml](.github/workflows/lint.yml), [typecheck.yml](.github/workflows/typecheck.yml)).
5. **Open a PR against `main`.** Keep the description focused on the *why*; the diff explains the *what*.

## Deploys

Merging to `main` triggers [deploy.yml](.github/workflows/deploy.yml) (GCP) and, for Qdrant cluster changes, [deploy-qdrant.yml](.github/workflows/deploy-qdrant.yml). Migrations apply automatically via the `alembic_migrate` job; LLM configs reconcile via `seed_llm_configs`; Qdrant collections reconcile via `qdrant_sync`. No manual steps after merge.

## Questions

Open an issue or reach out before starting on anything large — happy to sanity-check the approach.
