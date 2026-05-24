from collections.abc import Iterator

from kalshi_python_sync import Configuration, KalshiClient, Market, MarketApi
from tqdm import tqdm

from backend.kalshi.scripts.get_markets_with_retry import get_markets_with_retry

PAGE_LIMIT = 1000


def fetch_active_markets() -> Iterator[Market]:
    """Yield open Kalshi markets one at a time via the official kalshi-python-sync SDK.

    Public market data endpoint — no authentication required. Transient HTTP failures
    are retried inside get_markets_with_retry.
    """
    client = KalshiClient(Configuration())
    api = MarketApi(client)
    cursor: str | None = None
    total_seen = 0

    with tqdm(desc="kalshi - fetching pages", unit="page") as pbar:
        while True:
            response = get_markets_with_retry(api, cursor, PAGE_LIMIT)
            total_seen += len(response.markets)
            for market in response.markets:
                yield market

            pbar.update(1)
            pbar.set_postfix(seen=total_seen)

            cursor = response.cursor
            if not cursor:
                break
