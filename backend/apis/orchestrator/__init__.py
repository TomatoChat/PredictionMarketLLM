"""Local-import bridge for the orchestrator service. See backend/apis/polymarket/__init__.py."""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[2]

if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))
