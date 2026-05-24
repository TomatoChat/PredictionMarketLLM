# Queue Deployer (Pulumi)

Declarative deployer for Cloud Tasks queues under [`backend/queues/`](../../queues/). Each queue is **one YAML file named `<slug>.yaml`** — rate limits + retry config. `pulumi up` reads every YAML file directly under `backend/queues/` and reconciles a `gcp.cloudtasks.Queue` for each.

Only one stack today: `prd`.

## What it deploys

For each queue found:

| Resource | Pulumi type | Notes |
|---|---|---|
| Cloud Tasks Queue | `gcp:cloudtasks:Queue` | Name from filename, rate limits + retry config from the YAML body. |

The deployer is **declarative-only**: it never creates Tasks or knows about your task producers (that's your application code's job, using `google-cloud-tasks` / `pulumi_gcp.cloudtasks` SDKs to enqueue). It just owns the queue *definitions*.

## Queue layout

```
backend/queues/
└── kalshi-scrape.yaml
```

The filename **is** the queue name (kebab-case, ≤63 chars, lowercase alphanumeric + hyphens — Cloud Tasks naming rules).

Example `kalshi-scrape.yaml`:

```yaml
max_concurrent_dispatches: 100
max_dispatches_per_second: 500.0

max_attempts: 3
max_retry_duration: "3600s"
min_backoff: "0.1s"
max_backoff: "3600s"
max_doublings: 16
```

Fields (all optional — defaults shown above):

| Field | Default | Notes |
|---|---|---|
| `max_concurrent_dispatches` | `100` | 1–1000. Caps in-flight tasks across the queue. |
| `max_dispatches_per_second` | `500.0` | 0.1–500.0. Token-bucket dispatch rate. |
| `max_attempts` | `3` | -1 = unlimited; otherwise 0–100. |
| `max_retry_duration` | `"3600s"` | Total time across all attempts. Cloud Tasks duration format (`<seconds>s`). |
| `min_backoff` | `"0.1s"` | Minimum delay between retries. |
| `max_backoff` | `"3600s"` | Maximum delay between retries. |
| `max_doublings` | `16` | How many times to double the backoff before staying flat. 0–16. |

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

Stack-config keys (set in [Pulumi.prd.yaml](Pulumi.prd.yaml)):

| Key | Required | Notes |
|---|---|---|
| `gcp:project` | yes | GCP project ID. |
| `gcp:region` | no | Defaults to `europe-west3`. Cloud Tasks queues are regional. |
| `queue-deployer:queuesDir` | no | Override queue discovery root. Defaults to `../../queues`. |

Add a queue by creating a single YAML file under `backend/queues/`; the next `pulumi up` reconciles it.
