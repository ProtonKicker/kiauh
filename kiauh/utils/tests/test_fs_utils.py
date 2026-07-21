# ======================================================================= #
#  Copyright (C) 2020 - 2026 Dominik Willner <dev.dw-0@proton.me>         #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #

from __future__ import annotations

from pathlib import Path
from subprocess import CalledProcessError
from typing import Any, List
from zipfile import ZipFile

import pytest
from utils.fs_utils import (
    check_file_exist,
    create_folders,
    create_symlink,
    get_data_dir,
    remove_file,
    remove_with_sudo,
    run_remove_routines,
    unzip,
)


class TestCheckFileExist:
    def test_returns_true_for_existing_file(self, tmp_path: Path) -> None:
        file = tmp_path / "file.txt"
        file.write_text("x")
        assert check_file_exist(file) is True

    def test_returns_false_for_missing_file(self, tmp_path: Path) -> None:
        assert check_file_exist(tmp_path / "missing") is False

    def test_returns_false_for_broken_symlink(self, tmp_path: Path) -> None:
        link = tmp_path / "link"
        link.symlink_to(tmp_path / "target")
        assert check_file_exist(link) is False

    def test_with_sudo_uses_subprocess(self, monkeypatch) -> None:
        calls: List[List[str]] = []

        def fake_check_output(cmd: List[str], **kwargs: Any) -> bytes:
            calls.append(cmd)
            return b""

        monkeypatch.setattr("utils.fs_utils.check_output", fake_check_output)
        path = Path("/some/path")
        assert check_file_exist(path, sudo=True) is True
        assert calls[0] == ["sudo", "find", "-L", "/some/path", "-maxdepth", "0"]

    def test_with_sudo_returns_false_on_error(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "utils.fs_utils.check_output",
            lambda *a, **k: (_ for _ in ()).throw(CalledProcessError(1, "find")),
        )
        assert check_file_exist(Path("/some/path"), sudo=True) is False


class TestCreateSymlink:
    def test_calls_ln_with_correct_args(self, monkeypatch) -> None:
        runs: List[List[str]] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return None

        monkeypatch.setattr("utils.fs_utils.run", fake_run)
        create_symlink(Path("/src"), Path("/dst"))
        assert runs == [["ln", "-sf", "/src", "/dst"]]

    def test_uses_sudo(self, monkeypatch) -> None:
        runs: List[List[str]] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return None

        monkeypatch.setattr("utils.fs_utils.run", fake_run)
        create_symlink(Path("/src"), Path("/dst"), sudo=True)
        assert runs == [["sudo", "ln", "-sf", "/src", "/dst"]]

    def test_raises_on_failure(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "utils.fs_utils.run",
            lambda *a, **k: (_ for _ in ()).throw(CalledProcessError(1, "ln")),
        )
        with pytest.raises(CalledProcessError):
            create_symlink(Path("/src"), Path("/dst"))


class TestRemoveWithSudo:
    def test_removes_existing_files(self, monkeypatch) -> None:
        calls: List[tuple] = []

        def fake_call(cmd: List[str], **kwargs: Any) -> int:
            calls.append(("call", cmd))
            return 0

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            calls.append(("run", cmd))
            return None

        monkeypatch.setattr("utils.fs_utils.call", fake_call)
        monkeypatch.setattr("utils.fs_utils.run", fake_run)

        result = remove_with_sudo(Path("/some/file"))

        assert result is True
        assert ("call", ["sudo", "find", "/some/file"]) in calls
        assert ("run", ["sudo", "rm", "-rf", "/some/file"]) in calls

    def test_skips_missing_files(self, monkeypatch) -> None:
        def fake_call(cmd: List[str], **kwargs: Any) -> int:
            return 1

        monkeypatch.setattr("utils.fs_utils.call", fake_call)
        monkeypatch.setattr(
            "utils.fs_utils.run",
            lambda *a, **k: pytest.fail("should not run rm for missing file"),
        )

        assert remove_with_sudo(Path("/some/file")) is False

    def test_accepts_list(self, monkeypatch) -> None:
        runs: List[List[str]] = []

        def fake_call(cmd: List[str], **kwargs: Any) -> int:
            return 0

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return None

        monkeypatch.setattr("utils.fs_utils.call", fake_call)
        monkeypatch.setattr("utils.fs_utils.run", fake_run)

        remove_with_sudo([Path("/a"), Path("/b")])

        assert runs == [
            ["sudo", "rm", "-rf", "/a"],
            ["sudo", "rm", "-rf", "/b"],
        ]


class TestRemoveFile:
    def test_calls_shell_rm(self, monkeypatch) -> None:
        runs: List[Any] = []

        def fake_run(cmd: str, **kwargs: Any) -> Any:
            runs.append((cmd, kwargs.get("shell")))
            return None

        monkeypatch.setattr("utils.fs_utils.run", fake_run)

        with pytest.warns(DeprecationWarning):
            remove_file(Path("/some/file"), sudo=True)

        assert runs == [(f"sudo rm -f {Path('/some/file')}", True)]


class TestRunRemoveRoutines:
    def test_returns_false_for_missing(self, tmp_path: Path) -> None:
        assert run_remove_routines(tmp_path / "missing") is False

    def test_removes_file(self, tmp_path: Path) -> None:
        file = tmp_path / "file.txt"
        file.write_text("x")
        assert run_remove_routines(file) is True
        assert not file.exists()

    def test_removes_directory(self, tmp_path: Path) -> None:
        directory = tmp_path / "dir"
        directory.mkdir()
        (directory / "child").write_text("x")
        assert run_remove_routines(directory) is True
        assert not directory.exists()

    def test_removes_symlink(self, tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.write_text("x")
        link = tmp_path / "link"
        link.symlink_to(target)
        assert run_remove_routines(link) is True
        assert not link.exists()
        assert target.exists()


class TestUnzip:
    def test_extracts_contents(self, tmp_path: Path) -> None:
        archive = tmp_path / "archive.zip"
        target = tmp_path / "out"
        target.mkdir()

        with ZipFile(archive, "w") as zf:
            zf.writestr("hello.txt", "world")

        unzip(archive, target)

        assert (target / "hello.txt").read_text() == "world"


class TestCreateFolders:
    def test_creates_missing_directories(self, tmp_path: Path) -> None:
        dirs = [tmp_path / "a", tmp_path / "b"]
        create_folders(dirs)
        assert all(d.exists() for d in dirs)

    def test_skips_existing(self, tmp_path: Path) -> None:
        existing = tmp_path / "exists"
        existing.mkdir()
        create_folders([existing])
        assert existing.exists()


class TestGetDataDir:
    def test_reads_from_service_file(self, tmp_path: Path, monkeypatch) -> None:
        service = tmp_path / "klipper.service"
        service.write_text(
            "EnvironmentFile=/home/user/printer_data/systemd/klipper.env\n"
        )

        def fake_service_path(instance_type: type, suffix: str) -> Path:
            return service

        monkeypatch.setattr("utils.sys_utils.get_service_file_path", fake_service_path)
        monkeypatch.setattr("utils.fs_utils.Path.home", lambda: tmp_path / "home")

        result = get_data_dir(object, "")
        assert result == Path("/home/user/printer_data")

    def test_falls_back_to_suffixed_data_dir(self, tmp_path: Path, monkeypatch) -> None:
        def fake_service_path(instance_type: type, suffix: str) -> Path:
            return tmp_path / "no-such.service"

        monkeypatch.setattr("utils.sys_utils.get_service_file_path", fake_service_path)
        home = tmp_path / "home"
        monkeypatch.setattr("utils.fs_utils.Path.home", lambda: home)

        assert get_data_dir(object, "1") == home / "printer_1_data"

    def test_falls_back_to_default_data_dir(self, tmp_path: Path, monkeypatch) -> None:
        def fake_service_path(instance_type: type, suffix: str) -> Path:
            return tmp_path / "no-such.service"

        monkeypatch.setattr("utils.sys_utils.get_service_file_path", fake_service_path)
        home = tmp_path / "home"
        monkeypatch.setattr("utils.fs_utils.Path.home", lambda: home)

        assert get_data_dir(object, "") == home / "printer_data"
