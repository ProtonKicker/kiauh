# ======================================================================= #
#  Copyright (C) 2020 - 2026 Dominik Willner <dev.dw-0@proton.me>         #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from core import backends
from core.backends import LocalFilesystemBackend, SubprocessRunner
from tests.helpers.fake_backends import FakeCommandRunner, FakeFilesystemBackend
from utils import fs_utils, sys_utils


class TestSubprocessRunner:
    def test_run_executes_command(self) -> None:
        runner = SubprocessRunner()
        result = runner.run([sys.executable, "-c", ""])
        assert result.returncode == 0

    def test_check_output_returns_stdout(self) -> None:
        runner = SubprocessRunner()
        output = runner.check_output(
            [sys.executable, "-c", "print('hello')"], text=True
        )
        assert "hello" in output


class TestCommandRunnerInjection:
    def test_sys_utils_uses_injected_runner(self, monkeypatch) -> None:
        fake = FakeCommandRunner({
            ("some", "cmd"): subprocess.CompletedProcess(["some", "cmd"], 0, "", "")
        })
        monkeypatch.setattr(backends, "command_runner", fake)

        sys_utils.run(["some", "cmd"], check=True)

        assert fake.calls[0][0] == ["some", "cmd"]
        assert fake.calls[0][1].get("check") is True

    def test_cmd_sysctl_service_records_command(self, monkeypatch) -> None:
        expected_cmd = ["sudo", "systemctl", "start", "klipper.service"]
        fake = FakeCommandRunner({
            tuple(expected_cmd): subprocess.CompletedProcess(expected_cmd, 0, "", "")
        })
        monkeypatch.setattr(backends, "command_runner", fake)

        sys_utils.cmd_sysctl_service("klipper.service", "start")

        assert fake.calls[0][0] == expected_cmd

    @pytest.mark.parametrize("module", [sys_utils, fs_utils])
    def test_single_shared_command_runner_registry(self, monkeypatch, module) -> None:
        # there is only ONE ``command_runner`` global to patch.
        # Patching ``core.backends.command_runner`` must affect every wrapper
        # (sys_utils.run, fs_utils.run, enum helpers) — no per-module duplicates.
        fake = FakeCommandRunner({
            ("shared", "cmd"): subprocess.CompletedProcess(["shared", "cmd"], 0, "", "")
        })
        monkeypatch.setattr(backends, "command_runner", fake)

        module.run(["shared", "cmd"], check=True)

        assert fake.calls[0][0] == ["shared", "cmd"]


class TestLocalFilesystemBackend:
    def test_write_and_read_text(self, tmp_path: Path) -> None:
        fs = LocalFilesystemBackend()
        target = tmp_path / "test.txt"
        fs.write_text(target, "hello")
        assert fs.read_text(target) == "hello"

    def test_mkdir_and_exists(self, tmp_path: Path) -> None:
        fs = LocalFilesystemBackend()
        target = tmp_path / "new_dir"
        assert not fs.exists(target)
        fs.mkdir(target)
        assert fs.exists(target)
        assert fs.is_dir(target)


class TestFilesystemBackendInjection:
    def test_create_folders_uses_injected_fs(self, monkeypatch) -> None:
        fake = FakeFilesystemBackend()
        monkeypatch.setattr(backends, "filesystem", fake)

        fs_utils.create_folders([Path("/tmp/a"), Path("/tmp/b")])

        assert fake.exists(Path("/tmp/a"))
        assert fake.exists(Path("/tmp/b"))

    def test_run_remove_routines_uses_injected_fs(self, monkeypatch) -> None:
        fake = FakeFilesystemBackend()
        fake.add_file(Path("/tmp/file.txt"), "x")
        monkeypatch.setattr(backends, "filesystem", fake)

        assert fs_utils.run_remove_routines(Path("/tmp/file.txt")) is True
        assert not fake.exists(Path("/tmp/file.txt"))

    def test_run_remove_routines_skips_missing_file(self, monkeypatch) -> None:
        fake = FakeFilesystemBackend()
        monkeypatch.setattr(backends, "filesystem", fake)

        assert fs_utils.run_remove_routines(Path("/tmp/missing")) is False
