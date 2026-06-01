# PredictionMarketLLM

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)

Let LLMs play on prediction markets.

Python 3.14, [uv](https://docs.astral.sh/uv/), SQLAlchemy 2 ORM, Cloud SQL Postgres (Alembic-driven migrations), Qdrant Cloud for embeddings, GCP Cloud Run + Cloud Tasks + Cloud Scheduler, Pulumi for infra.

## Requirements

- Python `>=3.14`
- [uv](https://docs.astral.sh/uv/)
- [Docker](https://www.docker.com/) (for the local Postgres)

## Setup

```bash
uv sync                                                            # repo-level deps + prek
uv run prek install

docker compose up postgres -d                                      # local Postgres (mirrors Cloud SQL)

cd backend/apis/llm                                                # any service's venv has alembic
uv sync
uv run alembic -c ../../db/alembic.ini upgrade head                # create the schema locally
```

Drop a `.env` at the repo root with the DB / OpenAI / Qdrant creds (see [CLAUDE.md](CLAUDE.md) for the full list).

## Architecture

Event-driven pipeline running on GCP. A daily Cloud Scheduler cron kicks off the orchestrator; everything after that is Cloud Tasks fan-out between three Cloud Run services.

```
daily cron ──▶ orchestrator /prepare-scraping
                  └─ enqueue 1 bootstrap task ──▶ scrape-markets-polymarket queue
                                                     │
                                                     ▼
                                            polymarket /scrape (one page)
                                                ├─ upsert markets to Postgres
                                                ├─ enqueue next page  ──▶ scrape-markets-polymarket
                                                ├─ per new market     ──▶ save-embeddings-markets queue ──▶ llm /embed-market
                                                └─ per (market × cfg) ──▶ solve-market-llm queue       ──▶ llm /predict
```

### Services ([backend/apis/](backend/apis/))

| Service | Purpose |
| --- | --- |
| [`orchestrator`](backend/apis/orchestrator/) | `POST /prepare-scraping` — cron entry point. Enqueues the bootstrap scrape task. |
| [`polymarket`](backend/apis/polymarket/) | `POST /scrape` — handles one Polymarket CLOB page (one cursor), upserts **all** markets to Postgres (closed ones populate `outcome.market_winner`), enriches the tradeable subset with gamma-api volume/liquidity, then fans out embed + predict tasks for tradeable markets. |
| [`llm`](backend/apis/llm/) | `POST /predict` (one PredictorLLM cycle) + `POST /embed-market` (one market embedding into Qdrant). |

### Infrastructure ([backend/infra/](backend/infra/))

Five Pulumi stacks, deployed by [.github/workflows/deploy.yml](.github/workflows/deploy.yml). `cloud_sql_deployer` runs first; `cloud_run_deployer` depends on it (mounts the Cloud SQL socket); `queue_deployer` + `cron_deployer` depend on `cloud_run_deployer`; `qdrant_deployer` is independent (Qdrant Cloud, not GCP) and runs in parallel via its own workflow.

| Stack | Manages |
| --- | --- |
| [`cloud_sql_deployer`](backend/infra/cloud_sql_deployer/) | The Cloud SQL Postgres instance. (App data lives in the default `postgres` DB; the admin password is set in the GCP UI and stored in GSM.) |
| [`cloud_run_deployer`](backend/infra/cloud_run_deployer/) | Artifact Registry repo + the three Cloud Run services. Reads `instance_connection_name` from `cloud_sql_deployer` via `StackReference` and mounts the Cloud SQL Unix socket on services flagged `needs_cloudsql: true`. |
| [`queue_deployer`](backend/infra/queue_deployer/) | The shared `task-runner` SA + Cloud Tasks queues declared in [backend/queues/](backend/queues/) + IAM bindings. |
| [`cron_deployer`](backend/infra/cron_deployer/) | Cloud Scheduler jobs declared in [backend/crons/](backend/crons/). |
| [`qdrant_deployer`](backend/infra/qdrant_deployer/) | The Qdrant Cloud **cluster** (control plane). Collections are *not* managed here — they live in [backend/qdrant/schema.py](backend/qdrant/schema.py) and are reconciled by the `qdrant_sync` deploy job (`python -m qdrant.sync`). |

GCP resources live in `europe-west3` (Frankfurt); the Qdrant Cloud cluster is in the matching region.

### Storage

| What | Where | Owned by |
| --- | --- | --- |
| Relational data (markets, outcomes, snapshots, configs, predictions) | Cloud SQL Postgres (`prediction-market` instance, default `postgres` DB) | Schema in [backend/db/schema.py](backend/db/schema.py); migrations in [backend/db/alembic/](backend/db/alembic/) applied automatically by the `alembic_migrate` deploy job |
| Embeddings | Qdrant Cloud cluster | Schemas in [backend/qdrant/schema.py](backend/qdrant/schema.py); applied by `python -m qdrant.sync` in the `qdrant_sync` deploy job |
| Raw scraped payloads + raw LLM responses | GCS bucket (`prediction-market-llm-raw`) | Written by the polymarket + llm services via [`RawStore`](backend/raw_store/RawStore.py); pointers stored in `market.raw_path` / `llm_prediction.raw_response_path` |

The DB migration loop: edit `schema.py` → `cd backend/apis/llm && uv run alembic -c ../../db/alembic.ini revision --autogenerate -m "..."` → review the generated revision → commit. The next deploy applies it through the Cloud SQL Auth Proxy.

### Shared libs

Each service's Dockerfile `COPY`s the libs it needs:

| Lib | Used by |
| --- | --- |
| [`backend/db/`](backend/db/) | polymarket, llm — SQLAlchemy schema + queries + Alembic migrations |
| [`backend/qdrant/`](backend/qdrant/) | llm — Qdrant client, collection schema + `sync_collections` |
| [`backend/embedder/`](backend/embedder/) | llm — OpenAI embeddings wrapper |
| [`backend/tasks/`](backend/tasks/) | orchestrator, polymarket — Cloud Tasks `enqueue()` + `QUEUE_DISPATCH_DEADLINES` |
| [`backend/observability/`](backend/observability/) | all three — tracing/log correlation + trace-header propagation |
| [`backend/shared_models/`](backend/shared_models/) | all three — request models for inter-service tasks |
| [`settings/`](settings/) | all three — `Settings` (pulls secrets from GSM when running on Cloud Run) |

## Tooling

```bash
make check        # ruff lint+format + ty typecheck (also runs in CI)
make lint
make format
make typecheck
```

See [CLAUDE.md](CLAUDE.md) for the agent-facing project guide with conventions, gotchas, and local dev recipes.
