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
