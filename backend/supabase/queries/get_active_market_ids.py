from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import Market


class GetActiveMarketIdsResponse(BaseModel):
    market_ids: list[str]


def get_active_market_ids(session: Session) -> GetActiveMarketIdsResponse:
    """Market ids that are tradeable as of the last scrape (active, open, not archived)."""
    stmt = (
        select(Market.id)
        .where(Market.active.is_(True))
        .where(Market.closed.is_(False))
        .where(Market.archived.is_(False))
    )
    return GetActiveMarketIdsResponse(
        market_ids=list(session.execute(stmt).scalars().all())
    )
