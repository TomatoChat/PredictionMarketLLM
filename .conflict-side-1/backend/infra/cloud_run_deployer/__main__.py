"""
Pulumi entry point for the Cloud Run deployer.

Discovers every service under `backend/apis/<slug>/` (any directory holding
a `deployment.yaml`) and deploys all of them in a single `pulumi up`.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pulumi

from src.helpers import deploy_service, discover_services

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

config = pulumi.Config()
gcp_config = pulumi.Config("gcp")

project_id = gcp_config.require("project")
project_id_number = config.require("projectIdNumber")
region = gcp_config.get("region") or "europe-west3"
image_repo = config.get("imageRepo") or "gcr.io"

deployer_dir = Path(__file__).parent
apis_dir = Path(
    config.get("apisDir") or (deployer_dir / ".." / ".." / "apis")
).resolve()
build_context = Path(
    config.get("buildContext") or (deployer_dir / ".." / ".." / "..")
).resolve()

service_dirs = discover_services(apis_dir)
if not service_dirs:
    raise RuntimeError(f"No services found under {apis_dir}")

pulumi.log.info(
    f"Deploying {len(service_dirs)} services: {[p.name for p in service_dirs]}"
)

for service_dir in service_dirs:
    deploy_service(
        service_dir=service_dir,
        project_id=project_id,
        project_id_number=project_id_number,
        region=region,
        image_repo=image_repo,
        build_context=build_context,
    )
