from __future__ import annotations

from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn


class SyncProgress:
    """Rich progress display for skill sync operations."""

    def __init__(self) -> None:
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=32),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            transient=False,
        )
        self._task_id: int | None = None
        self._total = 0

    def __enter__(self) -> SyncProgress:
        self._progress.start()
        return self

    def __exit__(self, *args: object) -> None:
        self._progress.stop()

    def begin(self, total: int, message: str = "Applying changes") -> None:
        self._total = max(total, 1)
        self._task_id = self._progress.add_task(message, total=self._total)

    def _update(self, description: str, advance: int = 0) -> None:
        if self._task_id is None:
            return
        self._progress.update(self._task_id, description=description, advance=advance)

    def removing(self, name: str, index: int, total: int) -> None:
        self._update(f"Removing {name} ({index}/{total})", advance=1)

    def downloading(self, name: str, rel_path: str, file_index: int, file_total: int) -> None:
        self._update(f"Downloading {name} — {rel_path} ({file_index}/{file_total})")

    def installing(self, name: str) -> None:
        self._update(f"Installing {name}", advance=1)

    def linking(self, name: str) -> None:
        self._update(f"Linking {name} for agent discovery")
