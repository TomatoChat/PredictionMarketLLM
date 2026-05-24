from pydantic import BaseModel

from .Market import Market


class ListMarketsResponse(BaseModel):
    markets: list[Market]
