import logging
import time

from kalshi_python_sync import ApiException, GetMarketsResponse, MarketApi

MAX_RETRIES = 4
BACKOFF_BASE_SECONDS = 2.0

logger = logging.getLogger(__name__)


def get_markets_with_retry(
    api: MarketApi, cursor: str | None, limit: int
) -> GetMarketsResponse:
    """Call MarketApi.get_markets with exponential-backoff retry on ApiException.

    Filters server-side for `status="open"`. Retries up to MAX_RETRIES times before
    re-raising the last exception.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return api.get_markets(limit=limit, cursor=cursor, status="open")
        except ApiException as exc:
            if attempt == MAX_RETRIES:
                raise

            wait = BACKOFF_BASE_SECONDS**attempt

            logger.warning(
                "kalshi - get_markets failed (attempt %d/%d), retrying in %.1fs: %s",
                attempt,
                MAX_RETRIES,
                wait,
                exc,
            )
            time.sleep(wait)

    raise RuntimeError("unreachable: MAX_RETRIES must be > 0")
