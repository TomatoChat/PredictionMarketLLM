from pathlib import Path

import pulumi
import pulumi_gcp as gcp

from ..models import QueueConfig


def deploy_queue(
    queue_yaml: Path,
    project_id: str,
    region: str,
    task_runner_sa: gcp.serviceaccount.Account,
) -> None:
    slug = queue_yaml.stem
    cfg = QueueConfig.load_config(queue_yaml)

    queue = gcp.cloudtasks.Queue(
        f"{slug}-queue",
        name=slug,
        location=region,
        project=project_id,
        rate_limits=gcp.cloudtasks.QueueRateLimitsArgs(
            max_concurrent_dispatches=cfg.max_concurrent_dispatches,
            max_dispatches_per_second=cfg.max_dispatches_per_second,
        ),
        retry_config=gcp.cloudtasks.QueueRetryConfigArgs(
            max_attempts=cfg.max_attempts,
            max_retry_duration=cfg.max_retry_duration,
            min_backoff=cfg.min_backoff,
            max_backoff=cfg.max_backoff,
            max_doublings=cfg.max_doublings,
        ),
    )

    if cfg.target_service_slug:
        gcp.cloudrunv2.ServiceIamMember(
            f"{slug}-invoker",
            project=project_id,
            location=region,
            name=cfg.target_service_slug,
            role="roles/run.invoker",
            member=pulumi.Output.concat("serviceAccount:", task_runner_sa.email),
        )

    pulumi.export(f"{slug}_queue_id", queue.id)
    pulumi.export(f"{slug}_queue_name", queue.name)
