# PredictionMarketLLM

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)

Let LLMs play on prediction markets.

## Requirements

- Python `>=3.14`
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
uv run pre-commit install
```

## Architecture

Event-driven pipeline running on GCP. A daily Cloud Scheduler cron kicks off the orchestrator; everything after that is Cloud Tasks fan-out between three Cloud Run services.

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

### Services ([backend/apis/](backend/apis/))

| Service | Purpose |
| --- | --- |
| [`orchestrator`](backend/apis/orchestrator/) | `POST /prepare-scraping` — cron entry point. Enqueues the bootstrap scrape task. |
| [`polymarket`](backend/apis/polymarket/) | `POST /scrape` — handles one Polymarket CLOB page (one cursor), upserts **all** markets to Supabase (closed ones populate `outcome.market_winner`), enriches the tradeable subset with gamma-api volume/liquidity, then fans out embed + predict tasks for tradeable markets. |
| [`llm`](backend/apis/llm/) | `POST /predict` (one PredictorLLM cycle) + `POST /embed-market` (one market embedding into Qdrant). |

### Infrastructure ([backend/infra/](backend/infra/))

Four Pulumi stacks, deployed by [.github/workflows/deploy.yml](.github/workflows/deploy.yml). `cloud_run_deployer` runs first; `queue_deployer` + `cron_deployer` depend on it; `qdrant_deployer` is independent (Qdrant Cloud, not GCP) and runs in parallel.

| Stack | Manages |
| --- | --- |
| [`cloud_run_deployer`](backend/infra/cloud_run_deployer/) | Artifact Registry repo + the three Cloud Run services. |
| [`queue_deployer`](backend/infra/queue_deployer/) | The shared `task-runner` SA + Cloud Tasks queues declared in [backend/queues/](backend/queues/) + IAM bindings. |
| [`cron_deployer`](backend/infra/cron_deployer/) | Cloud Scheduler jobs declared in [backend/crons/](backend/crons/). |
| [`qdrant_deployer`](backend/infra/qdrant_deployer/) | The Qdrant Cloud **cluster** (control plane). Collections are *not* managed here — they live in [backend/qdrant/schema.py](backend/qdrant/schema.py) and are reconciled by the `qdrant_sync` deploy job (`python -m qdrant.sync`). |

GCP resources live in `europe-west3` (Frankfurt); the Qdrant Cloud cluster is in the matching region.

### Shared libs

Each service's Dockerfile `COPY`s the libs it needs:

| Lib | Used by |
| --- | --- |
| [`backend/supabase/`](backend/supabase/) | polymarket, llm — SQLAlchemy schema + queries |
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
