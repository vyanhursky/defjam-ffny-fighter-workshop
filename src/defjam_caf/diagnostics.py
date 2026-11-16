"""Best-effort private diagnostics, separate from player-facing errors."""

from pathlib import Path
from datetime import datetime, UTC


def log_detail(workspace, detail):
    try:
        folder = Path(workspace) / "logs"
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / "desktop.log").open("a", encoding="utf-8") as output:
            output.write(f"{datetime.now(UTC).isoformat()} {detail}\n")
    except OSError:
        pass
