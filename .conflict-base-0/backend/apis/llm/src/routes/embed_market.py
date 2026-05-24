from embedder import Embedder
from fastapi import APIRouter, HTTPException
from qdrant import (
    MARKETS,
    MarketEmbeddingPoint,
    ensure_collection,
    get_client,
    get_existing_point_ids,
    to_point_id,
    upsert_market_embeddings,
)
from settings import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from supabase.queries import get_market

from ..models import EmbedMarketRequest, EmbedMarketResponse

router = APIRouter()


@router.post(
    "/embed-market",
    response_model=EmbedMarketResponse,
    response_model_exclude_none=True,
)
def embed_market(request: EmbedMarketRequest) -> EmbedMarketResponse:
    """Compute + upsert one market's embedding into qdrant. Idempotent."""
    engine = create_engine(get_settings().database_url)

    with Session(engine) as session:
        market = get_market(session, request.market_id).market

        if market is None:
            raise HTTPException(
                status_code=404,
                detail=f"market {request.market_id!r} not found",
            )

        qdrant_client = get_client()
        ensure_collection(qdrant_client, MARKETS)

        point_id = to_point_id(market.id)
        existing = get_existing_point_ids(qdrant_client, MARKETS, [point_id])

        if point_id in existing:
            return EmbedMarketResponse(embedded=False)

        embedder = Embedder()
        [vector] = embedder.embed(
            [Embedder.build_input(market.question, market.description)]
        )

        upsert_market_embeddings(
            qdrant_client,
            [
                MarketEmbeddingPoint(
                    point_id=point_id,
                    market_id=market.id,
                    source=market.source,
                    embedding=vector,
                )
            ],
        )

    return EmbedMarketResponse(embedded=True)
