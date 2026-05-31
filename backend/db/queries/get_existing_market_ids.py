from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import Market


class GetExistingMarketIdsResponse(BaseModel):
    ids: set[str]


def get_existing_market_ids(
    session: Session, ids: list[str]
) -> GetExistingMarketIdsResponse:
    """Return the subset of ``ids`` that already exist in the market table.

    Used by the scraper to tell *newly seen* markets apart from ones it has
    upserted before — embeddings are enqueued only for the new ones (a market's
    question/description never change, so it's embedded once, open or closed).
    """
    if not ids:
        return GetExistingMarketIdsResponse(ids=set())
    rows = session.execute(select(Market.id).where(Market.id.in_(ids))).scalars().all()
    return GetExistingMarketIdsResponse(ids=set(rows))
