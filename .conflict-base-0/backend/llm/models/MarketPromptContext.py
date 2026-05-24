from datetime import date, datetime

from pydantic import BaseModel, Field


class MarketPromptContext(BaseModel):
    """Inputs handed to the Jinja prompt templates for one market."""

    question: str
    description: str | None = None
    end_date: datetime | None = None
    outcome_labels: list[str] = Field(
        description="Ordered outcome labels; the model must return probabilities keyed by these exact strings."
    )
    today: date
