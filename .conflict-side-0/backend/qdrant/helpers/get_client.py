from functools import lru_cache

from qdrant_client import QdrantClient
from settings import get_settings


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    """Return a process-wide cached Qdrant client built from settings."""
    settings = get_settings()

    return QdrantClient(
        url=settings.QDRANT_ENDPOINT.get_secret_value(),
        api_key=settings.QDRANT_API_KEY.get_secret_value(),
    )
