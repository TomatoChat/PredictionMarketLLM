# PredictionMarketLLM — agent guide

Let LLMs play on prediction markets. Python 3.14, `uv`, SQLAlchemy 2 ORM, Supabase/Postgres, GitHub Actions cron.

## Layout

| Path | What's there |
| --- | --- |
| `backend/crons/` | Scheduled jobs. `scrape_markets/` and `predict_markets/` each have a `main.py`, a `helpers/` package, and a sub-README. |
| `backend/llm/classes/PredictorLLM.py` | Glue: one instance per `llm_config` row, resolves provider via `LLMRegistry`, runs the prompt → predict → insert cycle. Also owns `canonical_configs()` / `seed_canonical_configs()` — the source of truth for which configs the project considers seedable. |
| `backend/llm/classes/providers/` | One file per provider (`OpenAI.py`, …) implementing `LLMProvider.predict()`. |
| `backend/llm/models/`, `backend/llm/prompts/` | Pydantic input/output models and Jinja templates for prompts. |
| `backend/supabase/schema.py` | All SQLAlchemy ORM models (single file). |
| `backend/supabase/queries/` | One query helper per file (`get_*.py`, `insert_*.py`, `upsert_*.py`). |
| `backend/supabase/migrations/` | `.sql` migrations applied by the Supabase CLI. |
| `backend/polymarket/`, `backend/kalshi/` | Source-specific scrapers / API clients consumed by `scrape_markets`. |
| `settings/get_settings.py` | Pydantic-settings entry point. `Settings()` is constructed eagerly at module load by several files — see gotchas. |
| `.github/workflows/predict_markets.yml` | The only active workflow. Runs `polymarket` job (scrape) then `predict` job (predictions) every 4h UTC. |

## Conventions

- **One definition per file.** Every `.py` under `backend/` holds exactly one function/class/model, and the filename matches the symbol's capitalization (e.g. `PredictorLLM.py`, `get_active_market_ids.py`, `Market.py`). `schema.py` is the deliberate exception (all ORM models live there). When adding a helper, create a new file and re-export it from the package's `__init__.py`.
- **Deterministic IDs.** Every domain row uses a `<prefix>_<uuid v5>` id derived from stable inputs (config name, scraped source + source id, etc.) so re-runs upsert in place. Prefixes live in `backend/supabase/consts/`.
- **Idempotent writes.** Upserts use `ON CONFLICT DO UPDATE`. `LLMPrediction` is append-only.
- **Append-only history.** `llm_prediction` rows accumulate forever; do not add update logic. Predictions cascade-delete with their config (`ondelete="CASCADE"`).

## Local dev

`.env` at the repo root supplies all secrets. Required:

| Var | Notes |
| --- | --- |
| `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` / `DB_NAME` | Postgres connection. Use Supabase Session pooler creds (`postgres.<ref>` user). |
| `DB_SSLMODE` | Default `require`. Set to `disable` for local Supabase. |
| `OPENAI_API_KEY` | **Required at import time** — see gotchas. |

Local Supabase:

```bash
cd backend/supabase
supabase start     # one-time
supabase db reset  # applies every migration; drops local DB
cd -
```

Run a cron locally:

```bash
# scrape one source (only Polymarket is wired into SCRAPERS today)
uv run python -c "from backend.crons.scrape_markets.helpers import scrape_polymarket; raise SystemExit(0 if scrape_polymarket() else 1)"

# seed canonical LLM configs
uv run python -m backend.llm.classes.PredictorLLM

# predict (full CLI: --config, --market-id, --dry-run)
uv run python -m backend.crons.predict_markets --config <name> --market-id <mkt_…> --dry-run
```

`--dry-run` calls the provider and logs the chosen outcome + token counts without writing the `llm_prediction` row. Always start here when iterating locally.

## Schema gotchas

- **`Base.model_dump()` returns `None` for unset columns.** [`schema.py`](backend/supabase/schema.py) defines a `model_dump()` helper on the ORM base that walks every column, falling back to `None`. If you pipe that dict into `insert(...).values(...)`, you send explicit `NULL` for columns the caller didn't set — which overrides Postgres `server_default`s and trips NOT NULL constraints (`created_at` is the obvious one). Strip `None` values before insert (see `backend/supabase/queries/upsert_llm_configs.py` for the pattern).
- **`OPENAI_API_KEY` required at import time.** Several modules call `get_settings()` at top-level (e.g. `backend/llm/classes/providers/OpenAI.py`, `backend/crons/scrape_markets/helpers/scrape_kalshi.py`). Importing `backend.crons.scrape_markets.helpers` for any reason pulls Settings in. CI must supply `OPENAI_API_KEY` even in jobs that only scrape.
- **Renaming a canonical config changes its id.** The id is `cfg_<uuid5(name)>` — rename → fresh id → old row stays in the DB and will still be picked up by `predict_all_configs` if `active = true`. Flip the old row to `active = false` (or delete it, accepting the cascade on `llm_prediction`).

## Workflow safety

`.github/workflows/predict_markets.yml` runs against the `prd` GitHub Environment by default. `prd` has required-reviewer protection rules, so a scheduled cron currently waits for approval. The pattern is to have a sibling `prd-cron` environment with the same secrets and no required reviewers, and route `github.event_name == 'schedule'` to it (see commit history / open PRs).

## Tooling

```bash
make check        # ruff lint+format + ty typecheck (also runs in CI)
make lint
make format
make typecheck
```

`ruff` is configured in `pyproject.toml`. `ty` (Astral's type checker, pre-1.0) is the only type checker — do not introduce `mypy`. CI workflows: `.github/workflows/lint.yml`, `typecheck.yml`.

## Available skills

- `.claude/skills/add-model-config/` — use when adding a new LLM config (model × params × tools combo) to the canonical list.
