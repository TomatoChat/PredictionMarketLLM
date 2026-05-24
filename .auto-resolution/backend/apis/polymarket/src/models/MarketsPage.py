from pydantic import BaseModel, ConfigDict, Field

from .Market import Market


class MarketsPage(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: list[Market] = Field(
        ...,
        description="Markets returned in this page of the paginated /markets response.",
    )
    next_cursor: str = Field(
        ...,
        description="Opaque cursor to pass back as next_cursor for the next page; equals 'LTE=' when no more pages remain.",
    )
    limit: int = Field(
        ...,
        description="Maximum number of markets the server is willing to return per page.",
    )
    count: int = Field(
        ..., description="Number of markets actually returned in this page."
    )
