from __future__ import annotations

import logging
import os

from google.cloud import secretmanager

logger = logging.getLogger(__name__)


def get_secret(
    secret_id: str,
    project_id: str | None = None,
    version_id: str = "latest",
    client: secretmanager.SecretManagerServiceClient | None = None,
) -> str:
    """Fetch one secret value from GCP Secret Manager.

    Args:
        secret_id: ID of the secret (e.g. ``OPENAI_API_KEY``). The secret
            resource is ``projects/<project>/secrets/<secret_id>/versions/<version>``.
        project_id: GCP project. Falls back to ``GCP_PROJECT_ID`` env var.
        version_id: Defaults to ``latest``.
        client: Existing ``SecretManagerServiceClient``. A new client is
            constructed if not provided.

    Returns:
        The secret payload as a UTF-8 string.

    Raises:
        ValueError: If ``project_id`` can't be determined.
    """
    if not project_id:
        project_id = os.getenv("GCP_PROJECT_ID")

    if not project_id:
        raise ValueError(
            "project_id is required (pass explicitly or set GCP_PROJECT_ID env var)"
        )

    if client is None:
        client = secretmanager.SecretManagerServiceClient()

    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    logger.info(f"fetching secret {secret_id!r} (version {version_id}) from GSM")

    response = client.access_secret_version(request={"name": name})

    return response.payload.data.decode("UTF-8")
