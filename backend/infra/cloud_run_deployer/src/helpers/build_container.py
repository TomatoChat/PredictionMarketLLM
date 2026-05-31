import pulumi
import pulumi_gcp as gcp

from ..models import DeploymentConfig


def build_container(
    image_ref: pulumi.Input[str],
    deployment_config: DeploymentConfig,
    port: int,
    volume_mounts: list[gcp.cloudrunv2.ServiceTemplateContainerVolumeMountArgs]
    | None = None,
) -> gcp.cloudrunv2.ServiceTemplateContainerArgs:
    env_vars = [
        gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(name=k, value=v)
        for k, v in deployment_config.environment_variables.items()
    ]

    startup_timeout = deployment_config.startup_probe_timeout

    if startup_timeout >= deployment_config.startup_probe_period:
        startup_timeout = deployment_config.startup_probe_period - 1

    return gcp.cloudrunv2.ServiceTemplateContainerArgs(
        image=image_ref,
        ports=gcp.cloudrunv2.ServiceTemplateContainerPortsArgs(container_port=port),
        envs=env_vars,
        volume_mounts=volume_mounts,
        resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
            limits={
                "memory": f"{deployment_config.memory}Mi",
                "cpu": str(deployment_config.cpu),
            },
            cpu_idle=True,
        ),
        startup_probe=gcp.cloudrunv2.ServiceTemplateContainerStartupProbeArgs(
            http_get=gcp.cloudrunv2.ServiceTemplateContainerStartupProbeHttpGetArgs(
                path=deployment_config.startup_probe_path,
                port=port,
            ),
            initial_delay_seconds=deployment_config.startup_probe_initial_delay,
            timeout_seconds=startup_timeout,
            period_seconds=deployment_config.startup_probe_period,
            failure_threshold=deployment_config.startup_probe_failure_threshold,
        ),
        liveness_probe=gcp.cloudrunv2.ServiceTemplateContainerLivenessProbeArgs(
            http_get=gcp.cloudrunv2.ServiceTemplateContainerLivenessProbeHttpGetArgs(
                path=deployment_config.health_check_path,
                port=port,
            ),
            timeout_seconds=deployment_config.health_check_timeout,
            period_seconds=deployment_config.health_check_interval,
            failure_threshold=deployment_config.health_check_failure_threshold,
        ),
    )
