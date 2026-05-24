# Cron Deployer (Pulumi)

Declarative scheduler-only deployer for crons under [`backend/crons/`](../../crons/). Each cron is **one YAML file named `<slug>.yaml`** — schedule + which Cloud Run service to call. The actual cron logic lives in the target api service (e.g. [`backend/apis/orchestrator`](../../apis/orchestrator)); this deployer never builds images or runs containers.

Only one stack today: `prd`.

## What it deploys

For each cron found:

| Resource | Pulumi type | Notes |
|---|---|---|
| Cloud Scheduler Job | `gcp:cloudscheduler:Job` | Cron expression + timezone. Calls the target service's URL with an OIDC token. |
| Service IAM binding | `gcp:cloudrunv2:ServiceIamMember` | Grants the shared scheduler service account `roles/run.invoker` on the target service. |

A single shared service account (`cron-scheduler@<project>.iam.gserviceaccount.com`) is created at the program level; every Scheduler Job uses it.

## Cron layout

```
backend/crons/
└── prepare-scraping.yaml
```

The filename **is** the cron slug. Cloud Scheduler creates a job named `cron-<slug>`.

Example [prepare-scraping.yaml](../../crons/prepare-scraping.yaml):

```yaml
schedule: "0 0 * * *"
timezone: UTC
target_service_slug: orchestrator
target_path: /prepare-scraping
http_method: POST
```

| Field | Required | Default | Notes |
|---|---|---|---|
| `schedule` | yes | — | 5-field cron expression (`minute hour day month day_of_week`). |
| `timezone` | no | `UTC` | IANA tz name. |
| `target_service_slug` | yes | — | Matches `service_slug` in a `backend/apis/<svc>/deployment.yaml`. Target service **must already be deployed** by `cloud_run_deployer`. |
| `target_path` | no | `/` | Must start with `/`. |
| `http_method` | no | `POST` | GET / POST / PUT / PATCH / DELETE. |
| `target_body` | no | — | Optional JSON string. When set, `Content-Type: application/json` is added automatically. |

## Deploy

CI auto-deploys on push to `main` touching `backend/crons/**` or this deployer — see [.github/workflows/deploy_crons.yml](../../../.github/workflows/deploy_crons.yml).

Locally:

```bash
cd backend/infra/cron_deployer
python -m venv .venv
.venv/bin/pip install -r requirements.txt

pulumi stack select prd
pulumi up
```

Stack-config keys (in [Pulumi.prd.yaml](Pulumi.prd.yaml)):

| Key | Required | Notes |
|---|---|---|
| `gcp:project` | yes | GCP project ID. |
| `gcp:region` | no | Defaults to `europe-west3`. Cloud Scheduler is regional. |
| `cron-deployer:cronsDir` | no | Override cron discovery root. Defaults to `../../crons`. |

## Ordering

The target Cloud Run service **must already exist** when `pulumi up` runs — `cron_deployer` does a `cloudrunv2.get_service_output(...)` lookup and the Scheduler Job's `oidc_token.audience` is its URL.

For a fresh project, deploy in order: `cloud_run_deployer` first, then `cron_deployer`.
