from pydantic import BaseModel, ConfigDict, Field


class RewardRate(BaseModel):
    model_config = ConfigDict(extra="allow")

    asset_address: str = Field(
        ..., description="ERC-20 contract address of the asset paid out as reward."
    )
    rewards_daily_rate: float = Field(
        ...,
        description="Total amount of the asset distributed per day to liquidity providers.",
    )
