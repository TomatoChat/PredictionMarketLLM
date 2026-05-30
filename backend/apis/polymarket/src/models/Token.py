from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    """One tradable outcome token of a CLOB market."""

    model_config = ConfigDict(extra="allow")

    token_id: str = Field(
        description="ERC-1155 token id (decimal string) for this outcome on Polymarket."
    )
    outcome: str = Field(
        description="Human-readable outcome label this token represents (e.g. 'Yes', 'No')."
    )
    price: float = Field(
        default=0.0,
        description="Last traded price in USDC between 0 and 1 (implied probability).",
    )
    winner: bool = Field(
        default=False,
        description="True if this outcome was declared the winner at market resolution.",
    )
