from pydantic import BaseModel, ConfigDict, Field

from .Rewards import Rewards
from .Token import Token


class Market(BaseModel):
    model_config = ConfigDict(extra="allow")

    enable_order_book: bool = Field(
        ...,
        description="Whether the central limit order book is enabled for this market.",
    )
    active: bool = Field(
        ...,
        description="Whether the market is currently active (not paused or disabled).",
    )
    closed: bool = Field(
        ...,
        description="Whether the market has been closed (resolved or no longer trading).",
    )
    archived: bool = Field(
        ...,
        description="Whether the market has been archived and is hidden from default listings.",
    )
    accepting_orders: bool = Field(
        ..., description="Whether the order book is currently accepting new orders."
    )
    accepting_order_timestamp: str | None = Field(
        ...,
        description="ISO-8601 timestamp at which the market started accepting orders, or null if it never has.",
    )
    minimum_order_size: float = Field(
        ..., description="Smallest allowed order size, expressed in shares."
    )
    minimum_tick_size: float = Field(
        ..., description="Smallest allowed price increment for limit orders, in USDC."
    )
    condition_id: str = Field(
        ...,
        description="Hex condition id (0x...) identifying this market on the Polymarket conditional-tokens framework.",
    )
    question_id: str = Field(
        ...,
        description="Hex id (0x...) of the underlying question on UMA / the resolution oracle.",
    )
    question: str = Field(
        ..., description="Human-readable question that this market resolves."
    )
    description: str = Field(
        ..., description="Long-form market description, including resolution criteria."
    )
    market_slug: str = Field(
        ..., description="URL-safe slug used to address this market on polymarket.com."
    )
    end_date_iso: str | None = Field(
        ...,
        description="ISO-8601 resolution deadline of the market, or null if no end date is set.",
    )
    game_start_time: str | None = Field(
        ...,
        description="ISO-8601 start time of the underlying event (e.g. game tip-off) for sports markets, or null.",
    )
    seconds_delay: int = Field(
        ...,
        description="Number of seconds of artificial matching delay applied to orders on this market.",
    )
    fpmm: str = Field(
        ...,
        description="Address of the legacy Fixed Product Market Maker contract for this market, or empty string if none.",
    )
    maker_base_fee: int = Field(
        ..., description="Base maker fee in basis points (1/100 of a percent)."
    )
    taker_base_fee: int = Field(
        ..., description="Base taker fee in basis points (1/100 of a percent)."
    )
    notifications_enabled: bool = Field(
        ...,
        description="Whether the API emits drop / fill notifications for this market.",
    )
    neg_risk: bool = Field(
        ...,
        description="Whether the market is part of Polymarket's negative-risk (multi-outcome) framework.",
    )
    neg_risk_market_id: str = Field(
        ...,
        description="Negative-risk market group id (0x...) this market belongs to, or empty string when not applicable.",
    )
    neg_risk_request_id: str = Field(
        ...,
        description="Negative-risk request id (0x...) used to track conversions, or empty string when not applicable.",
    )
    icon: str = Field(..., description="URL of the small market icon image.")
    image: str = Field(..., description="URL of the larger market banner image.")
    rewards: Rewards = Field(
        ..., description="Liquidity-rewards configuration that applies to this market."
    )
    is_50_50_outcome: bool = Field(
        ...,
        description="True if the market is configured to resolve 50/50 on ambiguity.",
    )
    tokens: list[Token] = Field(
        ...,
        description="Outcome tokens that can be traded on this market (typically two: Yes and No).",
    )
    tags: list[str] | None = Field(
        ...,
        description="Topical tags applied to the market for discovery (e.g. 'Politics'), or null if untagged.",
    )
