from api_contracts import ScrapeRequest
from fastapi import APIRouter, HTTPException
from settings import get_settings
from tasks import enqueue

from ..models import PrepareScrapingResponse

router = APIRouter()

POLYMARKET_INITIAL_CURSOR = "MA=="


@router.post(
    "/prepare-scraping",
    response_model=PrepareScrapingResponse,
    response_model_exclude_none=True,
)
def prepare_scraping() -> PrepareScrapingResponse:
    """Kick off the scrape pipeline.

    Enqueues one bootstrap task per supported source onto its scrape queue.
    The receiving service's /scrape handler chains the next page on its own.
    Currently only polymarket is wired up.
    """
    settings = get_settings()

    if not settings.POLYMARKET_SERVICE_URL:
        raise HTTPException(
            status_code=500,
            detail="POLYMARKET_SERVICE_URL not configured",
        )

    enqueue(
        queue_name="scrape-markets-polymarket",
        target_url=f"{settings.POLYMARKET_SERVICE_URL.rstrip('/')}/scrape",
        payload=ScrapeRequest(cursor=POLYMARKET_INITIAL_CURSOR),
    )

    return PrepareScrapingResponse(enqueued=1)
