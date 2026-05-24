from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.supabase import Outcome


class GetOutcomesForMarketResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    outcomes: list[Outcome]


def get_market_outcomes(
    session: Session, market_id: str
) -> GetOutcomesForMarketResponse:
    """Return every outcome of a market, ordered by id for deterministic iteration."""
    stmt = select(Outcome).where(Outcome.market_id == market_id).order_by(Outcome.id)
    outcomes = list(session.execute(stmt).scalars().all())
    return GetOutcomesForMarketResponse(outcomes=outcomes)
