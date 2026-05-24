from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from ..schema import MARKETS
from ..models import MarketEmbeddingPoint, UpsertMarketEmbeddingsResponse


def upsert_market_embeddings(
    client: QdrantClient, points: list[MarketEmbeddingPoint]
) -> UpsertMarketEmbeddingsResponse:
    """Upsert market embedding points into the ``MARKETS`` Qdrant collection."""
    if not points:
        return UpsertMarketEmbeddingsResponse(count=0)

    client.upsert(
        collection_name=MARKETS.name,
        points=[
            PointStruct(
                id=p.point_id,
                vector=p.embedding,
                payload={"market_id": p.market_id, "source": p.source.value},
            )
            for p in points
        ],
    )

    return UpsertMarketEmbeddingsResponse(count=len(points))
