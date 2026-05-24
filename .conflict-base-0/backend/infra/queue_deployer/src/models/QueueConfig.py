"""Local QueueConfig model for the queue deployer.

One YAML file per queue under `backend/queues/<slug>.yaml`. The file's stem
is the queue name (Cloud Tasks resource name).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, field_validator

logger = logging.getLogger(__name__)

_DURATION_RE = re.compile(r"^\d+(\.\d+)?s$")


class QueueConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_concurrent_dispatches: int = 100
    max_dispatches_per_second: float = 500.0

    max_attempts: int = 3
    max_retry_duration: str = "3600s"
    min_backoff: str = "0.1s"
    max_backoff: str = "3600s"
    max_doublings: int = 16

    target_service_slug: str | None = None

    @field_validator("max_concurrent_dispatches")
    @classmethod
    def _validate_mcd(cls, v: int) -> int:
        if not 1 <= v <= 1000:
            raise ValueError("max_concurrent_dispatches must be between 1 and 1000")
        return v

    @field_validator("max_dispatches_per_second")
    @classmethod
    def _validate_mdps(cls, v: float) -> float:
        if not 0.1 <= v <= 500.0:
            raise ValueError("max_dispatches_per_second must be between 0.1 and 500.0")
        return v

    @field_validator("max_attempts")
    @classmethod
    def _validate_attempts(cls, v: int) -> int:
        # -1 means unlimited (Cloud Tasks convention)
        if v < -1 or v > 100:
            raise ValueError("max_attempts must be between -1 (unlimited) and 100")
        return v

    @field_validator("max_doublings")
    @classmethod
    def _validate_doublings(cls, v: int) -> int:
        if not 0 <= v <= 16:
            raise ValueError("max_doublings must be between 0 and 16")
        return v

    @field_validator("max_retry_duration", "min_backoff", "max_backoff")
    @classmethod
    def _validate_duration(cls, v: str) -> str:
        if not _DURATION_RE.match(v):
            raise ValueError(
                f"duration must look like '<number>s' (got {v!r})"
            )
        return v

    @classmethod
    def load_config(cls, queue_yaml: Path) -> Self:
        logger.info(f"Loading QueueConfig from {queue_yaml}")
        with open(queue_yaml) as f:
            data = yaml.safe_load(f) or {}
        return cls.model_validate(data)
