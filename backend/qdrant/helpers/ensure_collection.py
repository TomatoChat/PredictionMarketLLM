from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams

from ..models import CollectionSchema


def ensure_collection(client: QdrantClient, schema: CollectionSchema) -> None:
    """Create the collection and its declared payload indexes if they don't already exist.

    Idempotent: safe to call at the start of every cron run. Mirrors the
    settings declared in ``backend.qdrant.schema`` so local/dev deployments
    can bootstrap themselves without manual UI steps.
    """
    if not client.collection_exists(schema.name):
        client.create_collection(
            collection_name=schema.name,
            vectors_config=VectorParams(
                size=schema.vector_size, distance=schema.distance
            ),
        )

    for index in schema.payload_indexes:
        client.create_payload_index(
            collection_name=schema.name,
            field_name=index.field_name,
            field_schema=index.field_schema,
        )
