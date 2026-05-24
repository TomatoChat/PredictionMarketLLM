from pydantic import BaseModel


class EmbedMarketRequest(BaseModel):
    """Payload for the save-embeddings-markets queue."""

    market_id: str
