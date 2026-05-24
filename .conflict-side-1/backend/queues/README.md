# backend/queues

One YAML file per queue, named `<slug>.yaml` directly under this directory — **no subdirectories, no Python code**. Each file declares the rate limits and retry config for a [Cloud Tasks queue](https://cloud.google.com/tasks/docs). Deployed by [../infra/queue_deployer](../infra/queue_deployer) as `gcp.cloudtasks.Queue` resources.

## What this is (and isn't)

This directory owns **queue definitions** — how fast Cloud Tasks should drain them, how aggressively to retry, how long before giving up. It does **not** define tasks. Producers in your application code enqueue tasks against `projects/<project>/locations/<region>/queues/<slug>` via the `google-cloud-tasks` SDK; the receiving end (typically a route on a service under [../apis](../apis)) does the work.

The split mirrors `crons`:

| Concern | Lives in | Owns |
|---|---|---|
| When a thing runs (recurring) | [../crons](../crons) | Cloud Scheduler entries |
| How a backlog drains (on demand) | this dir | Cloud Tasks queue rate/retry config |
| What the thing does | [../apis](../apis) | HTTP routes |

## Layout

```
backend/queues/
└── kalshi-scrape.yaml
```

The filename **is** the queue name (Cloud Tasks naming rules: lowercase alphanumeric + hyphens, ≤63 chars).

## File schema

Example:

```yaml
max_concurrent_dispatches: 100
max_dispatches_per_second: 500.0

max_attempts: 3
max_retry_duration: "3600s"
min_backoff: "0.1s"
max_backoff: "3600s"
max_doublings: 16
```

All fields optional — defaults below mirror Cloud Tasks defaults.

| Field | Default | Notes |
|---|---|---|
| `max_concurrent_dispatches` | `100` | 1–1000. Caps in-flight tasks across the queue. |
| `max_dispatches_per_second` | `500.0` | 0.1–500.0. Token-bucket dispatch rate. |
| `max_attempts` | `3` | `-1` for unlimited; otherwise 0–100. |
| `max_retry_duration` | `"3600s"` | Total time across all attempts. Format: `<seconds>s`. |
| `min_backoff` | `"0.1s"` | Minimum delay between retries. |
| `max_backoff` | `"3600s"` | Maximum delay between retries. |
| `max_doublings` | `16` | Times to double the backoff before staying flat. 0–16. |

The full schema lives in [QueueConfig.py](../infra/queue_deployer/src/models/QueueConfig.py).

## Deploy

Push to `main` touching `backend/queues/**` — [.github/workflows/deploy_queues.yml](../../.github/workflows/deploy_queues.yml) runs `pulumi up` against [../infra/queue_deployer](../infra/queue_deployer) and reconciles every queue in one pass.

Locally:

```bash
cd backend/infra/queue_deployer
pulumi stack select prd
pulumi up
```

## Adding a new queue

1. Pick a kebab-case slug (lowercase alphanumeric + hyphens, ≤63 chars).
2. Create `backend/queues/<slug>.yaml` with the fields above (all optional; an empty file uses defaults).
3. Push — the workflow picks it up automatically.
4. In your producer code, enqueue against `projects/<project>/locations/<region>/queues/<slug>`.

## Enqueuing tasks (sketch)

The deployer doesn't ship a task-producer SDK wrapper, but here's the pattern for application code:

```python
from google.cloud import tasks_v2

client = tasks_v2.CloudTasksClient()
queue_path = client.queue_path(project_id, region, "kalshi-scrape")

client.create_task(
    parent=queue_path,
    task=tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            url="https://kalshi-<hash>-<region>.run.app/process_one",
            http_method=tasks_v2.HttpMethod.POST,
            headers={"Content-Type": "application/json"},
            body=b'{"market_id": "..."}',
            oidc_token=tasks_v2.OidcToken(service_account_email=producer_sa_email),
        ),
    ),
)
```

If every task in a queue should hit the **same** URL, that's expressible as a queue-level `http_target` override on `gcp.cloudtasks.Queue`. The current `QueueConfig` schema doesn't surface it — happy to add `target_service_slug` + `target_path` fields (mirroring `cron_deployer`) when you have a concrete use case.
