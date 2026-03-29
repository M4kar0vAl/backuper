import asyncio
import logging
import shutil
from pathlib import Path
from typing import Annotated

import typer


log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)


class Syncer:
    def __init__(self, src: Path, dest: Path):
        self.src = src
        self.dest = dest

        if not self.src.exists():
            raise FileNotFoundError(f"Source {self.src} does not exist")

        self._ensure_path_is_a_dir(self.src)

        self.dest.mkdir(parents=True, exist_ok=True)
        self._ensure_path_is_a_dir(self.dest)

    async def sync(self):
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


def sync(
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
):
    asyncio.run(Syncer(src, dest).sync())


if __name__ == "__main__":
    typer.run(sync)
