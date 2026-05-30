"""Enrich CLOB markets with volume/liquidity from Polymarket's gamma-api.

The CLOB ``/markets`` payload has no volume/liquidity; gamma does, keyed by the
same ``conditionId``. We look those up in batches (gamma accepts repeated
``condition_ids`` params) so one HTTP call covers a whole page's active subset.
"""

import logging
from decimal import Decimal, InvalidOperation

import httpx

logger = logging.getLogger(__name__)

GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"
BATCH_SIZE = 50
REQUEST_TIMEOUT_SECONDS = 30.0

VolumeLiquidity = tuple[Decimal | None, Decimal | None]


def _to_decimal(raw: object) -> Decimal | None:
    if raw is None:
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None


def fetch_gamma_volume_liquidity(
    condition_ids: list[str],
) -> dict[str, VolumeLiquidity]:
    """Return ``{condition_id: (volume, liquidity)}`` for the given markets.

    Best-effort: condition ids gamma doesn't know are simply absent from the
    result, and any failed batch is logged and skipped (enrichment is optional,
    so a gamma hiccup must never fail the scrape).
    """
    result: dict[str, VolumeLiquidity] = {}
    if not condition_ids:
        return result

    for start in range(0, len(condition_ids), BATCH_SIZE):
        batch = condition_ids[start : start + BATCH_SIZE]
        params = [("condition_ids", cid) for cid in batch]
        params.append(("limit", str(len(batch))))
        try:
            resp = httpx.get(
                GAMMA_MARKETS_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS
            )
            resp.raise_for_status()
            payload = resp.json()
            if not isinstance(payload, list):
                continue
            for m in payload:
                cid = m.get("conditionId")
                if cid:
                    result[cid] = (
                        _to_decimal(m.get("volume")),
                        _to_decimal(m.get("liquidity")),
                    )
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(
                f"polymarket - gamma volume/liquidity batch failed "
                f"({start}..{start + len(batch)}): {exc}"
            )

    return result
