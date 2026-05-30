from pydantic import BaseModel, ConfigDict, Field

from .Token import Token


class Market(BaseModel):
    """One market from Polymarket's CLOB ``/markets`` response.

    Only the fields the scraper consumes are declared; ``extra="allow"`` keeps
    the rest of the payload around (it is persisted wholesale into ``market.raw``).
    """

    model_config = ConfigDict(extra="allow")

    condition_id: str = Field(
        description="Hex condition id (0x...) identifying this market.",
    )
    question: str = Field(description="Human-readable question the market resolves.")
    description: str | None = Field(
        default=None, description="Long-form market description / resolution criteria."
    )
    market_slug: str | None = Field(
        default=None, description="URL-safe slug used on polymarket.com."
    )
    end_date_iso: str | None = Field(
        default=None, description="ISO-8601 resolution deadline, or null if unset."
    )
    active: bool = Field(
        default=False,
        description="Whether the market is active (not paused/disabled).",
    )
    closed: bool = Field(
        default=False, description="Whether the market has closed (resolved)."
    )
    archived: bool = Field(default=False, description="Whether the market is archived.")
    accepting_orders: bool = Field(
        default=False, description="Whether the order book is accepting new orders."
    )
    tokens: list[Token] = Field(
        default_factory=list,
        description="Outcome tokens for this market (typically Yes/No).",
    )

    @property
    def is_tradeable(self) -> bool:
        """True when open for prediction (active, open, not archived, accepting orders)."""
        return (
            self.active
            and not self.closed
            and not self.archived
            and self.accepting_orders
        )
