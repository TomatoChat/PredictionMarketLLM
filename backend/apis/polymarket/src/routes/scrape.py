import logging

from shared_models import EmbedMarketRequest, PredictRequest, ScrapeRequest
from fastapi import APIRouter, HTTPException
from settings import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from supabase.queries import get_active_llm_config_names
from tasks import enqueue

from ..helpers.scrape import END_CURSOR, scrape_polymarket_page
from ..models import ScrapeResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/scrape",
    response_model=ScrapeResponse,
    response_model_exclude_none=True,
)
def scrape(request: ScrapeRequest) -> ScrapeResponse:
    """Scrape one Polymarket page and fan out embedding + prediction tasks.

    Chains the queue: if the API returns a non-terminal ``next_cursor``,
    we enqueue another scrape task. Per newly upserted market we enqueue:
    one ``save-embeddings-markets`` task, plus one ``solve-market-llm`` task
    per active llm_config.
    """
    settings = get_settings()
    polymarket_url = settings.POLYMARKET_SERVICE_URL
    llm_url = settings.LLM_SERVICE_URL
    if not polymarket_url or not llm_url:
        raise HTTPException(
            status_code=500,
            detail="POLYMARKET_SERVICE_URL and LLM_SERVICE_URL must be configured",
        )

    ok, next_cursor, new_market_ids = scrape_polymarket_page(request.cursor)
    if not ok:
        raise HTTPException(status_code=500, detail="scrape page failed; see logs")

    if next_cursor and next_cursor != END_CURSOR:
        enqueue(
            queue_name="scrape-markets-polymarket",
            target_url=f"{polymarket_url.rstrip('/')}/scrape",
            payload=ScrapeRequest(cursor=next_cursor),
            dispatch_deadline_seconds=600,
        )

    if new_market_ids:
        engine = create_engine(settings.database_url)
        with Session(engine) as session:
            config_names = get_active_llm_config_names(session).names

        embed_url = f"{llm_url.rstrip('/')}/embed-market"
        predict_url = f"{llm_url.rstrip('/')}/predict"

        for market_id in new_market_ids:
            enqueue(
                queue_name="save-embeddings-markets",
                target_url=embed_url,
                payload=EmbedMarketRequest(market_id=market_id),
                dispatch_deadline_seconds=300,
            )
            for config_name in config_names:
                enqueue(
                    queue_name="solve-market-llm",
                    target_url=predict_url,
                    payload=PredictRequest(
                        market_id=market_id,
                        config_name=config_name,
                    ),
                    dispatch_deadline_seconds=300,
                )

    return ScrapeResponse(
        ok=ok,
        next_cursor=next_cursor,
        new_markets=len(new_market_ids),
    )
