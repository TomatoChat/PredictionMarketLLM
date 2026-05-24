from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.supabase import MarketDaily


class UpsertMarketDailyResponse(BaseModel):
    count: int


def upsert_market_daily(
    session: Session, rows: list[MarketDaily]
) -> UpsertMarketDailyResponse:
    """Insert daily snapshots, updating all measured fields on conflict (outcome_id, snapshot_date)."""
    if not rows:
        return UpsertMarketDailyResponse(count=0)
    stmt = insert(MarketDaily).values([row.model_dump() for row in rows])
    stmt = stmt.on_conflict_do_update(
        index_elements=["outcome_id", "snapshot_date"],
        set_={
            "captured_at": stmt.excluded.captured_at,
            "price": stmt.excluded.price,
            "volume": stmt.excluded.volume,
            "liquidity": stmt.excluded.liquidity,
            "active": stmt.excluded.active,
            "closed": stmt.excluded.closed,
            "archived": stmt.excluded.archived,
            "accepting_orders": stmt.excluded.accepting_orders,
        },
    )
    session.execute(stmt)
    return UpsertMarketDailyResponse(count=len(rows))
