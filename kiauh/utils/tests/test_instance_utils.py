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
from typing import List

import pytest
from utils.instance_utils import (
    get_instance_suffix,
    get_instances,
    stop_klipper_instances_interactively,
)


class Klipper:
    def __init__(self, suffix: str):
        self.suffix = suffix

    def __eq__(self, other):
        return isinstance(other, Klipper) and self.suffix == other.suffix

    def __repr__(self):
        return f"Klipper({self.suffix!r})"


class TestGetInstances:
    def test_returns_empty_when_no_services(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr("utils.instance_utils.SYSTEMD", tmp_path)
        assert get_instances(Klipper) == []

    def test_raises_when_not_a_class(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr("utils.instance_utils.SYSTEMD", tmp_path)
        with pytest.raises(ValueError):
            get_instances("not-a-class")  # type: ignore[arg-type]

    def test_finds_and_sorts_instances(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr("utils.instance_utils.SYSTEMD", tmp_path)

        (tmp_path / "klipper.service").write_text("")
        (tmp_path / "klipper-1.service").write_text("")
        (tmp_path / "klipper-10.service").write_text("")
        (tmp_path / "klipper-a.service").write_text("")

        instances = get_instances(Klipper)
        assert [i.suffix for i in instances] == ["", "1", "10", "a"]

    def test_excludes_blacklisted_suffixes(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr("utils.instance_utils.SYSTEMD", tmp_path)

        (tmp_path / "klipper.service").write_text("")
        (tmp_path / "klipper-mcu.service").write_text("")

        instances = get_instances(Klipper)
        assert [i.suffix for i in instances] == [""]


class TestGetInstanceSuffix:
    @pytest.mark.parametrize(
        "name,service,expected",
        [
            ("klipper", "klipper.service", ""),
            ("klipper", "klipper-1.service", "1"),
            ("klipper", "klipper-10.service", "10"),
            ("moonraker", "moonraker-foo.service", "foo"),
        ],
    )
    def test_suffix(self, name: str, service: str, expected: str) -> None:
        assert get_instance_suffix(name, Path(service)) == expected


class TestStopKlipperInstancesInteractively:
    def test_empty_returns_true(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "utils.instance_utils.get_confirm",
            lambda *a, **k: pytest.fail("no prompt when no instances"),
        )
        assert stop_klipper_instances_interactively([]) is True

    def test_stops_on_confirm(self, monkeypatch) -> None:
        stopped: List[Klipper] = []
        instance = Klipper("")

        monkeypatch.setattr("utils.instance_utils.get_confirm", lambda *a, **k: True)
        monkeypatch.setattr(
            "utils.instance_utils.InstanceManager.stop_all",
            lambda instances: stopped.extend(instances),
        )

        assert stop_klipper_instances_interactively([instance], "update") is True
        assert [i.suffix for i in stopped] == [""]

    def test_aborts_on_decline(self, monkeypatch) -> None:
        monkeypatch.setattr("utils.instance_utils.get_confirm", lambda *a, **k: False)
        monkeypatch.setattr(
            "utils.instance_utils.InstanceManager.stop_all",
            lambda *a, **k: pytest.fail("should not stop when declined"),
        )

        assert stop_klipper_instances_interactively([Klipper("")]) is False
