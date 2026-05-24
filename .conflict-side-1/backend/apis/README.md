# backend/apis

One subdirectory per Cloud Run **service**. Each service is a FastAPI app with its own Docker image, deployed declaratively by [../infra/cloud_run_deployer](../infra/cloud_run_deployer).

## Layout

```
backend/apis/<slug>/
├── __init__.py         # local-import bootstrap (adds backend/ to sys.path)
├── Dockerfile          # builds the container image (build context = repo root)
├── .dockerignore
├── deployment.yaml     # DeploymentConfig (snake_case keys; see deployer src/models/DeploymentConfig.py)
├── pyproject.toml      # service-only deps installed inside the image
├── pyrightconfig.json  # IDE extra-paths so `from supabase import …` resolves locally
├── main.py             # FastAPI app entry — creates `app`, includes the routers
└── src/
    ├── routes/         # one route per file; each exports `router = APIRouter()`
    ├── classes/        # one class per file
    ├── helpers/        # one helper per file
    └── models/         # one Pydantic request/response model per file
```

`main.py` runs at the container's `/app/` root, importing `from src.routes import …`. Shared libraries get copied next to `src/` at build time (see "Shared libs" below).

## Service convention

| Concept | Convention | Example |
|---|---|---|
| Directory name | `snake_case` matching the Python identifier | `predict_markets` |
| `service_slug` in `deployment.yaml` | `kebab-case`, max 63 chars (Cloud Run naming) | `predict-markets` |
| Route file | snake_case (`<route>.py`), exports `router` | `routes/run.py` |
| Pydantic model file | PascalCase matching the class | `models/RunRequest.py` |
| Route handler signature | `def handler(request: <X>Request) -> <X>Response` | see [llm/predict.py](llm/src/routes/predict.py) |
| Response decorator | `@router.<verb>(..., response_model=<X>Response, response_model_exclude_none=True)` | every route |

Every service exposes `/healthz` and `/readyz` — Cloud Run uses them for startup + liveness probes.

## Shared libs

Each service's [Dockerfile](kalshi/Dockerfile) `COPY`s the shared backend libraries from the repo root into `/app/` alongside `src/`:

```dockerfile
COPY backend/llm       ./llm        # llm domain logic (PredictorLLM, providers, prompts)
COPY backend/embedder  ./embedder   # OpenAI Embedder wrapper
COPY backend/qdrant    ./qdrant     # Qdrant client + schema
COPY backend/supabase  ./supabase   # SQLAlchemy ORM + queries
COPY settings          ./settings   # pydantic-settings Settings()
```

Inside the container the imports look "as if at the top level": `from supabase import LLMConfig`, `from qdrant import MARKETS`, `from llm import PredictorLLM`, `from settings import get_settings`. The same imports resolve in the IDE because each service has a [pyrightconfig.json](kalshi/pyrightconfig.json) with `extraPaths` pointing at `backend/` and the repo root.

The service's own [pyproject.toml](kalshi/pyproject.toml) lists every third-party dep used directly OR transitively — including `sqlalchemy`, `qdrant-client`, `openai`, etc., when the service uses any shared lib that needs them.

## Services in this repo

| Slug | Purpose | Routes |
|---|---|---|
| [kalshi](kalshi) | Kalshi data fetch + scrape | `GET /markets`, `POST /scrape` |
| [polymarket](polymarket) | Polymarket data fetch + scrape | `GET /markets`, `POST /scrape` |
| [llm](llm) | One-shot LLM prediction | `POST /predict` |
| [predict_markets](predict_markets) | Orchestrator: loops configs × markets via `PredictorLLM` | `POST /run` |

`predict_markets` is the cron target — the [cron_deployer](../infra/cron_deployer) creates a Cloud Scheduler entry that POSTs to `predict-markets/run` every 4 hours.

## Deploy

Push to `main` touching `backend/apis/**` (or any of the shared libs the services copy in) — [.github/workflows/deploy_apis.yml](../../.github/workflows/deploy_apis.yml) runs `pulumi up` against [../infra/cloud_run_deployer](../infra/cloud_run_deployer) and reconciles every service in one pass.

Locally:

```bash
cd backend/infra/cloud_run_deployer
pulumi stack select prd
pulumi up
```

The deployer auto-discovers every `backend/apis/<slug>/deployment.yaml` and builds + deploys it.

## Adding a new service

1. `mkdir backend/apis/<new_slug>/` with the layout above.
2. Pick a kebab-case `service_slug` and put it in `deployment.yaml`.
3. Write `main.py` + at least `routes/healthz.py` and `routes/readyz.py` (Cloud Run probes need them).
4. List runtime deps in `pyproject.toml`.
5. Add `Dockerfile` + `.dockerignore` (copy an existing service's as a template).
6. Push — `deploy_apis.yml` picks it up automatically.

See [example](kalshi) as a minimal reference.
