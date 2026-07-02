import pytest
from pathlib import Path

from backuper import Backuper


class TestBackuper:
    def test_backuper_init(self, src, dest):
        """
        Test Backuper initialization with correct arguments.

        Should not raise an exception.
        """
        backuper = Backuper(src, dest, 2)

        assert hasattr(backuper, "src")
        assert hasattr(backuper, "dest")
        assert hasattr(backuper, "_max_concurrent")
        assert backuper.src == src
        assert backuper.dest == dest
        assert backuper._max_concurrent == 2

    def test_backuper_init_max_concurrent_is_0(self, src, dest):
        """
        Test Backuper initialization with max_concurrent = 0.

        Should raise an exception.
        """
        with pytest.raises(ValueError):
            Backuper(src, dest, 0)

    def test_backuper_init_max_concurrent_lt_0(self, src, dest):
        """
        Test Backuper initialization with max_concurrent < 0.

        Should raise an exception.
        """
        with pytest.raises(ValueError):
            Backuper(src, dest, -1)

    def test_backuper_init_src_does_not_exist(self, tmp_path, dest):
        """
        Test Backuper initialization with non-existent source.

        Should raise an exception.
        """
        with pytest.raises(FileNotFoundError):
            Backuper(tmp_path / "src", dest)

    def test_backuper_init_src_not_a_dir(self, tmp_path, dest):
        """
        Test Backuper initialization with source, which is not a directory.

        Should raise an exception.
        """
        src = tmp_path / "file.txt"
        src.touch(exist_ok=True)
        with pytest.raises(NotADirectoryError):
            Backuper(src, dest)

    def test_backuper_init_dest_does_not_exist(self, tmp_path, src):
        """
        Test Backuper initialization with non-existent destination.

        Should create destination.
        """
        dest: Path = tmp_path / "dest"
        assert not dest.exists()

        Backuper(src, dest)

        assert dest.exists()

    def test_backuper_init_dest_not_a_dir(self, tmp_path, src):
        """
        Test Backuper initialization with destination, which is not a directory.

        Should raise an exception.
        """
        dest = tmp_path / "file.txt"
        dest.touch(exist_ok=True)
        with pytest.raises(FileExistsError):
            Backuper(src, dest)

    def test_backuper_access_last_copied_before_calling_backup(self, backuper):
        """
        Test Backuper access `last_copied` attribute before running `backup`.

        Should raise an exception.
        """
        with pytest.raises(RuntimeError):
            backuper.last_copied

    async def test_backup_clears_last_copied_before_every_run(self, src, dest, backuper):
        """
        Test Backuper clears `last_copied` attribute before every run of `backup`.
        """
        src_file: Path = src / "file.txt"
        src_file.touch(exist_ok=True)
        dest_path = dest / src_file.name

        await backuper.backup()

        assert len(backuper.last_copied) == 1
        assert str(dest_path) == str(backuper.last_copied[0][0])

        await backuper.backup()

        # last_copied should be empty because file in dest is already up to date, so it is not copied again
        assert not backuper.last_copied

    async def test_backup_multiple_files(self, src, dest, backuper):
        """
        Test Backuper's `backup` method can handle backing up multiple files at once.
        """
        src_only_file: Path = src / "src_only.txt"  # should be copied in dest
        content = "content"
        src_only_file.write_text(content)

        src_newer_file: Path = src / "src_newer.txt"  # should be copied to dest
        dest_older_file: Path = (
            dest / src_newer_file.name
        )  # should be overwritten by src_newer_file
        new_content = "new content"
        dest_older_file.write_text("old content")
        src_newer_file.write_text(new_content)

        await backuper.backup()

        copied_file: Path = dest / src_only_file.name
        assert copied_file.exists()
        assert copied_file.read_text() == content

        assert dest_older_file.read_text() == new_content

        last_copied_paths = {str(p[0]) for p in backuper.last_copied}
        assert len(last_copied_paths) == 2
        assert str(copied_file) in last_copied_paths
        assert str(dest_older_file) in last_copied_paths

    async def test_backup_src_newer(self, src, dest, backuper):
        """
        Test Backuper's `backup` method can handle situation when file in `src` is newer than the corresponding one in `dest`.

        Should update file in `dest` to be the same as in `src`.
        """
        src_newer_file: Path = src / "src_newer.txt"  # should be copied to dest
        dest_older_file: Path = (
            dest / src_newer_file.name
        )  # should be overwritten by src_newer_file

        dest_older_file.write_text("old content")
        new_content = "new content"
        src_newer_file.write_text(new_content)
        newer_mtime = src_newer_file.stat().st_mtime_ns

        await backuper.backup()

        # check that both files have the same content and that it's the newer one's content
        assert src_newer_file.read_text() == new_content
        assert dest_older_file.read_text() == new_content

        # check that both files have the same mtime and that src file's mtime was not changed
        assert src_newer_file.stat().st_mtime_ns == newer_mtime
        assert dest_older_file.stat().st_mtime_ns == newer_mtime

        last_copied_paths = {str(p[0]) for p in backuper.last_copied}
        assert len(last_copied_paths) == 1
        assert str(dest_older_file) in last_copied_paths

    async def test_backup_src_only(self, src, dest, backuper):
        """
        Test Backuper's `backup` method can handle situation when file exists only in `src` but not in `dest`.

        Should copy file from `src` into `dest`.
        """
        src_only_file: Path = src / "src_only.txt"  # should be copied in dest
        content = "content"
        src_only_file.write_text(content)
        src_mtime = src_only_file.stat().st_mtime_ns

        await backuper.backup()

        dest_file_path: Path = dest / src_only_file.name

        # check that new file was created in dest with the same name as file from src
        assert dest_file_path.exists()

        # check that both files have the same content as initial src file
        assert dest_file_path.read_text() == content
        assert src_only_file.read_text() == content

        # check that mtime didn't change for src file and was copied to dest file as well
        assert src_only_file.stat().st_mtime_ns == src_mtime
        assert dest_file_path.stat().st_mtime_ns == src_mtime

        last_copied_paths = {str(p[0]) for p in backuper.last_copied}
        assert len(last_copied_paths) == 1
        assert str(dest_file_path) in last_copied_paths

    async def test_backup_src_older(self, src, dest, backuper):
        """
        Test Backuper's `backup` method can handle situation when file in `src` is older than the corresponding one in `dest`.

        Should skip this file.
        """
        src_older_file: Path = src / "src_older.txt"  # should not be copied to dest
        dest_newer_file: Path = dest / src_older_file.name  # should remain intact
        old_content = "old content"
        new_content = "new content"
        src_older_file.write_text(old_content)
        dest_newer_file.write_text(new_content)
        older_mtime = src_older_file.stat().st_mtime_ns
        newer_mtime = dest_newer_file.stat().st_mtime_ns

        await backuper.backup()

        # check that both files exist
        assert src_older_file.exists()
        assert dest_newer_file.exists()

        # check that mtimes remain intact
        assert src_older_file.stat().st_mtime_ns == older_mtime
        assert dest_newer_file.stat().st_mtime_ns == newer_mtime

        # check that content remain intact
        assert src_older_file.read_text() == old_content
        assert dest_newer_file.read_text() == new_content

        assert not backuper.last_copied

    async def test_backup_dest_only(self, src, dest, backuper):
        """
        Test Backuper's `backup` method can handle situation when file exists only in `dest` but not in `src`.

        Should not touch file in `dest`.
        """
        dest_only_file: Path = dest / "dest_only.txt"  # should remain intact
        content = "content"
        dest_only_file.write_text(content)
        mtime = dest_only_file.stat().st_mtime_ns

        await backuper.backup()

        assert not (src / dest_only_file.name).exists()
        assert dest_only_file.read_text() == content
        assert dest_only_file.stat().st_mtime_ns == mtime
        assert not backuper.last_copied
