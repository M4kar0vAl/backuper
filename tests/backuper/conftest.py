import pytest

from backuper import Backuper


@pytest.fixture
def backuper(src, dest) -> Backuper:
    return Backuper(src, dest)
