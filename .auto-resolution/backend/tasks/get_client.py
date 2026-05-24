from functools import lru_cache

from google.cloud import tasks_v2


@lru_cache(maxsize=1)
def get_client() -> tasks_v2.CloudTasksClient:
    """Return a process-wide cached Cloud Tasks client."""
    return tasks_v2.CloudTasksClient()
