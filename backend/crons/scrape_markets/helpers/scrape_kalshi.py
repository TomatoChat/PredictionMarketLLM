import logging
from datetime import UTC, datetime
from decimal import Decimal
from itertools import batched
from uuid import uuid5

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from tqdm import tqdm

from backend.kalshi import fetch_active_markets
from backend.supabase import Market, MarketDaily, Outcome, Source
from backend.supabase.consts import (
    MARKET_ID_PREFIX,
    OUTCOME_ID_PREFIX,
    UUID_NAMESPACE,
)
from settings import get_settings

BATCH_SIZE = 1000

logger = logging.getLogger(__name__)
settings = get_settings()


def _to_decimal(value: str | None) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(value)


def scrape_kalshi() -> bool:
    try:
        now = datetime.now(UTC)
        snapshot_date = now.date()
        engine = create_engine(settings.database_url)

        n_markets = 0
        n_outcomes = 0
        n_snapshots = 0

        with (
            Session(engine) as session,
            tqdm(desc="kalshi - upserting batches", unit="batch") as pbar,
        ):
            for km_batch in batched(fetch_active_markets(), BATCH_SIZE):
                market_orms: list[Market] = []
                outcome_orms: list[Outcome] = []
                daily_orms: list[MarketDaily] = []

                for km in km_batch:
                    market_uuid = uuid5(UUID_NAMESPACE, f"kalshi:{km.ticker}")
                    market_id = f"{MARKET_ID_PREFIX}{market_uuid}"

                    is_settled = km.status == "settled"
                    is_open = km.status in ("open", "active")
                    is_closed = km.status in ("closed", "settled")

                    market_orms.append(
                        Market(
                            id=market_id,
                            source=Source.KALSHI,
                            source_market_id=km.ticker,
                            question=km.title,
                            description=km.rules_primary or None,
                            slug=km.ticker,
                            end_date=km.close_time,
                            raw=km.model_dump(mode="json"),
                            first_seen_at=now,
                            last_seen_at=now,
                        )
                    )

                    yes_price = _to_decimal(km.last_price_dollars)
                    no_price = Decimal(1) - yes_price if yes_price is not None else None

                    yes_outcome_id = f"{OUTCOME_ID_PREFIX}{uuid5(UUID_NAMESPACE, f'{market_uuid}:yes')}"
                    no_outcome_id = f"{OUTCOME_ID_PREFIX}{uuid5(UUID_NAMESPACE, f'{market_uuid}:no')}"

                    outcome_orms.append(
                        Outcome(
                            id=yes_outcome_id,
                            market_id=market_id,
                            source_outcome_id="yes",
                            label=km.yes_sub_title or "Yes",
                            resolved_winner=(km.result == "yes")
                            if is_settled
                            else None,
                        )
                    )
                    outcome_orms.append(
                        Outcome(
                            id=no_outcome_id,
                            market_id=market_id,
                            source_outcome_id="no",
                            label=km.no_sub_title or "No",
                            resolved_winner=(km.result == "no") if is_settled else None,
                        )
                    )

                    volume = _to_decimal(km.volume_fp)
                    liquidity = _to_decimal(km.liquidity_dollars)

                    daily_orms.append(
                        MarketDaily(
                            outcome_id=yes_outcome_id,
                            snapshot_date=snapshot_date,
                            captured_at=now,
                            price=yes_price,
                            volume=volume,
                            liquidity=liquidity,
                            active=is_open,
                            closed=is_closed,
                            archived=False,
                            accepting_orders=is_open,
                        )
                    )
                    daily_orms.append(
                        MarketDaily(
                            outcome_id=no_outcome_id,
                            snapshot_date=snapshot_date,
                            captured_at=now,
                            price=no_price,
                            volume=volume,
                            liquidity=liquidity,
                            active=is_open,
                            closed=is_closed,
                            archived=False,
                            accepting_orders=is_open,
                        )
                    )

                market_orms = list({row.id: row for row in market_orms}.values())
                outcome_orms = list({row.id: row for row in outcome_orms}.values())
                daily_orms = list(
                    {
                        (row.outcome_id, row.snapshot_date): row for row in daily_orms
                    }.values()
                )

                market_stmt = insert(Market).values(
                    [row.model_dump() for row in market_orms]
                )
                market_stmt = market_stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "question": market_stmt.excluded.question,
                        "description": market_stmt.excluded.description,
                        "slug": market_stmt.excluded.slug,
                        "end_date": market_stmt.excluded.end_date,
                        "last_seen_at": market_stmt.excluded.last_seen_at,
                    },
                )

                session.execute(market_stmt)

                outcome_stmt = insert(Outcome).values(
                    [row.model_dump() for row in outcome_orms]
                )
                outcome_stmt = outcome_stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "label": outcome_stmt.excluded.label,
                        "resolved_winner": outcome_stmt.excluded.resolved_winner,
                    },
                )

                session.execute(outcome_stmt)

                daily_stmt = insert(MarketDaily).values(
                    [row.model_dump() for row in daily_orms]
                )
                daily_stmt = daily_stmt.on_conflict_do_update(
                    index_elements=["outcome_id", "snapshot_date"],
                    set_={
                        "captured_at": daily_stmt.excluded.captured_at,
                        "price": daily_stmt.excluded.price,
                        "volume": daily_stmt.excluded.volume,
                        "liquidity": daily_stmt.excluded.liquidity,
                        "active": daily_stmt.excluded.active,
                        "closed": daily_stmt.excluded.closed,
                        "archived": daily_stmt.excluded.archived,
                        "accepting_orders": daily_stmt.excluded.accepting_orders,
                    },
                )

                session.execute(daily_stmt)
                session.commit()

                n_markets += len(market_orms)
                n_outcomes += len(outcome_orms)
                n_snapshots += len(daily_orms)
                pbar.update(1)
                pbar.set_postfix(
                    markets=n_markets, outcomes=n_outcomes, snapshots=n_snapshots
                )

        logger.info(
            "kalshi - scrape complete",
            extra={
                "markets": n_markets,
                "outcomes": n_outcomes,
                "snapshots": n_snapshots,
            },
        )
        return True
    except Exception:
        logger.exception("kalshi - scrape failed")
        return False
