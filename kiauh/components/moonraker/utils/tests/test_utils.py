from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest
from components.moonraker.utils import utils as moonraker_utils
from components.moonraker.utils.utils import (
    backup_moonraker_db_dir,
    backup_moonraker_dir,
    create_example_moonraker_conf,
    get_moonraker_status,
    install_moonraker_packages,
    load_sysdeps_json,
    remove_polkit_rules,
)


class FakeMoonraker:
    def __init__(self, suffix: str = "") -> None:
        self.suffix = suffix
        self.data_dir = Path(f"/tmp/moonraker{suffix}_data")
        self.db_dir = self.data_dir.joinpath("database")
        self.cfg_file = self.data_dir.joinpath("moonraker.conf")
        self.base = type(
            "Base",
            (),
            {
                "cfg_dir": self.data_dir,
                "comms_dir": self.data_dir.joinpath("comms"),
            },
        )()


@pytest.fixture
def fake_instance(tmp_path: Path) -> FakeMoonraker:
    instance = FakeMoonraker("")
    instance.data_dir = tmp_path / "moonraker_data"
    instance.cfg_file = instance.data_dir / "moonraker.conf"
    instance.db_dir = instance.data_dir / "database"
    instance.base = type(
        "Base",
        (),
        {
            "cfg_dir": instance.data_dir,
            "comms_dir": instance.data_dir / "comms",
        },
    )()
    return instance


class TestGetMoonrakerStatus:
    def test_delegates_to_get_install_status(self, monkeypatch: pytest.MonkeyPatch) -> None:
        called: List[Any] = []
        monkeypatch.setattr(
            moonraker_utils,
            "get_install_status",
            lambda *args: called.append(args) or type("S", (), {"status": 0})(),
        )

        status = get_moonraker_status()

        assert called
        assert status.status == 0


class TestInstallMoonrakerPackages:
    def test_parses_deps_json_when_present(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        deps_file = tmp_path / "moonraker_deps.json"
        deps_file.write_text(json.dumps({"debian": ["pkg1", "pkg2"]}))
        install_script = tmp_path / "install_moonraker.sh"
        install_script.write_text("# dummy")

        monkeypatch.setattr(moonraker_utils, "MOONRAKER_DEPS_JSON_FILE", deps_file)
        monkeypatch.setattr(moonraker_utils, "MOONRAKER_INSTALL_SCRIPT", install_script)

        deps: List[str] = []
        monkeypatch.setattr(
            moonraker_utils, "check_install_dependencies", lambda p: deps.extend(p)
        )

        class FakeParser:
            def parse_dependencies(self, data):
                return ["pkg1", "pkg2"]

        monkeypatch.setattr(moonraker_utils, "SysDepsParser", FakeParser)

        install_moonraker_packages()

        assert "pkg1" in deps
        assert "pkg2" in deps

    def test_falls_back_to_install_script(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        deps_file = tmp_path / "missing.json"
        install_script = tmp_path / "install_moonraker.sh"
        install_script.write_text("apt-get install pkg3 pkg4\n")

        monkeypatch.setattr(moonraker_utils, "MOONRAKER_DEPS_JSON_FILE", deps_file)
        monkeypatch.setattr(moonraker_utils, "MOONRAKER_INSTALL_SCRIPT", install_script)

        deps: List[str] = []
        monkeypatch.setattr(
            moonraker_utils, "check_install_dependencies", lambda p: deps.extend(p)
        )
        monkeypatch.setattr(
            moonraker_utils,
            "parse_packages_from_file",
            lambda p: ["pkg3", "pkg4"],
        )

        install_moonraker_packages()

        assert "pkg3" in deps

    def test_raises_when_no_deps_found(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        deps_file = tmp_path / "missing.json"
        install_script = tmp_path / "missing.sh"

        monkeypatch.setattr(moonraker_utils, "MOONRAKER_DEPS_JSON_FILE", deps_file)
        monkeypatch.setattr(moonraker_utils, "MOONRAKER_INSTALL_SCRIPT", install_script)

        with pytest.raises(ValueError):
            install_moonraker_packages()


class TestRemovePolkitRules:
    def test_returns_false_when_moonraker_dir_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(moonraker_utils, "MOONRAKER_DIR", tmp_path / "missing")

        assert remove_polkit_rules() is False

    def test_returns_true_on_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(moonraker_utils, "MOONRAKER_DIR", tmp_path)
        monkeypatch.setattr(
            moonraker_utils,
            "run",
            lambda *a, **k: type("R", (), {"returncode": 0})(),
        )

        assert remove_polkit_rules() is True

    def test_returns_false_on_command_failure(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(moonraker_utils, "MOONRAKER_DIR", tmp_path)

        def fake_run(*a, **k):
            raise moonraker_utils.CalledProcessError(1, cmd="clear")

        monkeypatch.setattr(moonraker_utils, "run", fake_run)

        assert remove_polkit_rules() is False


class TestCreateExampleMoonrakerConf:
    def test_skips_when_config_already_exists(
        self, monkeypatch: pytest.MonkeyPatch, fake_instance: FakeMoonraker
    ) -> None:
        fake_instance.cfg_file.parent.mkdir(parents=True, exist_ok=True)
        fake_instance.cfg_file.write_text("existing")

        create_example_moonraker_conf(fake_instance, {})

        # no changes expected
        assert fake_instance.cfg_file.read_text() == "existing"

    def test_creates_config_with_default_port(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        fake_instance: FakeMoonraker,
    ) -> None:
        fake_instance.cfg_file.parent.mkdir(parents=True, exist_ok=True)
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        template = assets_dir / "moonraker.conf"
        template.write_text(
            "[server]\nport: %{PORT}%\nklippy_uds_address: %{UDS}%\n"
            "[authorization]\ntrusted_clients:\n    %{CLIENTS}%\n"
        )
        monkeypatch.setattr(moonraker_utils, "MODULE_PATH", tmp_path)
        monkeypatch.setattr(
            moonraker_utils, "get_ipv4_addr", lambda: "192.168.1.10"
        )

        create_example_moonraker_conf(fake_instance, {})

        content = fake_instance.cfg_file.read_text()
        assert "192.168.0.0/16" in content


class TestBackupMoonrakerDir:
    def test_backs_up_repository_and_environment(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        calls: List[Dict[str, Any]] = []

        class FakeBackup:
            def backup_directory(self, **kwargs):
                calls.append(kwargs)

        monkeypatch.setattr(moonraker_utils, "BackupService", FakeBackup)
        monkeypatch.setattr(moonraker_utils, "MOONRAKER_DIR", tmp_path / "moonraker")
        monkeypatch.setattr(moonraker_utils, "MOONRAKER_ENV_DIR", tmp_path / "env")

        backup_moonraker_dir()

        assert len(calls) == 2


class TestBackupMoonrakerDbDir:
    def test_backs_up_db_for_each_instance(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        calls: List[Dict[str, Any]] = []

        class FakeBackup:
            def backup_directory(self, **kwargs):
                calls.append(kwargs)

        monkeypatch.setattr(moonraker_utils, "BackupService", FakeBackup)
        monkeypatch.setattr(
            moonraker_utils, "get_instances", lambda model: [FakeMoonraker("")]
        )

        backup_moonraker_db_dir()

        assert len(calls) == 1

    def test_falls_back_to_home_dirs(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        printer_data = tmp_path / "printer_data"
        printer_data.mkdir()
        printer_data.joinpath("database").mkdir()

        calls: List[Dict[str, Any]] = []

        class FakeBackup:
            def backup_directory(self, **kwargs):
                calls.append(kwargs)

        monkeypatch.setattr(moonraker_utils, "BackupService", FakeBackup)
        monkeypatch.setattr(moonraker_utils, "get_instances", lambda model: [])

        backup_moonraker_db_dir()

        assert len(calls) == 1


class TestLoadSysdepsJson:
    def test_loads_valid_json(self, tmp_path: Path) -> None:
        file = tmp_path / "deps.json"
        file.write_text('{"debian": ["curl"]}')

        result = load_sysdeps_json(file)

        assert result == {"debian": ["curl"]}

    def test_returns_empty_on_invalid_json(self, tmp_path: Path) -> None:
        file = tmp_path / "deps.json"
        file.write_text("not json")

        result = load_sysdeps_json(file)

        assert result == {}
