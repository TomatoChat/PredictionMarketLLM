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
└── kalshi-scrape.yaml
```

The filename **is** the queue name (kebab-case, ≤63 chars, lowercase alphanumeric + hyphens).

Example `kalshi-scrape.yaml`:

```yaml
target_service_slug: kalshi

max_concurrent_dispatches: 100
max_dispatches_per_second: 500.0

max_attempts: 3
max_retry_duration: "3600s"
min_backoff: "0.1s"
max_backoff: "3600s"
max_doublings: 16
```

## Deploy

CI auto-deploys on push to `main` touching `backend/queues/**` or this deployer — see [.github/workflows/deploy_queues.yml](../../../.github/workflows/deploy_queues.yml).

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
