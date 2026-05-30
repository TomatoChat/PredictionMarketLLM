"""Scrape one Polymarket CLOB page and upsert it to supabase.

Markets come from the CLOB ``/markets`` cursor stream (all markets, including
closed ones — that's how outcome.market_winner gets populated). Volume/liquidity
are not in the CLOB payload, so the *tradeable* subset of each page is enriched
from gamma-api by condition_id before snapshotting. Embedding + prediction
fan-out happens in the route handler via the backend/tasks/ helpers.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import uuid5

from py_clob_client_v2.client import ClobClient
from settings import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from supabase import Market, MarketOutcomeSnapshot, Outcome, Source
from supabase.consts import (
    MARKET_ID_PREFIX,
    OUTCOME_ID_PREFIX,
    UUID_NAMESPACE,
)
from supabase.queries import (
    insert_market_outcome_snapshots,
    upsert_markets,
    upsert_outcomes,
)

from ..models import MarketsPage
from .fetch_gamma_volume_liquidity import fetch_gamma_volume_liquidity
from .get_markets_with_retry import get_markets_with_retry

logger = logging.getLogger(__name__)

HOST = "https://clob.polymarket.com"
CHAIN_ID = 137
INITIAL_CURSOR = "MA=="
END_CURSOR = "LTE="


def _to_decimal(raw: object) -> Decimal | None:
    if raw is None:
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None


def _parse_end_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def scrape_polymarket_page(cursor: str) -> tuple[bool, str | None, list[str]]:
    """Fetch ONE CLOB page at ``cursor`` and upsert it to supabase.

    Returns ``(ok, next_cursor, active_market_ids)``:

    - ``ok`` is True on success, False on any caught exception.
    - ``next_cursor`` is the cursor for the following page; ``None`` (or the API
      end sentinel ``"LTE="``) means stop.
    - ``active_market_ids`` is every *tradeable* market upserted in this page
      (active, open, not archived, accepting orders), used by the route handler
      to fan out embedding + prediction tasks. Closed markets are still stored
      (so outcome.market_winner is captured) but never fanned out.
    """
    try:
        now = datetime.now(UTC)
        settings = get_settings()
        engine = create_engine(settings.database_url)

        client = ClobClient(host=HOST, chain_id=CHAIN_ID)
        raw = get_markets_with_retry(client, cursor)
        page = MarketsPage.model_validate(raw)

        # Enrich the tradeable subset with gamma volume/liquidity (one batched call).
        tradeable = [pm for pm in page.data if pm.is_tradeable]
        vol_liq = fetch_gamma_volume_liquidity([pm.condition_id for pm in tradeable])

        market_orms: list[Market] = []
        outcome_orms: list[Outcome] = []
        snapshot_orms: list[MarketOutcomeSnapshot] = []
        active_market_ids: list[str] = []

        for pm in page.data:
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
                    end_date=_parse_end_date(pm.end_date_iso),
                    active=pm.active,
                    closed=pm.closed,
                    archived=pm.archived,
                    raw=pm.model_dump(mode="json"),
                    first_seen_at=now,
                    last_seen_at=now,
                )
            )

            volume, liquidity = vol_liq.get(pm.condition_id, (None, None))

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
                        market_winner=token.winner if pm.closed else None,
                    )
                )

                if pm.is_tradeable:
                    snapshot_orms.append(
                        MarketOutcomeSnapshot(
                            outcome_id=outcome_id,
                            captured_at=now,
                            price=_to_decimal(token.price),
                            volume=volume,
                            liquidity=liquidity,
                        )
                    )

            if pm.is_tradeable:
                active_market_ids.append(market_id)

        market_orms = list({row.id: row for row in market_orms}.values())
        outcome_orms = list({row.id: row for row in outcome_orms}.values())
        snapshot_orms = list(
            {(row.outcome_id, row.captured_at): row for row in snapshot_orms}.values()
        )

        with Session(engine) as session:
            upsert_markets(session, market_orms)
            upsert_outcomes(session, outcome_orms)
            insert_market_outcome_snapshots(session, snapshot_orms)
            session.commit()

        next_cursor = page.next_cursor
        stop = not next_cursor or next_cursor == END_CURSOR
        next_cursor_out = None if stop else next_cursor

        logger.info(
            "polymarket - scraped CLOB page",
            extra={
                "cursor": cursor,
                "next_cursor": next_cursor_out,
                "markets": len(market_orms),
                "outcomes": len(outcome_orms),
                "active_markets": len(active_market_ids),
                "snapshots": len(snapshot_orms),
            },
        )
        return True, next_cursor_out, active_market_ids
    except Exception:
        logger.exception(f"polymarket - scrape page failed at cursor={cursor!r}")
        return False, None, []
