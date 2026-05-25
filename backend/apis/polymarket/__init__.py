"""Local-import bridge for the polymarket service.

Container code imports `from src.X import Y` directly; this file exists so
that **inside the repo** we can write `from backend.apis.polymarket.<X>` and
have the moved code's `from supabase import …` / `from qdrant import …` /
`from tasks import …` references resolve when imported locally. It inserts
`backend/` into sys.path on first import.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[2]
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from .src.helpers.scrape import scrape_polymarket_page  # noqa: E402
from .src.models import Market, MarketsPage, RewardRate, Rewards, Token  # noqa: E402

__all__ = [
    "Market",
    "MarketsPage",
    "RewardRate",
    "Rewards",
    "Token",
    "scrape_polymarket_page",
]
