import asyncio
import logging
import shutil
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table


log_file = Path("logs/backuper.log")
log_file.parent.mkdir(parents=True, exist_ok=True)

rotating = RotatingFileHandler(log_file, maxBytes=1 * 1024 * 1024, backupCount=2)
rotating.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

logging.basicConfig(level=logging.INFO, handlers=[rotating])

log = logging.getLogger(__name__)

console = Console()


class Backuper:
    def __init__(self, src: Path, dest: Path, max_concurrent: int = 10):
        self.src = src
        self.dest = dest
        self._max_concurrent = max_concurrent

        if self._max_concurrent <= 0:
            raise ValueError("max_concurrent must be a positive integer")

        if not self.src.exists():
            raise FileNotFoundError(f"Source {self.src} does not exist")

        self._ensure_path_is_a_dir(self.src)

        self.dest.mkdir(parents=True, exist_ok=True)
        self._ensure_path_is_a_dir(self.dest)
        self._last_copied: list[tuple[Path, float]] | None = None
        self._semaphore = asyncio.BoundedSemaphore(self._max_concurrent)

    async def backup(self):
        self._last_copied = []  # clear previous records
        src_files = self._get_files_in_dir(self.src)

        async with asyncio.TaskGroup() as tg:
            for file in src_files:
                target_path = self.dest / file.name

                if not target_path.exists():
                    tg.create_task(self.backup_file(file))
                    continue

                src_mtime = self._get_mtime(file)
                dest_mtime = self._get_mtime(target_path)

                if src_mtime > dest_mtime:
                    tg.create_task(self.backup_file(file))
                elif src_mtime < dest_mtime:
                    log.warning("Skipped %s. Destination is newer.", file.name)
                    continue
                else:
                    log.info("Skipped %s. Already up to date", file.name)

    async def backup_file(
        self,
        file: Path,
    ) -> Path | None:
        async with self._semaphore:
            dest_path = await self._copy_file_to_dest(file)

        if dest_path is not None:
            self._last_copied.append(self._get_record_for_copied_file(dest_path))

        return dest_path

    @property
    def last_copied(self) -> list[tuple[Path, float]]:
        if self._last_copied is None:
            raise RuntimeError(
                "You should call 'backup' before accessing 'last_copied'"
            )

        return self._last_copied

    async def _copy_file_to_dest(self, file: Path) -> Path | None:
        try:
            dest_path = Path(await asyncio.to_thread(shutil.copy2, file, self.dest))
        except Exception as e:
            log.error("Failed to copy file %s: %s", file.name, e)
            return None
        else:
            log.info("Copied %s to %s", file.name, self.dest)

        return dest_path

    def _get_files_in_dir(self, dir_path: Path) -> list[Path]:
        self._ensure_path_is_a_dir(dir_path)
        return [p for p in dir_path.iterdir() if p.is_file()]

    def _get_record_for_copied_file(self, copied_file: Path) -> tuple[Path, float]:
        return copied_file, self._get_mtime_seconds(copied_file)

    @classmethod
    def _get_mtime_seconds(cls, path: Path) -> float:
        return path.stat().st_mtime

    @classmethod
    def _get_mtime(cls, path: Path) -> int:
        return path.stat().st_mtime_ns

    @classmethod
    def _ensure_path_is_a_dir(cls, path: Path) -> None:
        if not path.is_dir():
            raise NotADirectoryError(path)


def backup(
    src: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
            help="Source directory",
        ),
    ],
    dest: Annotated[
        Path,
        typer.Argument(
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
            help="Destination directory",
        ),
    ],
    show_copied: Annotated[
        bool,
        typer.Option(
            "--show-copied",
            "-s",
            help="Whether to print copied files after performing backup",
        ),
    ] = False,
):
    backuper = Backuper(src, dest)
    asyncio.run(backuper.backup())

    if show_copied:
        table = Table(
            title="Скопированные файлы:",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Имя файла", style="dim", width=25)
        table.add_column("Дата изменения", justify="right", style="green")

        for file, mtime in backuper.last_copied:
            dt = datetime.fromtimestamp(mtime)
            date_str = dt.strftime("%d.%m.%Y %H:%M")
            table.add_row(file.name, date_str)

        console.print(table)


if __name__ == "__main__":
    typer.run(backup)
