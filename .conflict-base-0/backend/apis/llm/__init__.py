"""Local-import bridge for the llm api service.

The api service container imports `from src.X import Y` directly; this file
exists so that **inside the repo** (e.g. crons or tests) we can write
`from backend.apis.llm.<X>` against the api package. It also inserts
`backend/` into sys.path so the api code's `from supabase import …` /
`from qdrant import …` / `from embedder import …` references resolve when
imported locally.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[2]
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))
