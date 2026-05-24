from dataclasses import dataclass, field

from qdrant_client.models import Distance

from .PayloadIndex import PayloadIndex


@dataclass(frozen=True)
class CollectionSchema:
    """Declarative definition of a Qdrant collection — its name, vector geometry, and payload indexes.

    Mirrors the role of ``backend.supabase.schema`` for SQLAlchemy ORM models:
    every Qdrant collection in the project is defined here, and helpers
    (``ensure_collection``, ``get_existing_point_ids``, upserts, …) accept a
    ``CollectionSchema`` so callers never hard-code collection names or vector
    sizes.
    """

    name: str
    vector_size: int
    distance: Distance
    payload_indexes: tuple[PayloadIndex, ...] = field(default_factory=tuple)
