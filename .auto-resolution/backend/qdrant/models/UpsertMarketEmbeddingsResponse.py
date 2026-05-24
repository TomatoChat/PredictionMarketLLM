from pydantic import BaseModel


class UpsertMarketEmbeddingsResponse(BaseModel):
    count: int
