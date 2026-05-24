import base64
from pathlib import Path

import pulumi
import pulumi_gcp as gcp

from ..models import CronConfig


def deploy_cron(
    cron_yaml: Path,
    project_id: str,
    region: str,
    scheduler_sa: gcp.serviceaccount.Account,
) -> None:
    slug = cron_yaml.stem
    cron_config = CronConfig.load_config(cron_yaml)

    target_service = gcp.cloudrunv2.get_service_output(
        name=cron_config.target_service_slug,
        project=project_id,
        location=region,
    )
    target_uri = pulumi.Output.concat(target_service.uri, cron_config.target_path)

    gcp.cloudrunv2.ServiceIamMember(
        f"{slug}-invoker",
        project=project_id,
        location=region,
        name=cron_config.target_service_slug,
        role="roles/run.invoker",
        member=pulumi.Output.concat("serviceAccount:", scheduler_sa.email),
    )

    body_b64 = (
        base64.b64encode(cron_config.target_body.encode()).decode()
        if cron_config.target_body
        else None
    )
    headers = {"Content-Type": "application/json"} if cron_config.target_body else None

    scheduler_job = gcp.cloudscheduler.Job(
        f"{slug}-scheduler",
        name=f"cron-{slug}",
        region=region,
        project=project_id,
        schedule=cron_config.schedule,
        time_zone=cron_config.timezone,
        http_target=gcp.cloudscheduler.JobHttpTargetArgs(
            http_method=cron_config.http_method,
            uri=target_uri,
            body=body_b64,
            headers=headers,
            oidc_token=gcp.cloudscheduler.JobHttpTargetOidcTokenArgs(
                service_account_email=scheduler_sa.email,
                audience=target_service.uri,
            ),
        ),
    )

    pulumi.export(f"{slug}_target_uri", target_uri)
    pulumi.export(f"{slug}_scheduler_name", scheduler_job.name)
