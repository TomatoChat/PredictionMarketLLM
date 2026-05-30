# Queues

One YAML file per Cloud Tasks queue. The filename stem is the queue name in GCP.

`backend/infra/queue_deployer/` discovers every `*.yaml` here and applies it via Pulumi. Setting `target_service_slug` grants the shared `task-runner` SA `roles/run.invoker` on that Cloud Run service so the queue can dispatch OIDC-authenticated tasks to it.

## Fields

| Field | Default | Notes |
|---|---|---|
| `target_service_slug` | — | Cloud Run service slug the queue dispatches to. |
| `max_concurrent_dispatches` | 100 | 1–1000. |
| `max_dispatches_per_second` | 500.0 | 0.1–500. |
| `max_attempts` | 3 | `-1` = unlimited. |
| `max_retry_duration` | `3600s` | Duration string. |
| `min_backoff` | `0.1s` | Duration string. |
| `max_backoff` | `3600s` | Duration string. |
| `max_doublings` | 16 | 0–16. |

## Dispatch deadline (per-task, not a queue field)

The Cloud Tasks **dispatch deadline** — how long Cloud Tasks waits for the worker
before retrying — is set **per task**, not on the queue, so it isn't a field here.
It lives in [`backend/tasks/QUEUE_DISPATCH_DEADLINES.py`](../tasks/QUEUE_DISPATCH_DEADLINES.py)
(keyed by queue name) and `enqueue()` applies it automatically. **Invariant:** each
deadline must be ≤ the target service's `timeout` in its `deployment.yaml`, or Cloud
Run kills the request before the deadline fires.

## Concurrency vs. service capacity

A queue's `max_concurrent_dispatches` should not exceed the target service's capacity
= `max_instances × concurrency` (from its `deployment.yaml`). When **multiple queues
target the same service**, their concurrencies must sum to ≤ that capacity, or the
excess gets 429'd and retried. Current llm-targeting queues are sized for this:
`save-embeddings-markets` (4) + `solve-market-llm` (4) = 8 = llm's `max_instances 1 × concurrency 8`.
