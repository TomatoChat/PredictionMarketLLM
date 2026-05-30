from pydantic import BaseModel, ConfigDict, Field

from .Market import Market


class MarketsPage(BaseModel):
    """One page of the CLOB ``/markets`` paginated response."""

    model_config = ConfigDict(extra="allow")

    data: list[Market] = Field(
        default_factory=list, description="Markets returned in this page."
    )
    next_cursor: str = Field(
        default="LTE=",
        description="Cursor for the next page; equals 'LTE=' when no pages remain.",
    )
    limit: int = Field(default=0, description="Max markets the server returns per page.")
    count: int = Field(default=0, description="Number of markets in this page.")
