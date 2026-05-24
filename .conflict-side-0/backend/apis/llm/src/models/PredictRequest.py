from pydantic import BaseModel


class PredictRequest(BaseModel):
    """Payload for the solve-market-llm queue."""

    config_name: str
    market_id: str
    dry_run: bool = False
