"""Scrape one Polymarket CLOB page and upsert it to Postgres.

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
from raw_store import RawStore
from settings import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from db import Market, MarketOutcomeSnapshot, Outcome, Source
from db.consts import (
    MARKET_ID_PREFIX,
    OUTCOME_ID_PREFIX,
    UUID_NAMESPACE,
)
from db.queries import (
    get_existing_market_ids,
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
    """Fetch ONE CLOB page at ``cursor`` and upsert it to Postgres.

    Returns ``(ok, next_cursor, new_market_ids, active_market_ids)``:

    - ``ok`` is True on success, False on any caught exception.
    - ``next_cursor`` is the cursor for the following page; ``None`` (or the API
      end sentinel ``"LTE="``) means stop.
    - ``new_market_ids`` is every market seen for the *first time* on this page
      (open or closed), used to fan out embedding tasks — a market's question /
      description never change, so it's embedded exactly once.
    - ``active_market_ids`` is every *tradeable* market on this page (active,
      open, not archived, accepting orders), used to fan out prediction tasks
      every walk. Closed markets are stored (so outcome.market_winner is
      captured) and embedded once, but never predicted.
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
        raw_by_market_id: dict[str, dict] = {}

        for pm in page.data:
            market_uuid = uuid5(UUID_NAMESPACE, f"polymarket:{pm.condition_id}")
            market_id = f"{MARKET_ID_PREFIX}{market_uuid}"

            raw_by_market_id[market_id] = pm.model_dump(mode="json")
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
        market_by_id = {row.id: row for row in market_orms}

        all_market_ids = [row.id for row in market_orms]

        with Session(engine) as session:
            # Determine which markets are new *before* upserting (so existing
            # reflects the pre-upsert state). New markets get embedded once.
            existing_ids = get_existing_market_ids(session, all_market_ids).ids
            new_market_ids = [mid for mid in all_market_ids if mid not in existing_ids]

            # Raw payloads never change, so (like embeddings) upload them once for
            # new markets only and set raw_path. upsert_markets leaves raw_path out
            # of its ON CONFLICT set, so re-scraped markets keep their stored path.
            raw_paths = RawStore().put_many_json(
                {f"market/{mid}.json.gz": raw_by_market_id[mid] for mid in new_market_ids}
            )
            for mid in new_market_ids:
                market_by_id[mid].raw_path = raw_paths[f"market/{mid}.json.gz"]

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
                "new_markets": len(new_market_ids),
                "active_markets": len(active_market_ids),
                "snapshots": len(snapshot_orms),
            },
        )
        return True, next_cursor_out, new_market_ids, active_market_ids
    except Exception:
        logger.exception(f"polymarket - scrape page failed at cursor={cursor!r}")
        return False, None, [], []
