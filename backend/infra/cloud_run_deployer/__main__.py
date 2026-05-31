"""
Pulumi entry point for the Cloud Run deployer.

Discovers every service under `backend/apis/<slug>/` (any directory holding
a `deployment.yaml`) and deploys all of them in a single `pulumi up`.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pulumi
import pulumi_gcp as gcp

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
ar_repo_id = config.get("artifactRegistryRepoId") or "apis"

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

ar_repo = gcp.artifactregistry.Repository(
    "apis-ar-repo",
    repository_id=ar_repo_id,
    location=region,
    project=project_id,
    format="DOCKER",
    description="Container images for the Cloud Run apis",
)

image_repo = f"{region}-docker.pkg.dev/{project_id}/{ar_repo_id}"

# Bucket for offloaded raw payloads (market.raw_path, llm_prediction.raw_response_path).
# Kept out of Postgres to save DB storage + egress; written by the polymarket and
# llm services, which run as the default compute SA.
raw_bucket_name = config.get("rawBucketName") or f"{project_id}-raw"
raw_bucket = gcp.storage.Bucket(
    "raw-payloads-bucket",
    name=raw_bucket_name,
    project=project_id,
    location=region,
    uniform_bucket_level_access=True,
)
runtime_sa_email = f"{project_id_number}-compute@developer.gserviceaccount.com"
gcp.storage.BucketIAMMember(
    "raw-payloads-bucket-writer",
    bucket=raw_bucket.name,
    role="roles/storage.objectAdmin",
    member=f"serviceAccount:{runtime_sa_email}",
)
pulumi.export("raw_bucket_name", raw_bucket.name)

# Cloud SQL instance is provisioned by the separate cloud_sql_deployer stack.
# Pull its connection name so we can mount it as a Unix socket on each service
# that opts in via `needs_cloudsql: true` in deployment.yaml.
cloud_sql_stack = pulumi.StackReference(
    config.get("cloudSqlStackRef") or f"organization/cloud-sql-deployer/{pulumi.get_stack()}"
)
cloud_sql_connection_name = cloud_sql_stack.get_output("instance_connection_name")

# Cloud Run needs roles/cloudsql.client on the runtime SA to open the socket.
gcp.projects.IAMMember(
    "runtime-sa-cloudsql-client",
    project=project_id,
    role="roles/cloudsql.client",
    member=f"serviceAccount:{runtime_sa_email}",
)

for service_dir in service_dirs:
    deploy_service(
        service_dir=service_dir,
        project_id=project_id,
        project_id_number=project_id_number,
        region=region,
        image_repo=image_repo,
        build_context=build_context,
        cloud_sql_instance_connection_name=cloud_sql_connection_name,
        depends_on=[ar_repo],
    )
