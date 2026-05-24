"""Scrape one Polymarket cursor page and upsert it to supabase.

Embedding + prediction fan-out happens in the route handler via the
backend/tasks/ helpers — this module is supabase-only.
"""

import logging
from datetime import UTC, datetime
from uuid import uuid5

from py_clob_client_v2.client import ClobClient
from settings import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from supabase import Market, MarketDaily, Outcome, OutcomeSnapshot, Source
from supabase.consts import (
    MARKET_ID_PREFIX,
    OUTCOME_ID_PREFIX,
    UUID_NAMESPACE,
)
from supabase.queries import (
    insert_outcome_snapshots,
    upsert_market_daily,
    upsert_markets,
    upsert_outcomes,
)

from ..models import MarketsPage
from .get_markets_with_retry import get_markets_with_retry

logger = logging.getLogger(__name__)

HOST = "https://clob.polymarket.com"
CHAIN_ID = 137
INITIAL_CURSOR = "MA=="
END_CURSOR = "LTE="


def scrape_polymarket_page(cursor: str) -> tuple[bool, str | None, list[str]]:
    """Fetch ONE Polymarket page at ``cursor`` and upsert it to supabase.

    Returns ``(ok, next_cursor, new_market_ids)``:

    - ``ok`` is True on success, False on any caught exception.
    - ``next_cursor`` is the cursor for the *following* page; the caller chains
      it back into the queue. ``None`` or the API's end sentinel means stop.
    - ``new_market_ids`` is every active market upserted in this page, used by
      the route handler to fan out embedding + prediction tasks.
    """
    try:
        now = datetime.now(UTC)
        snapshot_date = now.date()
        settings = get_settings()
        engine = create_engine(settings.database_url)

        client = ClobClient(host=HOST, chain_id=CHAIN_ID)
        raw = get_markets_with_retry(client, cursor)
        page = MarketsPage.model_validate(raw)

        active = [
            pm
            for pm in page.data
            if pm.active and not pm.closed and not pm.archived and pm.accepting_orders
        ]

        market_orms: list[Market] = []
        outcome_orms: list[Outcome] = []
        daily_orms: list[MarketDaily] = []
        snapshot_orms: list[OutcomeSnapshot] = []

        for pm in active:
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
                outcome_id = (
                    f"{OUTCOME_ID_PREFIX}"
                    f"{uuid5(UUID_NAMESPACE, f'{market_uuid}:{token.token_id}')}"
                )
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
                snapshot_orms.append(
                    OutcomeSnapshot(
                        outcome_id=outcome_id,
                        captured_at=now,
                        price=token.price,
                    )
                )

        market_orms = list({row.id: row for row in market_orms}.values())
        outcome_orms = list({row.id: row for row in outcome_orms}.values())
        daily_orms = list(
            {(row.outcome_id, row.snapshot_date): row for row in daily_orms}.values()
        )
        snapshot_orms = list(
            {(row.outcome_id, row.captured_at): row for row in snapshot_orms}.values()
        )

        with Session(engine) as session:
            upsert_markets(session, market_orms)
            upsert_outcomes(session, outcome_orms)
            upsert_market_daily(session, daily_orms)
            insert_outcome_snapshots(session, snapshot_orms)
            session.commit()

        logger.info(
            "polymarket - scraped page",
            extra={
                "cursor": cursor,
                "next_cursor": page.next_cursor,
                "markets": len(market_orms),
                "outcomes": len(outcome_orms),
                "snapshots": len(daily_orms),
            },
        )
        return True, page.next_cursor, [m.id for m in market_orms]
    except Exception:
        logger.exception(f"polymarket - scrape page failed at cursor={cursor!r}")
        return False, None, []
