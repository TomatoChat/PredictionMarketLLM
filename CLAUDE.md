# PredictionMarketLLM — agent guide

Let LLMs play on prediction markets. Python 3.14, `uv`, SQLAlchemy 2 ORM, Supabase/Postgres, Qdrant for embeddings, GCP Cloud Run + Cloud Tasks + Cloud Scheduler, Pulumi for infra.

## Layout

| Path | What's there |
| --- | --- |
| `backend/apis/orchestrator/` | Cloud Run service. `POST /prepare-scraping` is the cron entry point — enqueues one bootstrap task to the polymarket scrape queue. |
| `backend/apis/polymarket/` | Cloud Run service. `POST /scrape` handles one Polymarket page (cursor-driven), upserts to Supabase, then enqueues the next page + per-market embed + per-(market×config) predict tasks. |
| `backend/apis/llm/` | Cloud Run service. `POST /predict` runs one `PredictorLLM.predict()` cycle. `POST /embed-market` embeds one market into Qdrant. Also owns the `PredictorLLM` glue class + provider implementations under `src/classes/`. |
| `backend/apis/<svc>/deployment.yaml` | Per-service Cloud Run sizing + probes + env vars. Read by `cloud_run_deployer`. |
| `backend/infra/cloud_run_deployer/` | Pulumi stack. Builds each service's image with `pulumi-docker-build`, pushes to gcr.io, deploys as Cloud Run v2. |
| `backend/infra/queue_deployer/` | Pulumi stack. Creates the shared `task-runner` SA + each Cloud Tasks queue declared under `backend/queues/`, with IAM bindings to invoke the target service. |
| `backend/infra/cron_deployer/` | Pulumi stack. Creates Cloud Scheduler jobs from `backend/crons/<slug>.yaml`. |
| `backend/queues/<slug>.yaml` | One file per Cloud Tasks queue. Stem = queue name in GCP. |
| `backend/crons/<slug>.yaml` | One file per Cloud Scheduler job. |
| `backend/tasks/` | Shared lib: generic `enqueue(queue_name, target_url, payload)` helper using `google-cloud-tasks` with OIDC signing as `TASK_RUNNER_SA_EMAIL`. Copied into each producer service's container. |
| `backend/supabase/schema.py` | All SQLAlchemy ORM models (single file). |
| `backend/supabase/queries/` | One query helper per file (`get_*.py`, `insert_*.py`, `upsert_*.py`). |
| `backend/supabase/migrations/` | `.sql` migrations applied by the Supabase CLI. |
| `backend/qdrant/schema.py` | Qdrant collection schemas (single file). Shared lib copied into the llm service. |
| `backend/qdrant/consts/`, `backend/qdrant/helpers/`, `backend/qdrant/models/` | Consts (`EMBEDDING_DIMS`), helpers (`get_client`, `ensure_collection`, `upsert_market_embeddings`, …), Pydantic models. |
| `backend/embedder/` | Embedding client (OpenAI `text-embedding-3-large`). Shared lib copied into the llm service. |
| `settings/Settings.py` | Pydantic-settings entry point. Loads from `.env` locally; when `K_SERVICE`/`CLOUD_RUN_JOB` is set, fetches DB_*, OPENAI_API_KEY, QDRANT_* from Google Secret Manager (one secret per field, secret id == field name). |
| `.github/workflows/deploy.yml` | Single sequential workflow: `cloud_run_deployer` → `queue_deployer` → `cron_deployer`, each running `pulumi up --yes --stack prd`. |

## Architecture (event-driven, queue fan-out)

```
daily cron ──▶ orchestrator /prepare-scraping
                  └─ enqueue 1 bootstrap task ──▶ scrape-markets-polymarket queue
                                                     │
                                                     ▼
                                            polymarket /scrape (one page)
                                                ├─ upsert markets to Supabase
                                                ├─ enqueue next page  ──▶ scrape-markets-polymarket
                                                ├─ per new market     ──▶ save-embeddings-markets queue ──▶ llm /embed-market
                                                └─ per (market × cfg) ──▶ solve-market-llm queue       ──▶ llm /predict
```

Each handler is one small piece. Retries are scoped, failures isolated, pacing comes from queue rate limits.

## Conventions

- **One definition per file.** Every `.py` under `backend/` holds exactly one function/class/model; filename matches the symbol's capitalization (e.g. `PredictorLLM.py`, `get_active_market_ids.py`, `Market.py`). `schema.py` files (`backend/supabase/schema.py`, `backend/qdrant/schema.py`) are deliberate exceptions — all schema definitions live in one file per store.
- **Per-service health/ready probes.** Every Cloud Run service exposes `GET /health` and `GET /ready` (no `z` suffix). Wired into `deployment.yaml` startup + liveness probes.
- **Deterministic IDs.** Every domain row uses a `<prefix>_<uuid v5>` id derived from stable inputs (config name, scraped source + source id, etc.) so re-runs upsert in place. Prefixes live in `backend/supabase/consts/`.
- **Idempotent writes.** Upserts use `ON CONFLICT DO UPDATE`. `LLMPrediction` is append-only.
- **Append-only history.** `llm_prediction` rows accumulate forever; do not add update logic. Predictions cascade-delete with their config (`ondelete="CASCADE"`).
- **Free-tier GCP sizing.** `min_instances: 0`, `max_instances: 1`, `cpu_idle: true`, small mem/cpu in every `deployment.yaml`.

## Local dev

`.env` at the repo root supplies all secrets. Required:

| Var | Notes |
| --- | --- |
| `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` / `DB_NAME` | Postgres connection. Use Supabase Session pooler creds (`postgres.<ref>` user). |
| `DB_SSLMODE` | Default `require`. Set to `disable` for local Supabase. |
| `OPENAI_API_KEY` | Required by the llm service. |
| `QDRANT_ENDPOINT` / `QDRANT_API_KEY` | Required by the llm service. |

Settings auto-loads from `.env` locally; on Cloud Run it pulls the same names from GSM.

Local Supabase:

```bash
cd backend/supabase
supabase start     # one-time
supabase db reset  # applies every migration; drops local DB
cd -
```

Run a service locally:

```bash
cd backend/apis/<service>
uv sync
uv run uvicorn main:app --reload --port 8080
```

Seed canonical LLM configs (from inside the llm service venv):

```bash
cd backend/apis/llm
uv run python -c "from src.classes import PredictorLLM; PredictorLLM.seed_canonical_configs()"
```

## Gotchas

- **`Base.model_dump()` returns `None` for unset columns.** [`schema.py`](backend/supabase/schema.py) defines a `model_dump()` helper on the ORM base that walks every column, falling back to `None`. If you pipe that dict into `insert(...).values(...)`, you send explicit `NULL` for columns the caller didn't set — which overrides Postgres `server_default`s and trips NOT NULL constraints. Strip `None` before insert (see [`upsert_llm_configs.py`](backend/supabase/queries/upsert_llm_configs.py)).
- **Renaming a canonical config changes its id.** The id is `cfg_<uuid5(name)>` — rename → fresh id → old row stays in the DB and will still be picked up if `active = true`. Flip the old row to `active = false` (or delete it, accepting the cascade on `llm_prediction`).
- **Each Cloud Run service has its own `pyproject.toml` + `.venv`.** Shared libs (`backend/supabase`, `backend/qdrant`, `backend/embedder`, `backend/tasks`) are `COPY`'d into containers at build time, not installed as packages. `pyrightconfig.json` in each service adds the repo root to `extraPaths` so editors resolve them.
- **`TASK_RUNNER_SA_EMAIL`, `POLYMARKET_SERVICE_URL`, `LLM_SERVICE_URL` are hardcoded in each service's `deployment.yaml`.** They point at the well-known GCP-issued URLs (`https://<slug>-855896249283.europe-west4.run.app`).

## Tooling

```bash
make check        # ruff lint+format + ty typecheck (also runs in CI)
make lint
make format
make typecheck
```

`ruff` is configured in `pyproject.toml`. `ty` (Astral's type checker, pre-1.0) is the only type checker — do not introduce `mypy`. `backend/infra/`, `backend/apis/`, `backend/crons/`, `backend/tasks/` are excluded from the root ty check (each service has its own venv/typecheck).

CI workflows: [.github/workflows/lint.yml](.github/workflows/lint.yml), [.github/workflows/typecheck.yml](.github/workflows/typecheck.yml), [.github/workflows/deploy.yml](.github/workflows/deploy.yml).

## Available skills

- `.claude/skills/add-model-config/` — use when adding a new LLM config (model × params × tools combo) to the canonical list.
