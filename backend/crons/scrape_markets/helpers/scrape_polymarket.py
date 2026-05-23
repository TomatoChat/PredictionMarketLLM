import logging
from datetime import UTC, datetime
from itertools import batched
from uuid import uuid5

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tqdm import tqdm

from backend.polymarket import fetch_active_markets
from backend.supabase import Market, MarketDaily, Outcome, Source
from backend.supabase.consts import (
    MARKET_ID_PREFIX,
    OUTCOME_ID_PREFIX,
    UUID_NAMESPACE,
)
from backend.supabase.queries import (
    upsert_market_daily,
    upsert_markets,
    upsert_outcomes,
)
from settings import get_settings

BATCH_SIZE = 1000

logger = logging.getLogger(__name__)
settings = get_settings()


def scrape_polymarket() -> bool:
    try:
        now = datetime.now(UTC)
        snapshot_date = now.date()
        engine = create_engine(settings.database_url)

        n_markets = 0
        n_outcomes = 0
        n_snapshots = 0

        with (
            Session(engine) as session,
            tqdm(desc="polymarket - upserting batches", unit="batch") as pbar,
        ):
            for pm_batch in batched(fetch_active_markets(), BATCH_SIZE):
                market_orms: list[Market] = []
                outcome_orms: list[Outcome] = []
                daily_orms: list[MarketDaily] = []

                for pm in pm_batch:
                    market_uuid = uuid5(UUID_NAMESPACE, f"polymarket:{pm.condition_id}")
                    market_id = f"{MARKET_ID_PREFIX}{market_uuid}"

                    market_orms.append(
                        Market(
                            id=market_id,
                            source=Source.POLYMARKET,
                            source_market_id=pm.condition_id,
                            question=pm.question,
                            description=pm.description,
                            slug=pm.market_slug,
                            end_date=(
                                datetime.fromisoformat(
                                    pm.end_date_iso.replace("Z", "+00:00")
                                )
                                if pm.end_date_iso
                                else None
                            ),
                            raw=pm.model_dump(mode="json"),
                            first_seen_at=now,
                            last_seen_at=now,
                        )
                    )

                    for token in pm.tokens:
                        outcome_id = f"{OUTCOME_ID_PREFIX}{uuid5(UUID_NAMESPACE, f'{market_uuid}:{token.token_id}')}"

                        outcome_orms.append(
                            Outcome(
                                id=outcome_id,
                                market_id=market_id,
                                source_outcome_id=token.token_id,
                                label=token.outcome,
                                resolved_winner=token.winner if pm.closed else None,
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
                                active=pm.active,
                                closed=pm.closed,
                                archived=pm.archived,
                                accepting_orders=pm.accepting_orders,
                            )
                        )

                market_orms = list({row.id: row for row in market_orms}.values())
                outcome_orms = list({row.id: row for row in outcome_orms}.values())
                daily_orms = list(
                    {
                        (row.outcome_id, row.snapshot_date): row for row in daily_orms
                    }.values()
                )

                upsert_markets(session, market_orms)
                upsert_outcomes(session, outcome_orms)
                upsert_market_daily(session, daily_orms)
                session.commit()

                n_markets += len(market_orms)
                n_outcomes += len(outcome_orms)
                n_snapshots += len(daily_orms)
                pbar.update(1)
                pbar.set_postfix(
                    markets=n_markets, outcomes=n_outcomes, snapshots=n_snapshots
                )

        logger.info(
            "polymarket - scrape complete",
            extra={
                "markets": n_markets,
                "outcomes": n_outcomes,
                "snapshots": n_snapshots,
            },
        )
        return True
    except Exception:
        logger.exception("polymarket - scrape failed")
        return False
