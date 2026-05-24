from pydantic import BaseModel, ConfigDict, Field

from .RewardRate import RewardRate


class Rewards(BaseModel):
    model_config = ConfigDict(extra="allow")

    rates: list[RewardRate] | None = Field(
        ...,
        description="Per-asset daily reward emission rates for this market, or null when no rewards program is active.",
    )
    min_size: float = Field(
        ...,
        description="Minimum order size (in shares) that qualifies a maker order for liquidity rewards.",
    )
    max_spread: float = Field(
        ...,
        description="Maximum distance from the midpoint (in cents) at which a maker order still qualifies for rewards.",
    )
