import logging
from datetime import UTC, datetime

from shared_models import EmbedMarketRequest, PredictRequest, ScrapeRequest
from fastapi import APIRouter, HTTPException
from settings import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from db import Source
from db.queries import get_active_llm_configs
from tasks import enqueue

from ..helpers.scrape import scrape_polymarket_page
from ..models import ScrapeResponse

router = APIRouter()
logger = logging.getLogger(__name__)

SOURCE = Source.POLYMARKET.value


@router.post(
    "/scrape",
    response_model=ScrapeResponse,
    response_model_exclude_none=True,
)
def scrape(request: ScrapeRequest) -> ScrapeResponse:
    """Scrape one CLOB page and fan out embedding + prediction tasks.

    Chains the queue: while the API returns a non-terminal ``next_cursor`` we
    enqueue the next scrape task. Per newly upserted *tradeable* market we
    enqueue one ``save-embeddings-markets`` task, plus one ``solve-market-llm``
    task per active llm_config.
    """
    settings = get_settings()
    polymarket_url = settings.POLYMARKET_SERVICE_URL
    llm_url = settings.LLM_SERVICE_URL
    if not polymarket_url or not llm_url:
        raise HTTPException(
            status_code=500,
            detail="POLYMARKET_SERVICE_URL and LLM_SERVICE_URL must be configured",
        )

    ok, next_cursor, new_market_ids, active_market_ids = scrape_polymarket_page(
        request.cursor
    )
    if not ok:
        raise HTTPException(status_code=500, detail="scrape page failed; see logs")

    if next_cursor is not None:
        enqueue(
            queue_name="scrape-markets-polymarket",
            target_url=f"{polymarket_url.rstrip('/')}/scrape",
            payload=ScrapeRequest(cursor=next_cursor),
        )

    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    # Embed every newly-seen market once (open or closed): question/description
    # don't change after resolution, so a market is embedded exactly one time.
    # Task id: <timestamp>-<source>-<marketId>.
    embed_url = f"{llm_url.rstrip('/')}/embed-market"
    for market_id in new_market_ids:
        enqueue(
            queue_name="save-embeddings-markets",
            target_url=embed_url,
            payload=EmbedMarketRequest(market_id=market_id),
            task_id=f"{ts}-{SOURCE}-{market_id}",
        )

    # Predict every tradeable market on each walk (append-only history); closed
    # markets are never predicted. Task id:
    # <timestamp>-<source>-<marketId>-<configName>-<configId>.
    if active_market_ids:
        engine = create_engine(settings.database_url)
        with Session(engine) as session:
            configs = get_active_llm_configs(session).configs

        predict_url = f"{llm_url.rstrip('/')}/predict"
        for market_id in active_market_ids:
            for config_id, config_name in configs:
                enqueue(
                    queue_name="solve-market-llm",
                    target_url=predict_url,
                    payload=PredictRequest(
                        market_id=market_id,
                        config_name=config_name,
                    ),
                    task_id=f"{ts}-{SOURCE}-{market_id}-{config_name}-{config_id}",
                )

    return ScrapeResponse(
        ok=ok,
        next_cursor=next_cursor,
        new_markets=len(new_market_ids),
    )
