"""Local CronConfig model for the cron deployer.

One YAML file per cron under `backend/crons/<slug>.yaml`. The file's stem
is the cron slug — no `cron_slug` field inside.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, field_validator

logger = logging.getLogger(__name__)


class CronConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule: str
    timezone: str = "UTC"

    target_service_slug: str
    target_path: str = "/"
    http_method: str = "POST"
    target_body: str | None = None

    @field_validator("schedule")
    @classmethod
    def _validate_schedule(cls, v: str) -> str:
        parts = v.strip().split()
        if len(parts) != 5:
            raise ValueError(
                "schedule must be a 5-field cron expression "
                "(minute hour day month day_of_week)"
            )
        return v

    @field_validator("http_method")
    @classmethod
    def _validate_method(cls, v: str) -> str:
        valid = {"GET", "POST", "PUT", "PATCH", "DELETE"}
        v_upper = v.upper()
        if v_upper not in valid:
            raise ValueError(f"http_method must be one of: {', '.join(sorted(valid))}")
        return v_upper

    @field_validator("target_path")
    @classmethod
    def _validate_path(cls, v: str) -> str:
        if not v.startswith("/"):
            raise ValueError("target_path must start with '/'")
        return v

    @classmethod
    def load_config(cls, cron_yaml: Path) -> Self:
        logger.info(f"Loading CronConfig from {cron_yaml}")
        with open(cron_yaml) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)
