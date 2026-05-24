"""Generic helper that creates one Cloud Tasks task with a Pydantic payload."""

from __future__ import annotations

import logging

from google.cloud import tasks_v2
from pydantic import BaseModel
from settings import get_settings

from .get_client import get_client

logger = logging.getLogger(__name__)


def enqueue(
    queue_name: str,
    target_url: str,
    payload: BaseModel,
    http_method: str = "POST",
) -> tasks_v2.Task:
    """Create one HTTP task on ``queue_name`` targeting ``target_url``.

    ``payload`` is a Pydantic model — its ``model_dump_json()`` becomes the
    task body, and the model class is the typing contract shared with the
    receiving route handler (which declares the same model as its request).

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

    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=method,
            url=target_url,
            headers={"Content-Type": "application/json"},
            body=payload.model_dump_json().encode("utf-8"),
            oidc_token=oidc,
        ),
    )

    response = client.create_task(parent=parent, task=task)

    logger.info(f"enqueued task to {queue_name}: {response.name}")

    return response
