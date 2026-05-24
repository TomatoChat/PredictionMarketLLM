from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    model_config = ConfigDict(extra="allow")

    token_id: str = Field(
        ...,
        description="ERC-1155 token id (as a decimal string) for this outcome on Polymarket.",
    )
    outcome: str = Field(
        ...,
        description="Human-readable label of the outcome this token represents (e.g. 'Yes', 'No').",
    )
    price: float = Field(
        ...,
        description="Last traded price for this outcome, expressed in USDC between 0 and 1 (implied probability).",
    )
    winner: bool = Field(
        ...,
        description="True if this outcome has been declared the winning outcome upon market resolution.",
    )
