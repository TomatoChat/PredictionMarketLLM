from pydantic import BaseModel


class ScrapeRequest(BaseModel):
    """Payload for the scrape-markets-polymarket queue.

    Carries the Polymarket CLOB cursor for one page. ``"MA=="`` is the bootstrap
    cursor sent by the orchestrator's /prepare-scraping; each /scrape handler
    chains the API's ``next_cursor`` until the end sentinel ``"LTE="``.
    """

    cursor: str = "MA=="
