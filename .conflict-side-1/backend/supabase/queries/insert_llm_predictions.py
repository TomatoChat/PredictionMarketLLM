from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.supabase import LLMPrediction


class InsertLLMPredictionsResponse(BaseModel):
    count: int


def insert_llm_predictions(
    session: Session, rows: list[LLMPrediction]
) -> InsertLLMPredictionsResponse:
    """Append-only insert of llm_prediction rows. No upsert: predictions are immutable runs."""
    if not rows:
        return InsertLLMPredictionsResponse(count=0)
    session.execute(insert(LLMPrediction).values([row.model_dump() for row in rows]))
    return InsertLLMPredictionsResponse(count=len(rows))
