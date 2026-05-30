# Cloud Run Deployer (Pulumi)

Declarative Cloud Run deployer. One `pulumi up` discovers every service under [`backend/apis/`](../../apis/) (any subdirectory that contains a `deployment.yaml`) and deploys all of them as Pulumi resources under a single `prd` stack.

## What it deploys

For each service found:

| Resource | Pulumi type | Notes |
|---|---|---|
| Docker image | `docker-build:Image` | Built locally, pushed to `imageRepo`/`projectId`/`<slug>:latest`. Content-addressed via `image.ref`. |
| Cloud Run service | `gcp:cloudrunv2:Service` | VPC access, env vars, startup + liveness probes, ingress, native scaling. |

Scaling uses Cloud Run's built-in autoscaler (`min_instances` / `max_instances` from each service's `deployment.yaml`).

## Service layout

Each deployable service lives at `backend/apis/<slug>/` with:

```
backend/apis/<slug>/
├── Dockerfile
├── deployment.yaml     # DeploymentConfig (snake_case keys; see src/models/DeploymentConfig.py)
├── pyproject.toml
├── main.py
└── src/
    ├── routes/         # one route per file
    ├── classes/        # one class per file
    ├── helpers/        # one helper per file
    └── models/         # one model per file
```

See [`backend/apis/polymarket`](../../apis/polymarket) for a working FastAPI scaffold.

`.dockerignore` lives next to each service's `Dockerfile`. Make sure it excludes `.git/`, `__pycache__/`, `.venv/`, etc.

## Deploy

CI deploys automatically on every push to `main` that touches `backend/apis/**` or this deployer — see [.github/workflows/deploy.yml](../../../.github/workflows/deploy.yml) (the `cloud_run_deployer` job, which runs first; the other stacks depend on it).

To deploy locally:

```bash
cd backend/infra/cloud_run_deployer
python -m venv .venv
.venv/bin/pip install -r requirements.txt

pulumi stack select prd
pulumi up
```

Stack-config keys (set in [Pulumi.prd.yaml](Pulumi.prd.yaml)):

| Key | Required | Notes |
|---|---|---|
| `gcp:project` | yes | GCP project ID. |
| `gcp:region` | no | Defaults to `europe-west3`. |
| `cloud-run-deployer:projectIdNumber` | yes | Injected into the container as `GCP_PROJECT_ID_NUMBER`. |
| `cloud-run-deployer:apisDir` | no | Override service discovery root. Defaults to `../../apis`. |
| `cloud-run-deployer:buildContext` | no | Docker build context. Defaults to repo root. |
| `cloud-run-deployer:imageRepo` | no | Defaults to `gcr.io`. Set to `europe-west3-docker.pkg.dev/<project>/<repo>` for Artifact Registry. |

Add a new service by creating `backend/apis/<slug>/` with the files listed above; the next `pulumi up` picks it up automatically.

## Required CI secrets (GitHub Environment: `prd`)

| Secret | What it is |
|---|---|
| `GCP_CREDENTIALS_JSON` | Service account JSON with `roles/run.admin`, `roles/iam.serviceAccountUser`, `roles/storage.admin`, and image-push permission on `imageRepo`. Also used to access the Pulumi state bucket. |
| `PULUMI_CONFIG_PASSPHRASE` | Passphrase for the self-managed Pulumi state backend (`PULUMI_BACKEND_URL=gs://prediction-market-llm-pulumi-state`). |

> The state backend is **self-managed in GCS** (not Pulumi Cloud), so there is no `PULUMI_ACCESS_TOKEN`. The same two secrets apply to every deploy job (`queue_deployer`, `cron_deployer`, `qdrant_deployer`, `qdrant_sync`). The `qdrant_deployer` job additionally needs `QDRANT_CLOUD_API_KEY`.
