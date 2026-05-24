from pydantic import BaseModel


class PrepareScrapingResponse(BaseModel):
    enqueued: int
