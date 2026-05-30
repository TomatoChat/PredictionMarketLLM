# Queue Deployer (Pulumi)

Declarative deployer for Cloud Tasks queues under [`backend/queues/`](../../queues/). Each queue is **one YAML file named `<slug>.yaml`** — rate limits + retry config + optional target service for IAM. `pulumi up` reads every YAML file directly under `backend/queues/` and reconciles a `gcp.cloudtasks.Queue` for each.

Only one stack today: `prd`.

## What it deploys

Program-level (once):

| Resource | Pulumi type | Notes |
|---|---|---|
| Task-runner service account | `gcp:serviceaccount:Account` | Shared `task-runner@<project>.iam.gserviceaccount.com`. Producers mint OIDC tokens with this identity when creating tasks; receiving services validate via `roles/run.invoker`. |

Per queue found:

| Resource | Pulumi type | Notes |
|---|---|---|
| Cloud Tasks Queue | `gcp:cloudtasks:Queue` | Name from filename, rate limits + retry config from the YAML body. |
| Service IAM binding (optional) | `gcp:cloudrunv2:ServiceIamMember` | Created only when the YAML sets `target_service_slug`. Grants `task-runner` `roles/run.invoker` on that Cloud Run service. |

## Queue layout

```
backend/queues/
└── scrape-markets-polymarket.yaml
```

The filename **is** the queue name (kebab-case, ≤63 chars, lowercase alphanumeric + hyphens).

Example `scrape-markets-polymarket.yaml`:

```yaml
target_service_slug: polymarket

max_concurrent_dispatches: 1
max_dispatches_per_second: 1.0

max_attempts: 5
max_retry_duration: "3600s"
min_backoff: "10s"
max_backoff: "600s"
max_doublings: 4
```

## Deploy

CI auto-deploys on push to `main` touching `backend/queues/**` or this deployer — see [.github/workflows/deploy.yml](../../../.github/workflows/deploy.yml) (the `queue_deployer` job, which runs after `cloud_run_deployer`).

Locally:

```bash
cd backend/infra/queue_deployer
python -m venv .venv
.venv/bin/pip install -r requirements.txt

pulumi stack select prd
pulumi up
```

Stack-config keys (in [Pulumi.prd.yaml](Pulumi.prd.yaml)):

| Key | Required | Notes |
|---|---|---|
| `gcp:project` | yes | GCP project ID. |
| `gcp:region` | no | Defaults to `europe-west3`. Cloud Tasks queues are regional. |
| `queue-deployer:queuesDir` | no | Override queue discovery root. Defaults to `../../queues`. |
