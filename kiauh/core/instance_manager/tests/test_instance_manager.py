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
from pathlib import Path
from typing import List

import pytest
from core.instance_manager.instance_manager import InstanceManager
from tests.helpers.fake_backends import FakeCommandRunner


class FakeInstance:
    def __init__(self, name: str, log_dir: Path | None = None) -> None:
        self.service_file_path = Path(f"/etc/systemd/system/{name}.service")
        self.log_file_name = "klipper.log"
        self.base = type("Base", (), {"log_dir": log_dir})()


def _runner_for(*commands: List[str]) -> FakeCommandRunner:
    """Return a strict FakeCommandRunner with success responses for commands."""
    responses = {
        tuple(cmd): subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="", stderr=""
        )
        for cmd in commands
    }
    return FakeCommandRunner(responses)


class TestInstanceManager:
    def test_start_records_command(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cmd = ["sudo", "systemctl", "start", "klipper.service"]
        fake = _runner_for(cmd)
        monkeypatch.setattr("core.backends.command_runner", fake)

        instance = FakeInstance("klipper")
        InstanceManager.start(instance)

        assert fake.calls[0][0] == cmd

    def test_stop_records_command(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cmd = ["sudo", "systemctl", "stop", "klipper.service"]
        fake = _runner_for(cmd)
        monkeypatch.setattr("core.backends.command_runner", fake)

        instance = FakeInstance("klipper")
        InstanceManager.stop(instance)

        assert fake.calls[0][0] == cmd

    def test_restart_records_command(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cmd = ["sudo", "systemctl", "restart", "klipper.service"]
        fake = _runner_for(cmd)
        monkeypatch.setattr("core.backends.command_runner", fake)

        instance = FakeInstance("klipper")
        InstanceManager.restart(instance)

        assert fake.calls[0][0] == cmd

    def test_enable_records_command(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cmd = ["sudo", "systemctl", "enable", "klipper.service"]
        fake = _runner_for(cmd)
        monkeypatch.setattr("core.backends.command_runner", fake)

        instance = FakeInstance("klipper")
        InstanceManager.enable(instance)

        assert fake.calls[0][0] == cmd

    def test_disable_records_command(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cmd = ["sudo", "systemctl", "disable", "klipper.service"]
        fake = _runner_for(cmd)
        monkeypatch.setattr("core.backends.command_runner", fake)

        instance = FakeInstance("klipper")
        InstanceManager.disable(instance)

        assert fake.calls[0][0] == cmd

    def test_start_all_iterates_instances(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        commands = [
            ["sudo", "systemctl", "start", "klipper-1.service"],
            ["sudo", "systemctl", "start", "klipper-2.service"],
        ]
        fake = _runner_for(*commands)
        monkeypatch.setattr("core.backends.command_runner", fake)

        instances = [FakeInstance("klipper-1"), FakeInstance("klipper-2")]
        InstanceManager.start_all(instances)

        recorded = [call[0] for call in fake.calls]
        assert recorded == commands

    def test_stop_all_iterates_instances(self, monkeypatch: pytest.MonkeyPatch) -> None:
        commands = [
            ["sudo", "systemctl", "stop", "klipper-a.service"],
            ["sudo", "systemctl", "stop", "klipper-b.service"],
        ]
        fake = _runner_for(*commands)
        monkeypatch.setattr("core.backends.command_runner", fake)

        instances = [FakeInstance("klipper-a"), FakeInstance("klipper-b")]
        InstanceManager.stop_all(instances)

        recorded = [call[0] for call in fake.calls]
        assert recorded == commands
