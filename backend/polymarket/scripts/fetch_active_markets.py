import logging

from py_clob_client_v2.client import ClobClient

from backend.polymarket.models.Market import Market
from backend.polymarket.models.MarketsPage import MarketsPage

HOST = "https://clob.polymarket.com"
CHAIN_ID = 137
INITIAL_CURSOR = "MA=="
END_CURSOR = "LTE="

logger = logging.getLogger(__name__)


def fetch_active_markets() -> list[Market]:
    client = ClobClient(host=HOST, chain_id=CHAIN_ID)
    active_markets: list[Market] = []
    total_seen = 0
    page_index = 0
    next_cursor = INITIAL_CURSOR

    while next_cursor and next_cursor != END_CURSOR:
        raw = client.get_markets(next_cursor)
        page = MarketsPage.model_validate(raw)
        page_index += 1
        total_seen += len(page.data)

        for market in page.data:
            if (
                market.active
                and not market.closed
                and not market.archived
                and market.accepting_orders
            ):
                active_markets.append(market)

        logger.info(
            "polymarket - fetched markets page",
            extra={
                "page": page_index,
                "total_seen": total_seen,
                "active_open": len(active_markets),
                "next_cursor": page.next_cursor,
            },
        )
        next_cursor = page.next_cursor

    return active_markets
