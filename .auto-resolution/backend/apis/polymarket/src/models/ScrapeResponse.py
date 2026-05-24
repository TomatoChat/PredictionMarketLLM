from pydantic import BaseModel


class ScrapeResponse(BaseModel):
    ok: bool
    next_cursor: str | None = None
    new_markets: int = 0
