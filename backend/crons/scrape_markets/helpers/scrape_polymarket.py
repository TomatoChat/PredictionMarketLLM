import logging
from datetime import UTC, datetime
from itertools import batched
from uuid import uuid5

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.polymarket import fetch_active_markets
from backend.supabase import Market, MarketDaily, Outcome, Source
from backend.supabase.consts import (
    DATABASE_URL,
    MARKET_ID_PREFIX,
    OUTCOME_ID_PREFIX,
    UUID_NAMESPACE,
)

BATCH_SIZE = 1000

logger = logging.getLogger(__name__)


def scrape_polymarket() -> bool:
    try:
        markets = fetch_active_markets()
        now = datetime.now(UTC)
        snapshot_date = now.date()

        market_orms: list[Market] = []
        outcome_orms: list[Outcome] = []
        daily_orms: list[MarketDaily] = []

        for market in markets:
            market_uuid = uuid5(UUID_NAMESPACE, f"polymarket:{market.condition_id}")
            market_id = f"{MARKET_ID_PREFIX}{market_uuid}"

            market_orms.append(
                Market(
                    id=market_id,
                    source=Source.POLYMARKET,
                    source_market_id=market.condition_id,
                    question=market.question,
                    description=market.description,
                    slug=market.market_slug,
                    end_date=(
                        datetime.fromisoformat(
                            market.end_date_iso.replace("Z", "+00:00")
                        )
                        if market.end_date_iso
                        else None
                    ),
                    raw=market.model_dump(mode="json"),
                    first_seen_at=now,
                    last_seen_at=now,
                )
            )

            for token in market.tokens:
                outcome_id = f"{OUTCOME_ID_PREFIX}{uuid5(UUID_NAMESPACE, f'{market_uuid}:{token.token_id}')}"

                outcome_orms.append(
                    Outcome(
                        id=outcome_id,
                        market_id=market_id,
                        source_outcome_id=token.token_id,
                        label=token.outcome,
                        resolved_winner=token.winner if market.closed else None,
                    )
                )
                daily_orms.append(
                    MarketDaily(
                        outcome_id=outcome_id,
                        snapshot_date=snapshot_date,
                        captured_at=now,
                        price=token.price,
                        volume=None,
                        liquidity=None,
                        active=market.active,
                        closed=market.closed,
                        archived=market.archived,
                        accepting_orders=market.accepting_orders,
                    )
                )

        market_orms = list({row.id: row for row in market_orms}.values())
        outcome_orms = list({row.id: row for row in outcome_orms}.values())
        daily_orms = list(
            {(row.outcome_id, row.snapshot_date): row for row in daily_orms}.values()
        )

        engine = create_engine(DATABASE_URL)

        with Session(engine) as session:
            for chunk in batched(market_orms, BATCH_SIZE):
                stmt = insert(Market).values([row.model_dump() for row in chunk])
                stmt = stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "question": stmt.excluded.question,
                        "description": stmt.excluded.description,
                        "slug": stmt.excluded.slug,
                        "end_date": stmt.excluded.end_date,
                        "raw": stmt.excluded.raw,
                        "last_seen_at": stmt.excluded.last_seen_at,
                    },
                )

                session.execute(stmt)

            for chunk in batched(outcome_orms, BATCH_SIZE):
                stmt = insert(Outcome).values([row.model_dump() for row in chunk])
                stmt = stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "label": stmt.excluded.label,
                        "resolved_winner": stmt.excluded.resolved_winner,
                    },
                )

                session.execute(stmt)

            for chunk in batched(daily_orms, BATCH_SIZE):
                stmt = insert(MarketDaily).values([row.model_dump() for row in chunk])
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

            session.commit()

        logger.info(
            "polymarket - scrape complete",
            extra={
                "markets": len(market_orms),
                "outcomes": len(outcome_orms),
                "snapshots": len(daily_orms),
            },
        )
        return True
    except Exception:
        logger.exception("polymarket - scrape failed")
        return False
