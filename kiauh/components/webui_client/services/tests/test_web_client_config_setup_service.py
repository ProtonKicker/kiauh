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
from typing import Any, Dict, List

import pytest
from components.webui_client.services.web_client_config_setup_service import (
    WebClientConfigSetupService,
)


@pytest.fixture
def bind_client(client, monkeypatch: pytest.MonkeyPatch):
    """Make the service construct the per-test FakeWebClient instead of the real data class."""
    monkeypatch.setattr(
        WebClientConfigSetupService,
        "CLIENTS",
        {"mainsail": lambda: client, "fluidd": lambda: client},
    )
    return client


@pytest.fixture
def patched_install_deps(monkeypatch: pytest.MonkeyPatch) -> Dict[str, List[Any]]:
    calls: Dict[str, List[Any]] = {
        "download": [],
        "symlink": [],
        "backup_printer": [],
        "add_section": [],
        "add_section_at_top": [],
        "restart": [],
    }
    module = "components.webui_client.services.web_client_config_setup_service"
    monkeypatch.setattr(f"{module}.detect_client_cfg_conflict", lambda c: False)
    monkeypatch.setattr(f"{module}.get_instances", lambda model: [])
    monkeypatch.setattr(
        f"{module}.git_clone_wrapper",
        lambda repo, target: calls["download"].append((repo, str(target))),
    )
    monkeypatch.setattr(
        f"{module}.create_client_config_symlink",
        lambda cfg, kl: calls["symlink"].append((cfg.name, kl)),
    )

    class FakeBackup:
        def backup_printer_config_dir(self) -> None:
            calls["backup_printer"].append(True)

    monkeypatch.setattr(f"{module}.BackupService", FakeBackup)
    monkeypatch.setattr(
        f"{module}.add_config_section",
        lambda **kwargs: calls["add_section"].append(kwargs["section"]),
    )
    monkeypatch.setattr(
        f"{module}.add_config_section_at_top",
        lambda section, instances: calls["add_section_at_top"].append(section),
    )
    monkeypatch.setattr(
        f"{module}.InstanceManager.restart_all",
        staticmethod(lambda instances: calls["restart"].append(len(instances))),
    )
    return calls


class TestWebClientConfigSetupServiceConstruction:
    def test_accepts_known_clients(self) -> None:
        for name in ("mainsail", "fluidd"):
            svc = WebClientConfigSetupService(name)
            assert svc.name == name

    def test_rejects_unknown_client(self) -> None:
        with pytest.raises(ValueError):
            WebClientConfigSetupService("unknown")

    def test_clients_mapping_is_the_single_shared_source(self) -> None:
        # there must be exactly one CLIENTS dict, imported from
        # components.webui_client by both web-client services.
        from components import webui_client
        from components.webui_client.services.web_client_setup_service import (
            WebClientSetupService,
        )

        assert webui_client.CLIENTS is WebClientConfigSetupService.CLIENTS
        assert webui_client.CLIENTS is WebClientSetupService.CLIENTS
        assert set(WebClientConfigSetupService.CLIENTS.keys()) == {"mainsail", "fluidd"}


class TestInstallClientConfig:
    def test_installs_when_clean(
        self, bind_client, patched_install_deps, tmp_path: Path
    ) -> None:
        bind_client.client_config.config_dir = tmp_path / "mainsail-config"
        result = WebClientConfigSetupService("mainsail").install()

        assert result is True
        assert patched_install_deps["download"]
        assert patched_install_deps["symlink"]
        assert "update_manager mainsail-config" in patched_install_deps["add_section"]

    def test_skips_when_conflict_detected(
        self, bind_client, patched_install_deps, monkeypatch
    ) -> None:
        module = "components.webui_client.services.web_client_config_setup_service"
        monkeypatch.setattr(f"{module}.detect_client_cfg_conflict", lambda c: True)

        result = WebClientConfigSetupService("mainsail").install()

        assert result is True
        assert patched_install_deps["download"] == []

    def test_interactive_reinstall_after_confirm(
        self, bind_client, patched_install_deps, monkeypatch, tmp_path: Path
    ) -> None:
        module = "components.webui_client.services.web_client_config_setup_service"
        bind_client.client_config.config_dir = tmp_path / "mainsail-config"
        bind_client.client_config.config_dir.mkdir(parents=True, exist_ok=True)
        removed: List[Path] = []
        monkeypatch.setattr(f"{module}.shutil.rmtree", lambda p: removed.append(p))
        monkeypatch.setattr(f"{module}.get_confirm", lambda *a, **k: True)

        result = WebClientConfigSetupService("mainsail").install(interactive=True)

        assert result is True
        assert removed == [bind_client.client_config.config_dir]
        assert patched_install_deps["download"]

    def test_interactive_decline_reinstall_skips(
        self, bind_client, patched_install_deps, monkeypatch, tmp_path: Path
    ) -> None:
        module = "components.webui_client.services.web_client_config_setup_service"
        bind_client.client_config.config_dir = tmp_path / "mainsail-config"
        bind_client.client_config.config_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(
            f"{module}.shutil.rmtree", lambda p: pytest.fail("no rmtree")
        )
        monkeypatch.setattr(f"{module}.get_confirm", lambda *a, **k: False)

        result = WebClientConfigSetupService("mainsail").install(interactive=True)

        assert result is True
        assert patched_install_deps["download"] == []

    def test_non_interactive_existing_dir_skips(
        self, bind_client, patched_install_deps, monkeypatch, tmp_path: Path
    ) -> None:
        module = "components.webui_client.services.web_client_config_setup_service"
        bind_client.client_config.config_dir = tmp_path / "mainsail-config"
        bind_client.client_config.config_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(
            f"{module}.get_confirm",
            lambda *a, **k: pytest.fail("should not prompt in headless mode"),
        )

        result = WebClientConfigSetupService("mainsail").install(interactive=False)

        assert result is True
        assert patched_install_deps["download"] == []

    def test_install_failure_returns_false(
        self, bind_client, patched_install_deps, monkeypatch, tmp_path: Path
    ) -> None:
        bind_client.client_config.config_dir = tmp_path / "mainsail-config"
        module = "components.webui_client.services.web_client_config_setup_service"
        monkeypatch.setattr(
            f"{module}.git_clone_wrapper",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        result = WebClientConfigSetupService("mainsail").install()

        assert result is False


class TestUpdateClientConfig:
    def test_update_skips_when_dir_missing(
        self, bind_client, monkeypatch, tmp_path: Path
    ) -> None:
        bind_client.client_config.config_dir = tmp_path / "mainsail-config"
        module = "components.webui_client.services.web_client_config_setup_service"
        pulled: List[Any] = []
        monkeypatch.setattr(
            f"{module}.git_pull_wrapper", lambda *a, **k: pulled.append("pull")
        )

        result = WebClientConfigSetupService("mainsail").update()

        assert result is True
        assert pulled == []

    def test_update_pulls_when_dir_exists(
        self, bind_client, monkeypatch, tmp_path: Path
    ) -> None:
        module = "components.webui_client.services.web_client_config_setup_service"
        bind_client.client_config.config_dir = tmp_path / "mainsail-config"
        bind_client.client_config.config_dir.mkdir(parents=True, exist_ok=True)
        pulled: List[Any] = []
        monkeypatch.setattr(
            f"{module}.git_pull_wrapper", lambda *a, **k: pulled.append("pull")
        )
        monkeypatch.setattr(f"{module}.backup_client_config_data", lambda c: None)

        result = WebClientConfigSetupService("mainsail").update()

        assert result is True
        assert pulled == ["pull"]

    def test_update_failure_returns_false(
        self, bind_client, monkeypatch, tmp_path: Path
    ) -> None:
        module = "components.webui_client.services.web_client_config_setup_service"
        bind_client.client_config.config_dir = tmp_path / "mainsail-config"
        bind_client.client_config.config_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(
            f"{module}.git_pull_wrapper",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        monkeypatch.setattr(f"{module}.backup_client_config_data", lambda c: None)

        result = WebClientConfigSetupService("mainsail").update()

        assert result is False

    def test_update_non_interactive_omits_restart_hint(
        self, bind_client, monkeypatch, tmp_path: Path
    ) -> None:
        module = "components.webui_client.services.web_client_config_setup_service"
        bind_client.client_config.config_dir = tmp_path / "mainsail-config"
        bind_client.client_config.config_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(f"{module}.git_pull_wrapper", lambda *a, **k: None)
        monkeypatch.setattr(f"{module}.backup_client_config_data", lambda c: None)
        printed: List[str] = []
        monkeypatch.setattr(
            f"{module}.Logger.print_info", lambda msg, *a, **k: printed.append(str(msg))
        )

        WebClientConfigSetupService("mainsail").update(interactive=False)

        assert not any("Restart Klipper" in m for m in printed)

    def test_update_interactive_shows_restart_hint(
        self, bind_client, monkeypatch, tmp_path: Path
    ) -> None:
        module = "components.webui_client.services.web_client_config_setup_service"
        bind_client.client_config.config_dir = tmp_path / "mainsail-config"
        bind_client.client_config.config_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(f"{module}.git_pull_wrapper", lambda *a, **k: None)
        monkeypatch.setattr(f"{module}.backup_client_config_data", lambda c: None)
        printed: List[str] = []
        monkeypatch.setattr(
            f"{module}.Logger.print_info", lambda msg, *a, **k: printed.append(str(msg))
        )

        WebClientConfigSetupService("mainsail").update(interactive=True)

        assert any("Restart Klipper" in m for m in printed)


class TestRemoveClientConfig:
    def test_remove_signature_rejects_unused_interactive_parameter(
        self, bind_client, monkeypatch
    ) -> None:
        module = "components.webui_client.services.web_client_config_setup_service"
        monkeypatch.setattr(f"{module}.get_instances", lambda model: [])
        monkeypatch.setattr(f"{module}.run_remove_routines", lambda p: True)
        monkeypatch.setattr(f"{module}.remove_config_section", lambda s, i: i)

        class FakeBackup:
            def backup_moonraker_conf(self) -> None:
                pass

            def backup_printer_cfg(self) -> None:
                pass

        monkeypatch.setattr(f"{module}.BackupService", FakeBackup)
        monkeypatch.setattr(
            f"{module}.MessageService",
            lambda: type("MS", (), {"set_message": lambda self, m: None})(),
        )

        with pytest.raises(TypeError):
            WebClientConfigSetupService("mainsail").remove(interactive=True)

    def test_remove_runs_dir_and_section_cleanup(
        self, bind_client, monkeypatch
    ) -> None:
        module = "components.webui_client.services.web_client_config_setup_service"
        removed: List[str] = []
        sections: List[str] = []
        monkeypatch.setattr(f"{module}.get_instances", lambda model: [])
        monkeypatch.setattr(
            f"{module}.run_remove_routines",
            lambda p: removed.append(str(p)) or True,
        )
        monkeypatch.setattr(
            f"{module}.remove_config_section",
            lambda section, instances: sections.append(section) or instances,
        )

        class FakeBackup:
            def backup_moonraker_conf(self) -> None:
                pass

            def backup_printer_cfg(self) -> None:
                pass

        monkeypatch.setattr(f"{module}.BackupService", FakeBackup)
        monkeypatch.setattr(
            f"{module}.MessageService",
            lambda: type("MS", (), {"set_message": lambda self, m: None})(),
        )

        result = WebClientConfigSetupService("mainsail").remove()

        assert result is True
        assert any("mainsail-config" in p for p in removed)

    def test_remove_failure_returns_false(self, bind_client, monkeypatch) -> None:
        module = "components.webui_client.services.web_client_config_setup_service"
        monkeypatch.setattr(f"{module}.get_instances", lambda model: [])
        monkeypatch.setattr(
            f"{module}.run_remove_routines",
            lambda p: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        class FakeBackup:
            def backup_moonraker_conf(self) -> None:
                pass

            def backup_printer_cfg(self) -> None:
                pass

        monkeypatch.setattr(f"{module}.BackupService", FakeBackup)
        monkeypatch.setattr(
            f"{module}.MessageService",
            lambda: type("MS", (), {"set_message": lambda self, m: None})(),
        )

        result = WebClientConfigSetupService("mainsail").remove()

        assert result is False


class TestRemoveConfig:
    """The config-removal operation mutates the filesystem and returns the
    completion message. Its name must reflect that it does the removal, not
    merely build a message."""

    def test_old_build_removal_message_name_no_longer_exists(self) -> None:
        assert not hasattr(WebClientConfigSetupService, "build_removal_message")

    def test_remove_config_performs_destructive_removal_and_returns_message(
        self, bind_client, monkeypatch
    ) -> None:
        module = "components.webui_client.services.web_client_config_setup_service"
        removed: List[str] = []
        monkeypatch.setattr(f"{module}.get_instances", lambda model: [])
        monkeypatch.setattr(
            f"{module}.run_remove_routines",
            lambda p: removed.append(str(p)) or True,
        )
        monkeypatch.setattr(
            f"{module}.remove_config_section",
            lambda section, instances: instances,
        )

        class FakeBackup:
            def backup_moonraker_conf(self) -> None:
                pass

            def backup_printer_cfg(self) -> None:
                pass

        monkeypatch.setattr(f"{module}.BackupService", FakeBackup)

        message = WebClientConfigSetupService("mainsail").remove_config(
            kl_instances=[], mr_instances=[], backup_config=False
        )

        assert removed  # destructive removal actually ran
        assert message.text  # completion message populated
        assert any("config" in line.lower() for line in message.text)

    def test_remove_config_nothing_to_remove_message(
        self, bind_client, monkeypatch
    ) -> None:
        module = "components.webui_client.services.web_client_config_setup_service"
        monkeypatch.setattr(f"{module}.get_instances", lambda model: [])
        monkeypatch.setattr(f"{module}.run_remove_routines", lambda p: False)
        monkeypatch.setattr(
            f"{module}.remove_config_section",
            lambda section, instances: instances,
        )

        class FakeBackup:
            def backup_moonraker_conf(self) -> None:
                pass

            def backup_printer_cfg(self) -> None:
                pass

        monkeypatch.setattr(f"{module}.BackupService", FakeBackup)

        message = WebClientConfigSetupService("mainsail").remove_config(
            kl_instances=[], mr_instances=[]
        )

        assert "Nothing to remove." in message.text
