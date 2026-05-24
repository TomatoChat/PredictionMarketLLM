from qdrant_client import QdrantClient

from ..models import CollectionSchema


def get_existing_point_ids(
    client: QdrantClient, schema: CollectionSchema, point_ids: list[str]
) -> set[str]:
    """Return the subset of ``point_ids`` that already exist in the given collection.

    Used by ingest jobs to skip points whose vectors are already stored.
    """
    if not point_ids:
        return set()

    points = client.retrieve(
        collection_name=schema.name,
        ids=list(point_ids),
        with_payload=False,
        with_vectors=False,
    )

    return {str(p.id) for p in points}
