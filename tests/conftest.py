import pytest
import shutil
from pathlib import Path
from typing import Generator, Any


@pytest.fixture
def src(tmp_path) -> Generator[Path, Any, None]:
    src_: Path = tmp_path / "src"
    src_.mkdir(parents=True, exist_ok=True)

    yield src_

    shutil.rmtree(src_)


@pytest.fixture
def dest(tmp_path) -> Generator[Path, Any, None]:
    dest_: Path = tmp_path / "dest"
    dest_.mkdir(parents=True, exist_ok=True)

    yield dest_

    shutil.rmtree(dest_)
