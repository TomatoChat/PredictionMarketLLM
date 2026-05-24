"""
Pulumi entry point for the cron deployer.

Discovers every cron YAML directly under `backend/crons/` (one file per cron,
named `<slug>.yaml`) and deploys each as a Cloud Scheduler job that calls
the target api service's HTTP endpoint via OIDC-authenticated request.

The actual cron logic lives in the corresponding `backend/apis/<target_service_slug>/`
service — this deployer never builds images or runs containers.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pulumi
import pulumi_gcp as gcp

from src.helpers import deploy_cron, discover_crons

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

config = pulumi.Config()
gcp_config = pulumi.Config("gcp")

project_id = gcp_config.require("project")
region = gcp_config.get("region") or "europe-west3"

deployer_dir = Path(__file__).parent
crons_dir = Path(
    config.get("cronsDir") or (deployer_dir / ".." / ".." / "crons")
).resolve()

cron_yamls = discover_crons(crons_dir)
if not cron_yamls:
    raise RuntimeError(f"No crons found under {crons_dir}")

pulumi.log.info(
    f"Deploying {len(cron_yamls)} crons: {[p.stem for p in cron_yamls]}"
)

scheduler_sa = gcp.serviceaccount.Account(
    "cron-scheduler-sa",
    account_id="cron-scheduler",
    display_name="Cloud Scheduler Cron Trigger",
    project=project_id,
)

for cron_yaml in cron_yamls:
    deploy_cron(
        cron_yaml=cron_yaml,
        project_id=project_id,
        region=region,
        scheduler_sa=scheduler_sa,
    )

pulumi.export("scheduler_service_account_email", scheduler_sa.email)
