from pathlib import Path

import pulumi
import pulumi_docker_build as docker_build


def build_image(
    slug: str,
    service_dir: Path,
    build_context: Path,
    image_tag: str,
    opts: pulumi.ResourceOptions | None = None,
) -> docker_build.Image:
    return docker_build.Image(
        f"{slug}-image",
        context=docker_build.BuildContextArgs(location=str(build_context)),
        dockerfile=docker_build.DockerfileArgs(
            location=str(service_dir / "Dockerfile")
        ),
        platforms=[docker_build.Platform.LINUX_AMD64],
        push=True,
        tags=[image_tag],
        opts=opts,
    )
