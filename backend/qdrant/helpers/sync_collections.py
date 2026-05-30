import logging

from qdrant_client import QdrantClient

from ..models import CollectionSchema
from .ensure_collection import ensure_collection

logger = logging.getLogger(__name__)


def sync_collections(
    client: QdrantClient, collections: tuple[CollectionSchema, ...]
) -> dict[str, str]:
    """Reconcile Qdrant against the declared ``collections`` (schema.COLLECTIONS).

    For each collection:

    - **missing** -> create it and its payload indexes (``"created"``).
    - **present** -> verify the vector size matches the declared schema; a
      mismatch raises (vector size can't change in place — that needs a manual
      recreate + reindex), then reconcile payload indexes idempotently
      (``"synced"``).

    Returns ``{collection_name: action}``. Intended as the single deploy-time
    entry point (analogous to the Supabase migrations / ``seed_canonical_configs``)
    rather than being called lazily per request.
    """
    results: dict[str, str] = {}

    for schema in collections:
        if client.collection_exists(schema.name):
            info = client.get_collection(schema.name)
            vectors = info.config.params.vectors
            existing_size = getattr(vectors, "size", None)
            if existing_size is not None and existing_size != schema.vector_size:
                raise ValueError(
                    f"collection {schema.name!r}: existing vector size "
                    f"{existing_size} != declared {schema.vector_size}. Vector size "
                    "cannot change in place; recreate the collection and reindex."
                )
            action = "synced"
        else:
            action = "created"

        # ensure_collection creates the collection if missing and (re)declares
        # every payload index idempotently.
        ensure_collection(client, schema)
        results[schema.name] = action
        logger.info(f"qdrant - collection {schema.name!r}: {action}")

    return results
