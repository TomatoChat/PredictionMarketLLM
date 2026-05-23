from collections.abc import Iterator

from py_clob_client_v2.client import ClobClient
from tqdm import tqdm

from backend.polymarket.models import Market, MarketsPage
from backend.polymarket.scripts.get_markets_with_retry import get_markets_with_retry

HOST = "https://clob.polymarket.com"
CHAIN_ID = 137
INITIAL_CURSOR = "MA=="
END_CURSOR = "LTE="


def fetch_active_markets() -> Iterator[Market]:
    """Yield active+open Polymarket markets one at a time, streaming across paginated CLOB pages.

    Transient HTTP failures from the CLOB API are retried inside get_markets_with_retry.
    """
    client = ClobClient(host=HOST, chain_id=CHAIN_ID)
    next_cursor = INITIAL_CURSOR
    total_seen = 0
    total_active = 0

    with tqdm(desc="polymarket - fetching pages", unit="page") as pbar:
        while next_cursor and next_cursor != END_CURSOR:
            raw = get_markets_with_retry(client, next_cursor)
            page = MarketsPage.model_validate(raw)
            total_seen += len(page.data)

            for market in page.data:
                if (
                    market.active
                    and not market.closed
                    and not market.archived
                    and market.accepting_orders
                ):
                    total_active += 1
                    yield market

            next_cursor = page.next_cursor
            pbar.update(1)
            pbar.set_postfix(seen=total_seen, active=total_active)
