import asyncio
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)

console = Console()


class Backuper:
    def __init__(self, src: Path, dest: Path):
        self.src = src
        self.dest = dest

        if not self.src.exists():
            raise FileNotFoundError(f"Source {self.src} does not exist")

        self._ensure_path_is_a_dir(self.src)

        self.dest.mkdir(parents=True, exist_ok=True)
        self._ensure_path_is_a_dir(self.dest)
        self._last_copied = None

    async def backup(self):
        src_files = self._get_files_in_dir(self.src)
        last_copied: list[tuple[Path, float]] = []

        async with asyncio.TaskGroup() as tg:
            for file in src_files:
                target_path = self.dest / file.name
                file_mtime_seconds = self._get_mtime_seconds(file)
                copied_file_info = (target_path, file_mtime_seconds)

                if not target_path.exists():
                    tg.create_task(asyncio.to_thread(self._copy_file_to_dest, file))
                    last_copied.append(copied_file_info)
                    continue

                src_mtime = self._get_mtime(file)
                dest_mtime = self._get_mtime(target_path)

                if src_mtime > dest_mtime:
                    tg.create_task(asyncio.to_thread(self._copy_file_to_dest, file))
                    last_copied.append(copied_file_info)
                elif src_mtime < dest_mtime:
                    log.warning(f"Skipped {file.name}. Destination is newer.")
                    continue
                else:
                    log.info(f"Skipped {file.name}. Already up to date")

        self._last_copied = last_copied

    @property
    def last_copied(self) -> list[tuple[Path, float]]:
        if self._last_copied is None:
            raise RuntimeError(
                "You should call 'backup' before accessing 'last_copied'"
            )

        return self._last_copied

    def _copy_file_to_dest(self, file: Path) -> None:
        try:
            shutil.copy2(file, self.dest)
        except Exception as e:
            log.error(f"Failed to copy file {file.name}: {e}")
        else:
            log.info(f"Copied {file.name} to {self.dest}")

    def _get_files_in_dir(self, dir_path: Path) -> list[Path]:
        self._ensure_path_is_a_dir(dir_path)
        return [p for p in dir_path.iterdir() if p.is_file()]

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
