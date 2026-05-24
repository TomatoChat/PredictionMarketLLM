# Cron Deployer (Pulumi)

Declarative scheduler-only deployer for crons under [`backend/crons/`](../../crons/). Each cron is **one YAML file named `<slug>.yaml`** — schedule + which Cloud Run service to call. The actual cron logic lives in the target api service (e.g. [`backend/apis/predict_markets`](../../apis/predict_markets)); this deployer never builds images or runs containers.

Only one stack today: `prd`.

## What it deploys

For each cron found:

| Resource | Pulumi type | Notes |
|---|---|---|
| Cloud Scheduler Job | `gcp:cloudscheduler:Job` | Cron expression + timezone. Calls the target service's URL with an OIDC token. |
| Service IAM binding | `gcp:cloudrunv2:ServiceIamMember` | Grants the shared scheduler service account `roles/run.invoker` on the target service. |

A single shared service account (`cron-scheduler@<project>.iam.gserviceaccount.com`) is created at the program level; every Scheduler Job uses it.

## Cron layout

Each cron is **one YAML file** directly under `backend/crons/`, named `<slug>.yaml`. The filename **is** the cron slug (used as the Scheduler resource name `cron-<slug>`).

```
backend/crons/
└── predict-markets.yaml
```

Example `predict-markets.yaml`:

```yaml
schedule: "0 */4 * * *"
timezone: UTC
target_service_slug: predict-markets   # backend/apis/<svc>/ — must already be deployed
target_path: /run
http_method: POST
# target_body: '{"dry_run": false}'    # optional JSON body
```

Fields:

| Field | Required | Notes |
|---|---|---|
| `schedule` | yes | 5-field cron expression. |
| `timezone` | no | Defaults to `UTC`. |
| `target_service_slug` | yes | Matches a `service_slug` from a `backend/apis/<svc>/deployment.yaml`. The target service must already be deployed by `cloud_run_deployer`. |
| `target_path` | no | Defaults to `/`. Must start with `/`. |
| `http_method` | no | Defaults to `POST`. |
| `target_body` | no | Optional JSON string. When set, `Content-Type: application/json` is added automatically. |

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

Stack-config keys (set in [Pulumi.prd.yaml](Pulumi.prd.yaml)):

| Key | Required | Notes |
|---|---|---|
| `gcp:project` | yes | GCP project ID. |
| `gcp:region` | no | Defaults to `europe-west3`. Cloud Scheduler is regional. |
| `cron-deployer:cronsDir` | no | Override cron discovery root. Defaults to `../../crons`. |

## Ordering

The target Cloud Run service **must already exist** when `pulumi up` runs — `cron_deployer` does a `cloudrunv2.get_service_output(...)` lookup and the Scheduler Job's `oidc_token.audience` is its URL.

For a fresh project, deploy in order: `cloud_run_deployer` first, then `cron_deployer`. The two CI workflows are independent; the natural ordering is "push api code → deploy_apis → push cron schedule → deploy_crons".
