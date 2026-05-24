# backend/crons

One YAML file per cron, named `<slug>.yaml` directly under this directory — **no subdirectories, no Python code**. Each file declares a schedule and which `backend/apis/<svc>/` endpoint to call. Deployed by [../infra/cron_deployer](../infra/cron_deployer) as Cloud Scheduler jobs that POST to the target service with an OIDC-authenticated request.

## Why no code here

The cron only orchestrates *when* to run; the work lives in the target api. A cron is just:

```
Cloud Scheduler ──HTTP POST──▶ <target_service_slug>.<region>.run.app/<target_path>
```

If you need new logic, add it as a route on a service under [../apis](../apis). The cron stays a single YAML file pointing at that route.

## Layout

```
backend/crons/
└── predict-markets.yaml
```

The filename **is** the cron slug. Cloud Scheduler creates a job named `cron-<slug>` (e.g. `cron-predict-markets`).

## File schema

Example [predict-markets.yaml](predict-markets.yaml):

```yaml
schedule: "0 */4 * * *"
timezone: UTC
target_service_slug: predict-markets   # must match a service_slug in backend/apis/<svc>/deployment.yaml
target_path: /run
http_method: POST
# target_body: '{"dry_run": false}'    # optional JSON body
```

| Field | Required | Default | Notes |
|---|---|---|---|
| `schedule` | yes | — | 5-field cron expression (`minute hour day month day_of_week`). |
| `timezone` | no | `UTC` | IANA tz name. |
| `target_service_slug` | yes | — | Matches `service_slug` in a `backend/apis/<svc>/deployment.yaml`. Target service **must already be deployed** by `cloud_run_deployer`. |
| `target_path` | no | `/` | Must start with `/`. |
| `http_method` | no | `POST` | GET / POST / PUT / PATCH / DELETE. |
| `target_body` | no | — | Optional JSON string. When set, `Content-Type: application/json` is added automatically. |

The full schema lives in [QueueConfig.py](../infra/cron_deployer/src/models/CronConfig.py) — sorry, [CronConfig.py](../infra/cron_deployer/src/models/CronConfig.py).

## Auth

Cloud Scheduler signs every dispatch with an OIDC token minted for a shared service account (`cron-scheduler@<project>.iam.gserviceaccount.com`, created by the deployer). The deployer also grants that SA `roles/run.invoker` on every targeted service, so private (internal-only) Cloud Run services accept the call.

## Deploy

Push to `main` touching `backend/crons/**` — [.github/workflows/deploy_crons.yml](../../.github/workflows/deploy_crons.yml) runs `pulumi up` against [../infra/cron_deployer](../infra/cron_deployer) and reconciles every cron in one pass.

Locally:

```bash
cd backend/infra/cron_deployer
pulumi stack select prd
pulumi up
```

## Adding a new cron

1. Pick a kebab-case slug (lowercase alphanumeric + hyphens).
2. Create `backend/crons/<slug>.yaml` with the fields above.
3. Make sure the target service exists under [../apis](../apis) and is deployed.
4. Push — the workflow picks it up automatically.

## Why not native cron containers?

Cloud Run **Jobs** (one-shot containers) are also a valid cron pattern in GCP. We deliberately do *not* use them here: the cron's logic always lives in a service anyway (so we can also invoke it ad-hoc via HTTP — the predict_markets `POST /run` is callable for manual reruns, debugging, or chained workflows). Keeping crons as thin schedulers makes the architecture uniform.

If you ever need a one-shot job that has *no* HTTP entry point, add it as a route on a new service and point a cron at it.
