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

    async def backup(self):
        src_files = self._get_files_in_dir(self.src)

        async with asyncio.TaskGroup() as tg:
            for file in src_files:
                target_path = self.dest / file.name

                if not target_path.exists():
                    tg.create_task(asyncio.to_thread(self._copy_file_to_dest, file))
                    log.info(f"Copied {file} to {self.dest}")
                    continue

                dest_mtime = self._get_mtime(target_path)
                src_mtime = self._get_mtime(file)

                if src_mtime > dest_mtime:
                    tg.create_task(asyncio.to_thread(self._copy_file_to_dest, file))
                    log.info(f"Copied {file} to {self.dest}")
                elif src_mtime < dest_mtime:
                    log.warning(f"Skipped {file}. Destination is newer.")
                    continue
                else:
                    log.info(f"Skipped {file}. Already up to date")

    def get_dest_files_with_mtime(self) -> list[tuple[Path, float]]:
        dest_files = self._get_files_in_dir(self.dest)
        return [(file, file.stat().st_mtime) for file in dest_files]

    def _copy_file_to_dest(self, file: Path) -> None:
        shutil.copy2(file, self.dest)

    def _get_files_in_dir(self, dir_path: Path) -> list[Path]:
        self._ensure_path_is_a_dir(dir_path)
        return [p for p in dir_path.iterdir() if p.is_file()]

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
    print_dest_files: Annotated[
        bool,
        typer.Option(
            "--print-dest-files",
            "-p",
            help="Whether to print files in destination after performing backup",
        ),
    ] = False,
):
    backuper = Backuper(src, dest)
    asyncio.run(backuper.backup())

    if print_dest_files:
        table = Table(
            title=f"Файлы в {backuper.dest}:",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Имя файла", style="dim", width=25)
        table.add_column("Дата изменения", justify="right", style="green")

        for file, mtime in backuper.get_dest_files_with_mtime():
            dt = datetime.fromtimestamp(mtime)
            date_str = dt.strftime("%d.%m.%Y %H:%M")
            table.add_row(file.name, date_str)

        console.print(table)


if __name__ == "__main__":
    typer.run(backup)
