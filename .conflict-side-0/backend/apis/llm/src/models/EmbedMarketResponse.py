from pydantic import BaseModel


class EmbedMarketResponse(BaseModel):
    embedded: bool
