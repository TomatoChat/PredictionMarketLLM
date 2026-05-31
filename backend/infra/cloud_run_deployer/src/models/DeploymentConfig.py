"""
Local DeploymentConfig model for the Cloud Run deployer.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class DeploymentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_slug: str
    service_name: str
    is_public: bool

    memory: int
    cpu: float
    min_instances: int
    max_instances: int
    concurrency: int
    timeout: int

    environment_variables: dict[str, str] = {}

    needs_cloudsql: bool = False

    startup_probe_path: str
    startup_probe_initial_delay: int
    startup_probe_timeout: int
    startup_probe_period: int
    startup_probe_failure_threshold: int

    health_check_path: str
    health_check_timeout: int
    health_check_interval: int
    health_check_failure_threshold: int

    @classmethod
    def load_config(cls, service_dir: Path) -> Self:
        config_path = service_dir / "deployment.yaml"
        logger.info(f"Loading DeploymentConfig from {config_path}")
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)
