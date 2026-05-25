from pathlib import Path

import pulumi
import pulumi_gcp as gcp

from ..models import DeploymentConfig
from .build_container import build_container
from .build_image import build_image

PORT = 8080


def deploy_service(
    service_dir: Path,
    project_id: str,
    project_id_number: str,
    region: str,
    image_repo: str,
    build_context: Path,
    depends_on: list[pulumi.Resource] | None = None,
) -> None:
    slug = service_dir.name
    deployment_config = DeploymentConfig.load_config(service_dir)
    deployment_config.environment_variables.update(
        {
            "GCP_PROJECT_ID": project_id,
            "GCP_PROJECT_ID_NUMBER": project_id_number,
            "GCP_REGION": region,
        }
    )

    image_tag = f"{image_repo}/{deployment_config.service_slug}:latest"
    image = build_image(
        slug=slug,
        service_dir=service_dir,
        build_context=build_context,
        image_tag=image_tag,
        opts=pulumi.ResourceOptions(depends_on=depends_on) if depends_on else None,
    )

    container = build_container(
        image_ref=image.ref,
        deployment_config=deployment_config,
        port=PORT,
    )

    service = gcp.cloudrunv2.Service(
        f"{slug}-service",
        name=deployment_config.service_slug,
        location=region,
        project=project_id,
        ingress=(
            "INGRESS_TRAFFIC_ALL"
            if deployment_config.is_public
            else "INGRESS_TRAFFIC_INTERNAL_ONLY"
        ),
        template=gcp.cloudrunv2.ServiceTemplateArgs(
            containers=[container],
            scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
                min_instance_count=deployment_config.min_instances,
                max_instance_count=deployment_config.max_instances,
            ),
            timeout=f"{deployment_config.timeout}s",
            max_instance_request_concurrency=deployment_config.concurrency,
        ),
    )

    pulumi.export(f"{slug}_service_name", service.name)
    pulumi.export(f"{slug}_service_url", service.uri)
    pulumi.export(f"{slug}_image_digest", image.ref)
