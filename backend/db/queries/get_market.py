from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session, load_only

from .. import Market


class GetMarketResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    market: Market | None


def get_market(session: Session, market_id: str) -> GetMarketResponse:
    """Load one market, deferring the heavy ``raw`` JSONB.

    Predict/embed only read question/description/end_date/source, so the full
    raw payload is left unloaded to keep these reads off the egress meter.
    """
    stmt = (
        select(Market)
        .where(Market.id == market_id)
        .options(
            load_only(
                Market.source,
                Market.question,
                Market.description,
                Market.end_date,
            )
        )
    )
    return GetMarketResponse(market=session.scalars(stmt).first())
