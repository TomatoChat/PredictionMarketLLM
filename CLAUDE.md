# PredictionMarketLLM — agent guide

Let LLMs play on prediction markets. Python 3.14, `uv`, SQLAlchemy 2 ORM, Cloud SQL Postgres (Alembic for migrations), Qdrant for embeddings, GCP Cloud Run + Cloud Tasks + Cloud Scheduler, Pulumi for infra.

## Layout

| Path | What's there |
| --- | --- |
| `backend/apis/orchestrator/` | Cloud Run service. `POST /prepare-scraping` is the cron entry point — enqueues one bootstrap task to the polymarket scrape queue. |
| `backend/apis/polymarket/` | Cloud Run service. `POST /scrape` handles one Polymarket **CLOB** page (cursor-driven `get_markets`), upserts **all** markets to Postgres (closed ones populate `outcome.market_winner` from `token.winner`), enriches the *tradeable* subset with **gamma-api** volume/liquidity, then enqueues the next page + per-tradeable-market embed + per-(market×config) predict tasks. |
| `backend/apis/llm/` | Cloud Run service. `POST /predict` runs one `PredictorLLM.predict()` cycle. `POST /embed-market` embeds one market into Qdrant. Also owns the `PredictorLLM` glue class + provider implementations under `src/classes/`. |
| `backend/apis/<svc>/deployment.yaml` | Per-service Cloud Run sizing + probes + env vars. Read by `cloud_run_deployer`. The `timeout` must stay ≥ the dispatch deadline of any queue targeting the service (see `QUEUE_DISPATCH_DEADLINES`). |
| `backend/infra/cloud_run_deployer/` | Pulumi stack. Builds each service's image with `pulumi-docker-build`, pushes to gcr.io, deploys as Cloud Run v2. Reads `instance_connection_name` from `cloud_sql_deployer` via `pulumi.StackReference` and mounts it on every service that sets `needs_cloudsql: true`. |
| `backend/infra/cloud_sql_deployer/` | Pulumi stack. Provisions the project's Cloud SQL Postgres 16 instance, application database, and app user. Exports `instance_connection_name` for `cloud_run_deployer` to consume. |
| `backend/infra/queue_deployer/` | Pulumi stack. Creates the shared `task-runner` SA + each Cloud Tasks queue declared under `backend/queues/`, with IAM bindings to invoke the target service. |
| `backend/infra/cron_deployer/` | Pulumi stack. Creates Cloud Scheduler jobs from `backend/crons/<slug>.yaml`. |
| `backend/infra/qdrant_deployer/` | Pulumi stack (Terraform-bridged Qdrant Cloud provider). Manages the Qdrant **cluster** (control plane) only — *not* collections. Deployed by the separate `deploy-qdrant.yml` workflow. Needs the existing cluster `pulumi import`ed first (see its README). |
| `backend/queues/<slug>.yaml` | One file per Cloud Tasks queue. Stem = queue name in GCP. Dispatch deadline is *not* here — it's per-task (see `QUEUE_DISPATCH_DEADLINES`). |
| `backend/crons/<slug>.yaml` | One file per Cloud Scheduler job. |
| `backend/tasks/` | Shared lib: generic `enqueue(queue_name, target_url, payload, task_id?, dispatch_deadline_seconds?)` helper (`google-cloud-tasks`, OIDC as `TASK_RUNNER_SA_EMAIL`). `QUEUE_DISPATCH_DEADLINES.py` is the single source of truth for per-queue task deadlines; `enqueue` applies them by queue name. Copied into each producer service's container. |
| `backend/observability/` | Shared lib: OpenTelemetry tracing + log correlation + trace-header propagation (`inject_trace_headers`). Copied into every service. |
| `backend/db/schema.py` | All SQLAlchemy ORM models (single file): `Market` (+`active`/`closed`/`archived` status), `Outcome` (+`market_winner`), `MarketOutcomeSnapshot` (price/volume/liquidity, active-only), `LLMConfig`, `LLMPrediction`. |
| `backend/db/queries/` | One query helper per file (`get_*.py`, `insert_*.py`, `upsert_*.py`, `deactivate_*.py`). |
| `backend/db/alembic/` | Alembic migration project. `env.py` reads `target_metadata` from `db.schema.Base` and the DSN from `settings.Settings`, so `alembic revision --autogenerate` diffs new revisions against the ORM. Applied automatically by the `alembic_migrate` job in `deploy.yml`. |
| `backend/qdrant/schema.py` | Qdrant collection schemas + the `COLLECTIONS` registry (single file). Shared lib copied into the llm service. |
| `backend/qdrant/consts/`, `backend/qdrant/helpers/`, `backend/qdrant/models/` | Consts (`EMBEDDING_DIMS`), helpers (`get_client`, `ensure_collection`, `sync_collections`, `upsert_market_embeddings`, …), Pydantic models. `python -m qdrant.sync` reconciles every collection in `COLLECTIONS`. |
| `backend/embedder/` | Embedding client (OpenAI `text-embedding-3-large`). Shared lib copied into the llm service. |
| `backend/raw_store/` | `RawStore`: gzip+upload escape-hatch JSON payloads to the `GCS_RAW_BUCKET` (`market.raw_path`, `llm_prediction.raw_response_path`), keeping the blobs out of Postgres. Shared lib copied into the polymarket + llm services. |
| `settings/Settings.py` | Pydantic-settings entry point. Loads from `.env` locally; when `K_SERVICE`/`CLOUD_RUN_JOB` is set, fetches DB_*, OPENAI_API_KEY, QDRANT_* from Google Secret Manager (one secret per field, secret id == field name). |
| `.github/workflows/deploy.yml` | GCP deploy: `cloud_sql_deployer` → (`cloud_run_deployer` → `queue_deployer` ∥ `cron_deployer`) ∥ (`alembic_migrate` → `seed_llm_configs`). `alembic_migrate` runs `alembic upgrade head` through the Cloud SQL Auth Proxy. `seed_llm_configs` reconciles `llm_config` against `PredictorLLM.canonical_configs()` (DB creds from GSM) so config + schema changes both sync on deploy. |
| `.github/workflows/deploy-qdrant.yml` | Qdrant deploy (independent of GCP): `qdrant_sync` (collections, `python -m qdrant.sync`) ∥ `qdrant_deployer` (cluster). |

## Architecture (event-driven, queue fan-out)

```
daily cron ──▶ orchestrator /prepare-scraping
                  └─ enqueue 1 bootstrap task ──▶ scrape-markets-polymarket queue
                                                     │
                                                     ▼
                                            polymarket /scrape (one CLOB page)
                                                ├─ upsert ALL markets + outcomes to Postgres
                                                │    (closed markets set outcome.market_winner)
                                                ├─ gamma-enrich + snapshot the TRADEABLE subset
                                                ├─ enqueue next page   ──▶ scrape-markets-polymarket
                                                ├─ per tradeable mkt   ──▶ save-embeddings-markets queue ──▶ llm /embed-market
                                                └─ per (tradeable × cfg) ─▶ solve-market-llm queue       ──▶ llm /predict
```

Each handler is one small piece. Retries are scoped, failures isolated, pacing comes from queue rate limits.

**Storage vs. fan-out split.** Every market is stored (so closed ones populate `outcome.market_winner` — the scoring ground truth, joined `llm_prediction.outcome_id → outcome.market_winner`). But snapshots (`market_outcome_snapshot`, with gamma volume/liquidity) and embed/predict fan-out happen **only for tradeable markets** (active, open, not archived). Resolution is captured for free on the daily re-scrape: a market that has since closed gets re-upserted with its winner.

## Conventions

- **One definition per file.** Every `.py` under `backend/` holds exactly one function/class/model; filename matches the symbol's capitalization (e.g. `PredictorLLM.py`, `get_active_market_ids.py`, `Market.py`). `schema.py` files (`backend/db/schema.py`, `backend/qdrant/schema.py`) are deliberate exceptions — all schema definitions live in one file per store.
- **Per-service health/ready probes.** Every Cloud Run service exposes `GET /health` and `GET /ready` (no `z` suffix). Wired into `deployment.yaml` startup + liveness probes.
- **Deterministic IDs.** Every domain row uses a `<prefix>_<uuid v5>` id derived from stable inputs (config name, scraped source + source id, etc.) so re-runs upsert in place. Prefixes live in `backend/db/consts/`.
- **Schema changes go through Alembic.** Edit `backend/db/schema.py`, then `cd backend/apis/llm && uv run alembic -c ../../db/alembic.ini revision --autogenerate -m "..."`. Review the generated revision (autogen misses renames, enum value adds, expression indexes). Commit. The next deploy applies it via `alembic_migrate`.
- **Idempotent writes.** Upserts use `ON CONFLICT DO UPDATE`. `LLMPrediction` is append-only.
- **Append-only history.** `llm_prediction` rows accumulate forever; do not add update logic. Predictions cascade-delete with their config (`ondelete="CASCADE"`).
- **Free-tier GCP sizing.** `min_instances: 0`, `max_instances: 1`, `cpu_idle: true`, small mem/cpu in every `deployment.yaml`.

## Local dev

`.env` at the repo root supplies all secrets. Required:

| Var | Notes |
| --- | --- |
| `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` / `DB_NAME` | Postgres connection. Locally use `postgres` / `postgres` / `127.0.0.1` / `5432` / `postgres` against the bundled Docker Postgres. In prod GSM stores Cloud SQL creds; `DB_HOST` is the socket path `/cloudsql/<instance_connection_name>`, `DB_NAME` is `postgres` (the default DB Cloud SQL auto-creates). |
| `DB_SSLMODE` | `disable` locally and on Cloud Run (Unix socket carries no TLS). `require` only for direct TCP to a managed Postgres. |
| `OPENAI_API_KEY` | Required by the llm service. |
| `QDRANT_ENDPOINT` / `QDRANT_API_KEY` | Required by the llm service. |
| `GCS_RAW_BUCKET` | Bucket for offloaded raw payloads (polymarket + llm services). Locally needs ADC (`gcloud auth application-default login`) with write access; on Cloud Run the default compute SA is granted `objectAdmin` by the `cloud_run_deployer` stack. |

Settings auto-loads from `.env` locally; on Cloud Run it pulls the same names from GSM.

Local Postgres + migrations:

```bash
docker compose up postgres -d                                   # start local DB
cd backend/apis/llm
uv sync
uv run alembic -c ../../db/alembic.ini upgrade head             # apply schema
```

To create a new revision after a `schema.py` change:

```bash
cd backend/apis/llm
uv run alembic -c ../../db/alembic.ini revision --autogenerate -m "add foo column"
# review the new file under backend/db/alembic/versions/ before committing
```

Run a service locally:

```bash
cd backend/apis/<service>
uv sync
uv run uvicorn main:app --reload --port 8080
```

Seed canonical LLM configs. This **reconciles**: it upserts every config in `PredictorLLM.canonical_configs()` *and* flips `active = false` on any other row (via `deactivate_llm_configs_except`), so adding/dropping a config in code syncs the DB — no migration. **This runs automatically on every deploy** via the `seed_llm_configs` job in `deploy.yml`, so editing `canonical_configs()` + pushing is all you need. To run it manually (local/ad-hoc), from the llm service venv:

```bash
cd backend/apis/llm
uv run python -c "from src.classes.PredictorLLM import PredictorLLM; PredictorLLM.seed_canonical_configs()"
```

Sync Qdrant collections (reconcile every collection in `COLLECTIONS` — create missing, reconcile payload indexes; idempotent). Run from a venv that has `qdrant-client` (e.g. the llm service's), with `QDRANT_*` set:

```bash
PYTHONPATH=backend python -m qdrant.sync
```

## Gotchas

- **`Base.model_dump()` returns `None` for unset columns.** [`schema.py`](backend/db/schema.py) defines a `model_dump()` helper on the ORM base that walks every column, falling back to `None`. If you pipe that dict into `insert(...).values(...)`, you send explicit `NULL` for columns the caller didn't set — which overrides Postgres `server_default`s and trips NOT NULL constraints. Strip `None` before insert (see [`upsert_llm_configs.py`](backend/db/queries/upsert_llm_configs.py)).
- **Renaming a canonical config changes its id.** The id is `cfg_<uuid5(name)>` — rename → fresh id → the old row would linger. `seed_canonical_configs` reconciles (deactivates every non-canonical row) and runs automatically on every deploy (`seed_llm_configs` job), so a rename/removal retires the old row on push. No manual flip needed.
- **Each Cloud Run service has its own `pyproject.toml` + `.venv`.** Shared libs (`backend/db`, `backend/qdrant`, `backend/embedder`, `backend/raw_store`, `backend/tasks`, `backend/observability`, `backend/shared_models`) are `COPY`'d into containers at build time, not installed as packages. `pyrightconfig.json` in each service adds the repo root to `extraPaths` so editors resolve them. (`from src.classes import PredictorLLM` imports the *module*, not the class — use `from src.classes.PredictorLLM import PredictorLLM`.)
- **`TASK_RUNNER_SA_EMAIL`, `POLYMARKET_SERVICE_URL`, `LLM_SERVICE_URL` are hardcoded in each service's `deployment.yaml`.** They point at the well-known GCP-issued URLs (`https://<slug>-855896249283.europe-west3.run.app`).
- **Scrape source = CLOB `get_markets` (oldest-first), gamma only for volume/liquidity.** The CLOB stream returns the *entire* archive oldest-first, so active markets are deep — a full daily walk is ~1.25M markets / ~1,300 pages (~20 min, paced by `max_dispatches_per_second`). We tried migrating wholesale to gamma but reverted: gamma's default `/markets` excludes closed markets and offset-paginates with a hard cap (~20k; `/markets/keyset` needed beyond), whereas CLOB gives all markets in one deep cursor stream **and** an explicit `token.winner`. Gamma is used only to enrich the tradeable subset's volume/liquidity (batched by `condition_ids`; `conditionId == condition_id`).
- **Dispatch deadline ↔ Cloud Run `timeout` must stay in lockstep.** Per-task deadlines live in [`QUEUE_DISPATCH_DEADLINES.py`](backend/tasks/QUEUE_DISPATCH_DEADLINES.py) (scrape 180 / embed 60 / predict 180) and each must be ≤ the target service's `deployment.yaml timeout` (polymarket 180, llm 180) or Cloud Run kills the request before the deadline fires.
- **Queue concurrency must fit the instance.** A service's capacity is `max_instances × concurrency`. When multiple queues hit the same service their `max_concurrent_dispatches` must sum to ≤ capacity, or excess is 429'd + retried. The llm queues are sized for this: `save-embeddings-markets` (4) + `solve-market-llm` (4) = 8 = llm's `1 × 8`.
- **Qdrant collections are code, the cluster is Pulumi.** Collections live in `schema.py`/`COLLECTIONS` and are reconciled by `qdrant.sync` (`sync_collections` raises on an incompatible vector-size change — that needs a manual recreate+reindex). The cluster is the `qdrant_deployer` Pulumi stack. They deploy via the separate `deploy-qdrant.yml`.
- **Raw payloads live in GCS, not Postgres.** `market.raw_path` / `llm_prediction.raw_response_path` hold `gs://` pointers to gzip'd JSON in `GCS_RAW_BUCKET` (written by [`RawStore`](backend/raw_store/RawStore.py)). The scraper uploads a market's raw **only on first sight** (like embeddings — `upsert_markets` keeps `raw_path` out of its `ON CONFLICT` set, so re-scrapes don't re-upload). Nothing in app code reads these back; they're escape hatches (`gsutil cat … | gunzip`). A failed upload leaves the path `NULL` rather than dropping the row.
- **Multi-row inserts need a homogeneous column set.** Don't strip `None` per-row when nullable columns vary across rows in one batch (e.g. snapshot `volume`/`liquidity`) — SQLAlchemy can't compile it. See [`insert_market_outcome_snapshots.py`](backend/db/queries/insert_market_outcome_snapshots.py).
- **Cloud Run reaches Cloud SQL over a Unix socket, not TCP.** `cloud_run_deployer` mounts the instance via `cloudsql_instances` at `/cloudsql/<instance_connection_name>`. The GSM secret `DB_HOST` is that socket path (starts with `/`); `DB_SSLMODE` must be `disable` (the socket has no TLS layer). The CI `alembic_migrate` + `seed_llm_configs` jobs instead reach the same instance through the Cloud SQL Auth Proxy on `127.0.0.1:5432`, so they override the host/port/sslmode at job scope.

## Tooling

```bash
make check        # ruff lint+format + ty typecheck (also runs in CI)
make lint
make format
make typecheck
```

`ruff` is configured in `pyproject.toml`. `ty` (Astral's type checker, pre-1.0) is the only type checker — do not introduce `mypy`. `backend/infra/`, `backend/apis/`, `backend/crons/`, `backend/tasks/` are excluded from the root ty check (each service has its own venv/typecheck).

CI workflows: [.github/workflows/lint.yml](.github/workflows/lint.yml), [.github/workflows/typecheck.yml](.github/workflows/typecheck.yml), [.github/workflows/deploy.yml](.github/workflows/deploy.yml) (GCP), [.github/workflows/deploy-qdrant.yml](.github/workflows/deploy-qdrant.yml) (Qdrant).

## Available skills

- `.claude/skills/add-model-config/` — use when adding a new LLM config (model × params × tools combo) to the canonical list.
