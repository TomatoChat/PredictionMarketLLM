<<<<<<< New base: queue deployer
"""
Pulumi entry point for the queue deployer.

Discovers every queue YAML directly under `backend/queues/` (one file per
queue, named `<slug>.yaml`) and deploys each as a Cloud Tasks queue with the
declared rate limits and retry config.

Also creates a shared `task-runner` service account. Each queue YAML that
sets `target_service_slug` gets an IAM binding granting that SA
`roles/run.invoker` on the target Cloud Run service, so OIDC-authenticated
tasks the queue dispatches are accepted.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pulumi
import pulumi_gcp as gcp

from src.helpers import deploy_queue, discover_queues

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

config = pulumi.Config()
gcp_config = pulumi.Config("gcp")

project_id = gcp_config.require("project")
region = gcp_config.get("region") or "europe-west3"

deployer_dir = Path(__file__).parent
queues_dir = Path(
    config.get("queuesDir") or (deployer_dir / ".." / ".." / "queues")
).resolve()

queue_yamls = discover_queues(queues_dir)
if not queue_yamls:
    raise RuntimeError(f"No queues found under {queues_dir}")

pulumi.log.info(
    f"Deploying {len(queue_yamls)} queues: {[p.stem for p in queue_yamls]}"
)

task_runner_sa = gcp.serviceaccount.Account(
    "task-runner-sa",
    account_id="task-runner",
    display_name="Cloud Tasks OIDC Token Issuer",
    project=project_id,
)

for queue_yaml in queue_yamls:
    deploy_queue(
        queue_yaml=queue_yaml,
        project_id=project_id,
        region=region,
        task_runner_sa=task_runner_sa,
    )

pulumi.export("task_runner_service_account_email", task_runner_sa.email)
|||||||
=======
"""
Pulumi entry point for the queue deployer.

Discovers every queue YAML directly under `backend/queues/` (one file per
queue, named `<slug>.yaml`) and deploys each as a Cloud Tasks queue with the
declared rate limits and retry config.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pulumi

from src.helpers import deploy_queue, discover_queues

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

config = pulumi.Config()
gcp_config = pulumi.Config("gcp")

project_id = gcp_config.require("project")
region = gcp_config.get("region") or "europe-west3"

deployer_dir = Path(__file__).parent
queues_dir = Path(
    config.get("queuesDir") or (deployer_dir / ".." / ".." / "queues")
).resolve()

queue_yamls = discover_queues(queues_dir)
if not queue_yamls:
    raise RuntimeError(f"No queues found under {queues_dir}")

pulumi.log.info(
    f"Deploying {len(queue_yamls)} queues: {[p.stem for p in queue_yamls]}"
)

for queue_yaml in queue_yamls:
    deploy_queue(
        queue_yaml=queue_yaml,
        project_id=project_id,
        region=region,
    )
>>>>>>> Current commit: queue deployer
