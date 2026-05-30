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
    # Registry-backed BuildKit cache: persist layers under a `:buildcache` tag in
    # the same Artifact Registry repo so a fresh CI runner (no local layer cache)
    # reuses unchanged layers instead of rebuilding from scratch every deploy.
    cache_ref = f"{image_tag.rsplit(':', 1)[0]}:buildcache"

    return docker_build.Image(
        f"{slug}-image",
        context=docker_build.BuildContextArgs(location=str(build_context)),
        dockerfile=docker_build.DockerfileArgs(
            location=str(service_dir / "Dockerfile")
        ),
        platforms=[docker_build.Platform.LINUX_AMD64],
        push=True,
        tags=[image_tag],
        cache_from=[
            docker_build.CacheFromArgs(
                registry=docker_build.CacheFromRegistryArgs(ref=cache_ref)
            )
        ],
        cache_to=[
            docker_build.CacheToArgs(
                registry=docker_build.CacheToRegistryArgs(
                    ref=cache_ref,
                    mode=docker_build.CacheMode.MAX,
                )
            )
        ],
        opts=opts,
    )
