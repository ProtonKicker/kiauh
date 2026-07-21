# ======================================================================= #
#  Copyright (C) 2020 - 2026 Dominik Willner <dev.dw-0@proton.me>         #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Set

import pytest
from core.constants import GLOBAL_DEPS
from utils.common import (
    check_install_dependencies,
    convert_camelcase_to_kebabcase,
    get_current_date,
    get_install_status,
    get_kiauh_version,
    moonraker_exists,
    trunc_string,
)


class TestGetKiauhVersion:
    def test_uses_project_root(self, monkeypatch) -> None:
        expected_root = Path(__file__).parent.parent.parent.parent
        captured: List[Path] = []

        def fake_get_local_tags(path: Path, _filter: str | None = None) -> List[str]:
            captured.append(path)
            return ["v6.3.0", "v6.3.1"]

        monkeypatch.setattr("utils.common.get_local_tags", fake_get_local_tags)
        result = get_kiauh_version()

        assert captured == [expected_root]
        assert result == "v6.3.1"

    def test_fallback_when_no_tags(self, monkeypatch) -> None:
        monkeypatch.setattr("utils.common.get_local_tags", lambda *_a, **_k: [])
        assert get_kiauh_version() == "v?.?.?"


class TestConvertCamelcaseToKebabcase:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("Klipper", "klipper"),
            ("Moonraker", "moonraker"),
            ("MoonrakerObico", "moonraker-obico"),
            ("HTTPResponse", "h-t-t-p-response"),
            ("already", "already"),
        ],
    )
    def test_converts(self, name: str, expected: str) -> None:
        assert convert_camelcase_to_kebabcase(name) == expected


class TestGetCurrentDate:
    def test_returns_formatted_values(self) -> None:
        result = get_current_date()
        now = datetime.today()

        assert set(result.keys()) == {"date", "time"}
        assert result["date"] == now.strftime("%Y%m%d")
        assert result["time"] == now.strftime("%H%M%S")


class TestCheckInstallDependencies:
    def test_with_global_and_custom(self, monkeypatch) -> None:
        checked: Set[str] = set()
        updated: List[bool] = []
        installed_pkgs: List[List[str]] = []

        def fake_check_package_install(deps: Set[str]) -> List[str]:
            checked.update(deps)
            return ["extra-pkg"]

        monkeypatch.setattr(
            "utils.common.check_package_install", fake_check_package_install
        )
        monkeypatch.setattr(
            "utils.common.update_system_package_lists",
            lambda silent: updated.append(silent),
        )
        monkeypatch.setattr(
            "utils.common.install_system_packages",
            lambda pkgs: installed_pkgs.append(pkgs),
        )

        check_install_dependencies({"custom-pkg"}, include_global=True)

        assert "custom-pkg" in checked
        assert all(dep in checked for dep in GLOBAL_DEPS)
        assert updated == [False]
        assert installed_pkgs == [["extra-pkg"]]

    def test_no_requirements(self, monkeypatch) -> None:
        monkeypatch.setattr("utils.common.check_package_install", lambda *_a, **_k: [])
        monkeypatch.setattr(
            "utils.common.update_system_package_lists",
            lambda *a, **k: pytest.fail("should not update when nothing to install"),
        )
        monkeypatch.setattr(
            "utils.common.install_system_packages",
            lambda *a, **k: pytest.fail("should not install when nothing to install"),
        )

        check_install_dependencies({"pkg"})

    def test_propagates_runtime_error_from_package_list_update(
        self, monkeypatch
    ) -> None:
        # Installing dependencies must propagate apt update failures rather than
        # swallow them, because continuing with broken package metadata is unsafe.
        monkeypatch.setattr(
            "utils.common.check_package_install",
            lambda *_a, **_k: ["missing-pkg"],
        )

        def _raise(*_a, **_k):
            raise RuntimeError("apt-get update failed")

        monkeypatch.setattr("utils.common.update_system_package_lists", _raise)
        monkeypatch.setattr(
            "utils.common.install_system_packages",
            lambda *_a, **_k: pytest.fail("should not install on broken apt update"),
        )

        with pytest.raises(RuntimeError):
            check_install_dependencies({"pkg"})


class _FakeInstanceType:
    def __init__(self, suffix: str):
        self.suffix = suffix

    def __eq__(self, other):
        return isinstance(other, _FakeInstanceType) and self.suffix == other.suffix


class TestGetInstallStatus:
    def test_not_installed(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        env = tmp_path / "env"

        monkeypatch.setattr("utils.common.get_current_branch", lambda *_a, **_k: None)
        monkeypatch.setattr("utils.common.get_repo_name", lambda *_a, **_k: (None, None))
        monkeypatch.setattr("utils.common.get_repo_url", lambda *_a, **_k: None)
        monkeypatch.setattr("utils.common.get_local_commit", lambda *_a, **_k: None)
        monkeypatch.setattr("utils.common.get_remote_commit", lambda *_a, **_k: None)
        monkeypatch.setattr("utils.instance_utils.get_instances", lambda *_a, **_k: [])

        status = get_install_status(repo, env, _FakeInstanceType)

        assert status.status == 0
        assert status.instances == 0

    def test_fully_installed(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        env = tmp_path / "env"
        repo.mkdir()
        env.mkdir()
        (repo / ".git").mkdir()
        extra_file = tmp_path / "extra"
        extra_file.write_text("x")

        monkeypatch.setattr(
            "utils.instance_utils.get_instances", lambda *_a, **_k: [_FakeInstanceType("")]
        )
        monkeypatch.setattr("utils.common.get_current_branch", lambda *_a, **_k: "main")
        monkeypatch.setattr(
            "utils.common.get_repo_name", lambda *_a, **_k: ("dw-0", "kiauh")
        )
        monkeypatch.setattr(
            "utils.common.get_repo_url", lambda *_a, **_k: "https://github.com/dw-0/kiauh"
        )
        monkeypatch.setattr("utils.common.get_local_commit", lambda *_a, **_k: "abc")
        monkeypatch.setattr("utils.common.get_remote_commit", lambda *_a, **_k: "def")

        status = get_install_status(repo, env, _FakeInstanceType, files=[extra_file])

        assert status.status == 2
        assert status.instances == 1
        assert status.owner == "dw-0"
        assert status.repo == "kiauh"
        assert status.branch == "main"
        assert status.local == "abc"
        assert status.remote == "def"

    def test_incomplete(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        env = tmp_path / "env"
        repo.mkdir()

        monkeypatch.setattr(
            "utils.instance_utils.get_instances", lambda *_a, **_k: [_FakeInstanceType("")]
        )
        monkeypatch.setattr("utils.common.get_current_branch", lambda *_a, **_k: "main")
        monkeypatch.setattr("utils.common.get_repo_name", lambda *_a, **_k: (None, None))
        monkeypatch.setattr("utils.common.get_repo_url", lambda *_a, **_k: None)
        monkeypatch.setattr("utils.common.get_local_commit", lambda *_a, **_k: None)
        monkeypatch.setattr("utils.common.get_remote_commit", lambda *_a, **_k: None)

        status = get_install_status(repo, env, _FakeInstanceType)

        assert status.status == 1


class TestMoonrakerExists:
    def test_returns_instances(self, monkeypatch) -> None:
        fake = object()
        monkeypatch.setattr("utils.common.get_instances", lambda *_a, **_k: [fake])
        assert moonraker_exists() == [fake]

    def test_warns_when_none(self, monkeypatch) -> None:
        monkeypatch.setattr("utils.common.get_instances", lambda *_a, **_k: [])
        assert moonraker_exists("SomeInstaller") == []


class TestTruncString:
    @pytest.mark.parametrize(
        "value,length,expected",
        [
            ("short", 10, "short"),
            ("exactly seven", 20, "exactly seven"),
            ("much longer string", 10, "much lo..."),
            ("abcdef", 5, "ab..."),
        ],
    )
    def test_truncates(self, value: str, length: int, expected: str) -> None:
        assert trunc_string(value, length) == expected
