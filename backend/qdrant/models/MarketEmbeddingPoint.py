from pydantic import BaseModel, ConfigDict

from supabase import Source


class MarketEmbeddingPoint(BaseModel):
    """One market embedding ready to upsert into the ``markets`` Qdrant collection.

    ``point_id`` is the bare UUID (the part after ``mkt_``) — that's what
    Qdrant uses as the primary key. ``market_id`` (the full prefixed id) and
    ``source`` are stored in the payload.
    """

    model_config = ConfigDict(frozen=True)

    point_id: str
    market_id: str
    source: Source
    embedding: list[float]
