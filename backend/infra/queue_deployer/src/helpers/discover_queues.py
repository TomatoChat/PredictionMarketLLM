from pathlib import Path


def discover_queues(root: Path) -> list[Path]:
    return sorted(root.glob("*.yaml"))
