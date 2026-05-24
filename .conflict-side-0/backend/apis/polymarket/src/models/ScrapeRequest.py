from pydantic import BaseModel


class ScrapeRequest(BaseModel):
    """Payload for the scrape-markets-polymarket queue.

    Carries the Polymarket cursor for one page. ``"MA=="`` is the bootstrap
    cursor sent by the orchestrator's /prepare-scraping.
    """

    cursor: str
