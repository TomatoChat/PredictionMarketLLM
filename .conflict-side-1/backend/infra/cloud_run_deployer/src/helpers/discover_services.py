from pathlib import Path


def discover_services(root: Path) -> list[Path]:
    return sorted(p.parent for p in root.glob("*/deployment.yaml"))
