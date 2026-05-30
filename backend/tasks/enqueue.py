"""Generic helper that creates one Cloud Tasks task with a Pydantic payload."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from google.cloud import tasks_v2
from google.protobuf import duration_pb2
from observability import inject_trace_headers
from pydantic import BaseModel
from settings import get_settings

from .get_client import get_client

logger = logging.getLogger(__name__)


def enqueue(
    queue_name: str,
    target_url: str,
    payload: BaseModel,
    task_id: str | None = None,
    dispatch_deadline_seconds: int | None = None,
    http_method: str = "POST",
) -> tasks_v2.Task:
    """Create one HTTP task on ``queue_name`` targeting ``target_url``.

    ``payload`` is a Pydantic model — its ``model_dump_json()`` becomes the
    task body, and the model class is the typing contract shared with the
    receiving route handler (which declares the same model as its request).

    ``task_id`` lets the caller pick the Cloud Tasks task id (and therefore
    the full task name). Must match ``[A-Za-z0-9_-]{1,500}``. If omitted, we
    generate ``YYYYMMDDTHHMMSSZ-<uuid4hex>``.

    ``dispatch_deadline_seconds`` is the per-task Cloud Tasks dispatch
    deadline — how long Cloud Tasks waits for the worker to respond before
    treating the attempt as failed (and retrying per the queue's retry config).
    Valid range is 15..1800. Cloud Tasks default is 600. The receiving Cloud
    Run service's ``timeout`` must be >= this value or the request is killed
    before the deadline.

    The task is signed with an OIDC token minted for the shared ``task-runner``
    service account so the receiving Cloud Run service can validate it via
    ``roles/run.invoker``.
    """
    settings = get_settings()
    project_id = settings.GCP_PROJECT_ID
    region = settings.GCP_REGION
    sa_email = settings.TASK_RUNNER_SA_EMAIL

    if not project_id or not region:
        raise RuntimeError(
            "GCP_PROJECT_ID and GCP_REGION must be set in env to enqueue tasks"
        )

    client = get_client()
    parent = client.queue_path(project_id, region, queue_name)
    oidc = (
        tasks_v2.OidcToken(service_account_email=sa_email, audience=target_url)
        if sa_email
        else None
    )

    method = getattr(tasks_v2.HttpMethod, http_method.upper())

    if task_id is None:
        task_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex}"
    task_name = f"{parent}/tasks/{task_id}"

    deadline = (
        duration_pb2.Duration(seconds=dispatch_deadline_seconds)
        if dispatch_deadline_seconds is not None
        else None
    )

    headers = inject_trace_headers({"Content-Type": "application/json"})

    task = tasks_v2.Task(
        name=task_name,
        http_request=tasks_v2.HttpRequest(
            http_method=method,
            url=target_url,
            headers=headers,
            body=payload.model_dump_json().encode("utf-8"),
            oidc_token=oidc,
        ),
        dispatch_deadline=deadline,
    )

    response = client.create_task(parent=parent, task=task)

    logger.info(f"enqueued task to {queue_name}: {response.name}")

    return response
