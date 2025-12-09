"""Progress tracking for BugHive crawl sessions."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class ProgressTracker:
    """Tracks crawl progress with human-readable files and JSON state snapshots."""

    def __init__(self, session_id: str, output_dir: Path | str = "./progress"):
        self.session_id = session_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.progress_file = self.output_dir / f"{session_id}_progress.txt"
        self.state_file = self.output_dir / f"{session_id}_state.json"

    def update(
        self,
        stage: str,
        pages_done: int,
        pages_total: int,
        bugs_found: int,
        cost: float,
        eta_seconds: int | None = None,
    ) -> None:
        """Write human-readable progress line to file."""
        eta = f" | ETA: {eta_seconds}s" if eta_seconds else ""
        line = (
            f"[{datetime.now().isoformat()}] {stage} | "
            f"Pages: {pages_done}/{pages_total} | "
            f"Bugs: {bugs_found} | Cost: ${cost:.4f}{eta}\n"
        )
        with self.progress_file.open("a") as f:
            f.write(line)

    def save_state(self, state: dict[str, Any]) -> None:
        """Save structured state snapshot to JSON."""
        # Convert non-serializable types
        serializable = self._make_serializable(state)
        with self.state_file.open("w") as f:
            json.dump(serializable, f, indent=2, default=str)

    def load_state(self) -> dict[str, Any] | None:
        """Load state from JSON file if exists."""
        if self.state_file.exists():
            with self.state_file.open() as f:
                return json.load(f)
        return None

    def _make_serializable(self, obj: Any) -> Any:
        """Convert objects to JSON-serializable format."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(v) for v in obj]
        elif isinstance(obj, (datetime,)):
            return obj.isoformat()
        elif hasattr(obj, "__dict__"):
            return str(obj)
        return obj

    def get_progress_summary(self) -> str | None:
        """Read last line of progress file."""
        if self.progress_file.exists():
            with self.progress_file.open() as f:
                lines = f.readlines()
                return lines[-1].strip() if lines else None
        return None
