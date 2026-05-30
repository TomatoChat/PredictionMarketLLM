from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .. import Market


class UpsertMarketsResponse(BaseModel):
    count: int


def upsert_markets(session: Session, rows: list[Market]) -> UpsertMarketsResponse:
    """Insert markets, updating mutable fields on conflict (id)."""
    if not rows:
        return UpsertMarketsResponse(count=0)
    stmt = insert(Market).values([row.model_dump() for row in rows])
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "question": stmt.excluded.question,
            "description": stmt.excluded.description,
            "slug": stmt.excluded.slug,
            "end_date": stmt.excluded.end_date,
            "active": stmt.excluded.active,
            "closed": stmt.excluded.closed,
            "archived": stmt.excluded.archived,
            "last_seen_at": stmt.excluded.last_seen_at,
        },
    )
    session.execute(stmt)
    return UpsertMarketsResponse(count=len(rows))
