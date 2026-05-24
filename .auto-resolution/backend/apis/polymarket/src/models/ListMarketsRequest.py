from pydantic import BaseModel


class ListMarketsRequest(BaseModel):
    limit: int = 10
