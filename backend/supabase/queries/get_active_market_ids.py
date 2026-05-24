from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import Market, MarketDaily, Outcome


class GetActiveMarketIdsResponse(BaseModel):
    market_ids: list[str]


def get_active_market_ids(session: Session) -> GetActiveMarketIdsResponse:
    """Market ids whose latest snapshot (today's scrape) is active and not closed."""
    today = datetime.now(UTC).date()
    stmt = (
        select(Market.id)
        .join(Outcome, Outcome.market_id == Market.id)
        .join(MarketDaily, MarketDaily.outcome_id == Outcome.id)
        .where(MarketDaily.snapshot_date == today)
        .where(MarketDaily.active.is_(True))
        .where(MarketDaily.closed.is_(False))
        .distinct()
    )
    return GetActiveMarketIdsResponse(
        market_ids=list(session.execute(stmt).scalars().all())
    )
