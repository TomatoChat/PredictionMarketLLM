from pathlib import Path


def discover_queues(root: Path) -> list[Path]:
    """Return every `*.yaml` file directly under `root`. Each file is one queue."""
    return sorted(root.glob("*.yaml"))
