from collections.abc import Callable

from backend.crons.scrape_markets.helpers import scrape_polymarket

SCRAPERS: list[Callable[[], bool]] = [
    scrape_polymarket,
]


def main() -> bool:
    return all([scraper() for scraper in SCRAPERS])
