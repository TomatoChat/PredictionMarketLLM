from pathlib import Path


def discover_crons(root: Path) -> list[Path]:
    """Return every `*.yaml` file directly under `root`. Each file is one cron."""
    return sorted(root.glob("*.yaml"))
