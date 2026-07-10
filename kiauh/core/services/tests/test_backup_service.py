from __future__ import annotations

from pathlib import Path

import pytest
from core.services.backup_service import BackupService


class FakeKlipper:
    def __init__(self, suffix: str = "") -> None:
        self.suffix = suffix
        self.data_dir = Path(f"/tmp/klipper{suffix}_data")
        self.cfg_file = self.data_dir.joinpath("printer.cfg")


class FakeMoonraker:
    def __init__(self, suffix: str = "") -> None:
        self.suffix = suffix
        self.data_dir = Path(f"/tmp/moonraker{suffix}_data")
        self.cfg_file = self.data_dir.joinpath("moonraker.conf")


@pytest.fixture
def service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BackupService:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    svc = BackupService()
    return svc


class TestBackupFile:
    def test_returns_false_when_source_does_not_exist(self, service: BackupService) -> None:
        result = service.backup_file(source_path=Path("/does/not/exist.cfg"))
        assert result is False

    def test_returns_false_when_source_is_not_a_file(
        self, service: BackupService, tmp_path: Path
    ) -> None:
        directory = tmp_path / "directory"
        directory.mkdir()
        result = service.backup_file(source_path=directory)
        assert result is False

    def test_creates_backup_and_returns_true(
        self, service: BackupService, tmp_path: Path
    ) -> None:
        source = tmp_path / "printer.cfg"
        source.write_text("config")

        result = service.backup_file(source_path=source)

        assert result is True
        backups = list(service.backup_root.glob("*.cfg"))
        assert len(backups) == 1
        assert backups[0].read_text() == "config"

    def test_skips_when_target_already_exists(
        self, service: BackupService, tmp_path: Path
    ) -> None:
        source = tmp_path / "printer.cfg"
        source.write_text("config")
        service.backup_root.mkdir(parents=True, exist_ok=True)
        expected_name = f"printer_{service.timestamp}.cfg"
        service.backup_root.joinpath(expected_name).touch()

        result = service.backup_file(source_path=source)

        assert result is True

    def test_returns_false_on_copy_error(
        self, service: BackupService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = tmp_path / "printer.cfg"
        source.write_text("config")
        monkeypatch.setattr(
            "core.services.backup_service.shutil.copy2",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("copy failed")),
        )

        result = service.backup_file(source_path=source)

        assert result is False


class TestBackupDirectory:
    def test_returns_none_when_source_does_not_exist(
        self, service: BackupService
    ) -> None:
        result = service.backup_directory(
            source_path=Path("/does/not/exist"), backup_name="config"
        )
        assert result is None

    def test_returns_none_when_source_is_not_a_directory(
        self, service: BackupService, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "file.txt"
        file_path.write_text("data")
        result = service.backup_directory(
            source_path=file_path, backup_name="config"
        )
        assert result is None

    def test_creates_timestamped_backup_directory(
        self, service: BackupService, tmp_path: Path
    ) -> None:
        source = tmp_path / "config"
        source.mkdir()
        source.joinpath("printer.cfg").write_text("data")

        result = service.backup_directory(
            source_path=source, backup_name="config"
        )

        assert result is not None
        assert result.exists()
        assert result.joinpath("printer.cfg").read_text() == "data"

    def test_reuses_existing_backup_and_skips_existing_files(
        self, service: BackupService, tmp_path: Path
    ) -> None:
        source = tmp_path / "config"
        source.mkdir()
        source.joinpath("printer.cfg").write_text("new")
        backup_dir = service.backup_root.joinpath(f"config_{service.timestamp}")
        backup_dir.mkdir(parents=True)
        backup_dir.joinpath("printer.cfg").write_text("old")

        result = service.backup_directory(
            source_path=source, backup_name="config"
        )

        assert result == backup_dir
        assert result.joinpath("printer.cfg").read_text() == "old"

    def test_returns_none_on_copy_error(
        self, service: BackupService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = tmp_path / "config"
        source.mkdir()
        source.joinpath("file.cfg").write_text("data")
        monkeypatch.setattr(
            "core.services.backup_service.shutil.copytree",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("copytree failed")),
        )

        result = service.backup_directory(
            source_path=source, backup_name="config"
        )

        assert result is None


class TestSpecificBackupMethods:
    def test_backup_printer_cfg_backs_up_each_instance(
        self, service: BackupService, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        instances = [FakeKlipper(""), FakeKlipper("a")]
        for i in instances:
            i.cfg_file.parent.mkdir(parents=True, exist_ok=True)
            i.cfg_file.write_text("printer config")
        monkeypatch.setattr(
            "core.services.backup_service.get_instances", lambda model: instances
        )

        service.backup_printer_cfg()

        backups = list(service.backup_root.rglob("printer*.cfg"))
        assert len(backups) == 2

    def test_backup_moonraker_conf_backs_up_each_instance(
        self, service: BackupService, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        instances = [FakeMoonraker(""), FakeMoonraker("a")]
        for i in instances:
            i.cfg_file.parent.mkdir(parents=True, exist_ok=True)
            i.cfg_file.write_text("moonraker config")
        monkeypatch.setattr(
            "core.services.backup_service.get_instances", lambda model: instances
        )

        service.backup_moonraker_conf()

        backups = list(service.backup_root.rglob("moonraker*.conf"))
        assert len(backups) == 2

    def test_backup_printer_config_dir_falls_back_to_home_dirs(
        self, service: BackupService, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(
            "core.services.backup_service.get_instances", lambda model: []
        )
        printer_data = tmp_path / "printer_data"
        printer_data.mkdir()
        config_dir = printer_data / "config"
        config_dir.mkdir()
        config_dir.joinpath("printer.cfg").write_text("home config")

        service.backup_printer_config_dir()

        backups = list(service.backup_root.rglob("printer_data/config_*/printer.cfg"))
        assert len(backups) == 1

    def test_backup_printer_config_dir_returns_when_no_dirs_found(
        self, service: BackupService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "core.services.backup_service.get_instances", lambda model: []
        )

        # should not raise and should not create backups
        service.backup_printer_config_dir()

        assert not service.backup_root.exists()
