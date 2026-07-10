# ======================================================================= #
#  Copyright (C) 2020 - 2026 Dominik Willner <th33xitus@gmail.com>        #
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
from components.webui_client.base_data import WebClientType
from components.webui_client.services.web_client_setup_service import (
    WebClientSetupService,
)


@pytest.fixture
def bind_client(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        WebClientSetupService, "CLIENTS", {"mainsail": lambda: client, "fluidd": lambda: client}
    )
    return client


class FakeInstance:
    def __init__(self, suffix: str = "") -> None:
        self.suffix = suffix
        self.service_file_path = Path(f"service-{suffix}.service")
        self.base = type("Base", (), {"log_dir": Path(f"/tmp/log-{suffix}")})()


@pytest.fixture
def patch_install_deps(monkeypatch: pytest.MonkeyPatch) -> Dict[str, List[Any]]:
    calls: Dict[str, List[Any]] = {
        "download_client": [],
        "enable_remotemode": [],
        "backup_printer": [],
        "add_config_section": [],
        "restart_all": [],
        "install_client_config": [],
        "copy_upstream": [],
        "copy_common_vars": [],
        "create_nginx_cfg": [],
        "symlink_logs": [],
        "restart_nginx": [],
    }
    module = "components.webui_client.services.web_client_setup_service"
    monkeypatch.setattr(f"{module}.get_instances", lambda model: [])
    monkeypatch.setattr(f"{module}.check_install_dependencies", lambda packages: None)
    monkeypatch.setattr(
        f"{module}._download_client",
        lambda client: calls["download_client"].append(client.name),
    )
    monkeypatch.setattr(
        f"{module}.enable_mainsail_remotemode",
        lambda: calls["enable_remotemode"].append(True),
    )

    class FakeBackup:
        def backup_printer_config_dir(self) -> None:
            calls["backup_printer"].append(True)

        def backup_moonraker_conf(self) -> None:
            calls["backup_printer"].append("moonraker_conf")

    monkeypatch.setattr(f"{module}.BackupService", FakeBackup)
    monkeypatch.setattr(
        f"{module}.add_config_section",
        lambda **kwargs: calls["add_config_section"].append(kwargs),
    )
    monkeypatch.setattr(
        f"{module}.InstanceManager.restart_all",
        staticmethod(lambda instances: calls["restart_all"].append(len(instances))),
    )
    monkeypatch.setattr(
        f"{module}.WebClientConfigSetupService",
        lambda name: type(
            "FakeCfgSvc",
            (),
            {
                "install": lambda self, cfg_backup=True, interactive=True: (
                    calls["install_client_config"].append((name, cfg_backup, interactive))
                    or True
                )
            },
        )(),
    )
    monkeypatch.setattr(
        f"{module}.copy_upstream_nginx_cfg", lambda: calls["copy_upstream"].append(True)
    )
    monkeypatch.setattr(
        f"{module}.copy_common_vars_nginx_cfg",
        lambda: calls["copy_common_vars"].append(True),
    )
    monkeypatch.setattr(
        f"{module}.create_nginx_cfg",
        lambda **kwargs: calls["create_nginx_cfg"].append(kwargs),
    )
    monkeypatch.setattr(
        f"{module}.symlink_webui_nginx_log",
        lambda client, instances: calls["symlink_logs"].append(
            (client.name, len(instances))
        ),
    )
    monkeypatch.setattr(
        f"{module}.cmd_sysctl_service",
        lambda service, action: calls["restart_nginx"].append((service, action)),
    )
    return calls


class TestWebClientSetupServiceConstruction:
    @pytest.mark.parametrize("name", ["mainsail", "fluidd"])
    def test_accepts_known_clients(self, name: str) -> None:
        svc = WebClientSetupService(name)
        assert svc.name == name

    def test_rejects_unknown_client(self) -> None:
        with pytest.raises(ValueError):
            WebClientSetupService("unknown")


class TestInstallClient:
    def test_interactive_install_runs_all_steps(
        self, bind_client, patch_install_deps, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service.get_client_port_selection",
            lambda c, s, reconfigure=False: 80,
        )
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service.get_confirm",
            lambda *a, **k: True,
        )

        result = WebClientSetupService("mainsail").install()

        assert result is True
        assert patch_install_deps["download_client"] == ["mainsail"]
        assert patch_install_deps["create_nginx_cfg"]
        assert patch_install_deps["restart_nginx"] == [("nginx", "restart")]

    def test_headless_install_uses_explicit_port_and_cfg(
        self, bind_client, patch_install_deps, monkeypatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service.get_confirm",
            lambda *a, **k: pytest.fail("should not prompt in headless mode"),
        )
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service.get_client_port_selection",
            lambda *a, **k: pytest.fail("should not select port interactively"),
        )
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service.get_instances",
            lambda model: [FakeInstance()] if model.__name__ == "Klipper" else [],
        )
        bind_client.client_config.config_dir = tmp_path / "mainsail-config"

        result = WebClientSetupService("mainsail").install(
            interactive=False, port=8080, install_client_cfg=True, continue_without_moonraker=True
        )

        assert result is True
        assert patch_install_deps["download_client"] == ["mainsail"]
        assert patch_install_deps["install_client_config"] == [("mainsail", False, False)]
        nginx_call = patch_install_deps["create_nginx_cfg"][0]
        assert nginx_call["PORT"] == 8080

    def test_reinstall_uses_default_port_without_prompting(
        self, bind_client, patch_install_deps, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service.get_instances",
            lambda model: [FakeInstance()] if model.__name__ == "Moonraker" else [],
        )
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service.get_client_port_selection",
            lambda *a, **k: pytest.fail("should not prompt for port during reinstall"),
        )
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service.get_confirm",
            lambda *a, **k: pytest.fail("should not prompt during reinstall"),
        )

        result = WebClientSetupService("mainsail").install(reinstall=True, interactive=True)

        assert result is True
        nginx_call = patch_install_deps["create_nginx_cfg"][0]
        assert nginx_call["PORT"] == 80

    def test_reinstall_explicit_port_overrides_default(
        self, bind_client, patch_install_deps, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service.get_instances",
            lambda model: [FakeInstance()] if model.__name__ == "Moonraker" else [],
        )
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service.get_client_port_selection",
            lambda *a, **k: pytest.fail("should not prompt when port is explicit"),
        )
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service.get_confirm",
            lambda *a, **k: pytest.fail("should not prompt during reinstall"),
        )

        result = WebClientSetupService("mainsail").install(
            reinstall=True, interactive=True, port=9090
        )

        assert result is True
        nginx_call = patch_install_deps["create_nginx_cfg"][0]
        assert nginx_call["PORT"] == 9090

    def test_headless_install_without_moonraker_returns_false(
        self, bind_client, patch_install_deps
    ) -> None:
        result = WebClientSetupService("mainsail").install(
            interactive=False, continue_without_moonraker=False
        )

        assert result is False
        assert patch_install_deps["download_client"] == []

    def test_install_failure_returns_false(
        self, bind_client, patch_install_deps, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service._download_client",
            lambda client: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        result = WebClientSetupService("mainsail").install(
            interactive=False, continue_without_moonraker=True
        )

        assert result is False

    def test_headless_install_failure_does_not_show_error_dialog(
        self, bind_client, patch_install_deps, monkeypatch
    ) -> None:
        module = "components.webui_client.services.web_client_setup_service"
        monkeypatch.setattr(
            f"{module}._download_client",
            lambda client: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        monkeypatch.setattr(
            f"{module}.Logger.print_dialog",
            lambda *a, **k: pytest.fail("should not show error dialog in headless mode"),
        )

        result = WebClientSetupService("mainsail").install(
            interactive=False, continue_without_moonraker=True
        )

        assert result is False

    def test_headless_install_does_not_show_completion_dialog(
        self, bind_client, patch_install_deps, monkeypatch
    ) -> None:
        module = "components.webui_client.services.web_client_setup_service"
        monkeypatch.setattr(
            f"{module}.get_confirm",
            lambda *a, **k: pytest.fail("should not prompt in headless mode"),
        )
        monkeypatch.setattr(
            f"{module}.Logger.print_dialog",
            lambda *a, **k: pytest.fail("should not show dialog in headless mode"),
        )

        result = WebClientSetupService("mainsail").install(
            interactive=False, continue_without_moonraker=True
        )

        assert result is True

    def test_interactive_install_shows_completion_dialog(
        self, bind_client, patch_install_deps, monkeypatch
    ) -> None:
        module = "components.webui_client.services.web_client_setup_service"
        monkeypatch.setattr(
            f"{module}.get_confirm", lambda *a, **k: True
        )
        monkeypatch.setattr(
            f"{module}.get_client_port_selection",
            lambda c, s, reconfigure=False: 80,
        )
        dialog_calls: List[Any] = []
        monkeypatch.setattr(
            f"{module}.Logger.print_dialog",
            lambda *a, **k: dialog_calls.append(k),
        )

        WebClientSetupService("mainsail").install(interactive=True)

        assert dialog_calls


class TestUpdateClient:
    def test_update_downloads_and_restores_config(
        self, bind_client, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service._download_client",
            lambda c: None,
        )
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service.shutil.copy",
            lambda src, dst: None,
        )
        bind_client.client_dir.mkdir(parents=True, exist_ok=True)
        bind_client.config_file.write_text("{}")

        result = WebClientSetupService("mainsail").update()

        assert result is True

    def test_update_missing_dir_returns_true(
        self, bind_client, monkeypatch, tmp_path: Path
    ) -> None:
        bind_client.client_dir = tmp_path / "does-not-exist"
        pulled: List[Any] = []
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service._download_client",
            lambda c: pulled.append("download"),
        )

        result = WebClientSetupService("mainsail").update()

        assert result is True
        assert pulled == []

    def test_update_failure_returns_false(
        self, bind_client, monkeypatch
    ) -> None:
        bind_client.client_dir.mkdir(parents=True, exist_ok=True)
        bind_client.config_file.write_text("{}")
        monkeypatch.setattr(
            "components.webui_client.services.web_client_setup_service._download_client",
            lambda c: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        result = WebClientSetupService("mainsail").update()

        assert result is False

    def test_update_accepts_interactive_parameter(
        self, bind_client, monkeypatch
    ) -> None:
        module = "components.webui_client.services.web_client_setup_service"
        bind_client.client_dir.mkdir(parents=True, exist_ok=True)
        bind_client.config_file.write_text("{}")
        monkeypatch.setattr(f"{module}._download_client", lambda c: None)
        monkeypatch.setattr(f"{module}.shutil.copy", lambda s, d: None)

        result = WebClientSetupService("mainsail").update(interactive=False)

        assert result is True

    def test_update_headless_does_not_show_dialog(
        self, bind_client, monkeypatch
    ) -> None:
        module = "components.webui_client.services.web_client_setup_service"
        bind_client.client_dir.mkdir(parents=True, exist_ok=True)
        bind_client.config_file.write_text("{}")
        monkeypatch.setattr(f"{module}._download_client", lambda c: None)
        monkeypatch.setattr(f"{module}.shutil.copy", lambda s, d: None)
        monkeypatch.setattr(
            f"{module}.Logger.print_dialog",
            lambda *a, **k: pytest.fail("should not show dialog in headless update"),
        )

        result = WebClientSetupService("mainsail").update(interactive=False)

        assert result is True


class TestRemoveClientHelpers:
    """Directly exercise the small removal helper methods so the destructive
    remove path is covered beyond the integrated ``remove()`` test."""

    def test_remove_client_dir_returns_run_remove_result(self, bind_client, monkeypatch) -> None:
        module = "components.webui_client.services.web_client_setup_service"
        monkeypatch.setattr(
            f"{module}.run_remove_routines", lambda p: True
        )
        svc = WebClientSetupService("mainsail")
        assert svc._remove_client_dir() is True

    def test_remove_client_nginx_config_delegates_to_sudo(self, bind_client, monkeypatch) -> None:
        module = "components.webui_client.services.web_client_setup_service"
        removed: List[Any] = []
        monkeypatch.setattr(
            f"{module}.remove_with_sudo", lambda files: removed.append(files) or True
        )
        svc = WebClientSetupService("mainsail")
        assert svc._remove_client_nginx_config("mainsail") is True
        assert removed  # files passed through

    def test_remove_client_nginx_logs_appends_per_instance_paths(
        self, bind_client, monkeypatch
    ) -> None:
        module = "components.webui_client.services.web_client_setup_service"
        passed: List[Any] = []
        monkeypatch.setattr(
            f"{module}.remove_with_sudo", lambda files: passed.append(files) or True
        )

        class FakeKlipperInstance:
            def __init__(self, suffix: str) -> None:
                self.suffix = suffix
                self.base = type("Base", (), {"log_dir": Path(f"/tmp/log-{suffix}")})()

        svc = WebClientSetupService("mainsail")
        result = svc._remove_client_nginx_logs(
            svc.client, [FakeKlipperInstance("a"), FakeKlipperInstance("b")]
        )

        assert result is True
        # 2 base log files + 2 per instance * 2 = 6 files total
        assert len(passed[0]) == 6


class TestRemoteModeLogic:
    @pytest.mark.parametrize(
        "client_name, instance_count, expected",
        [
            ("mainsail", 0, True),
            ("mainsail", 1, False),
            ("mainsail", 2, True),
            ("fluidd", 0, False),
            ("fluidd", 2, False),
        ],
    )
    def test_should_enable_remote_mode(
        self, client_name: str, instance_count: int, expected: bool
    ) -> None:
        svc = WebClientSetupService(client_name)
        mr_instances = [FakeInstance(str(i)) for i in range(instance_count)]

        result = svc._should_enable_remote_mode(mr_instances)

        assert result is expected

    def test_should_enable_remote_mode_rejects_non_mainsail(
        self) -> None:
        svc = WebClientSetupService("mainsail")
        svc.client = type("NotMainsail", (), {"client": WebClientType.FLUIDD})()

        assert svc._should_enable_remote_mode([]) is False


class TestRemoveClient:
    def test_remove_client_and_config(
        self, bind_client, monkeypatch
    ) -> None:
        module = "components.webui_client.services.web_client_setup_service"
        removed_dir: List[str] = []
        sections: List[str] = []
        monkeypatch.setattr(f"{module}.get_instances", lambda model: [])
        monkeypatch.setattr(
            f"{module}.run_remove_routines",
            lambda p: removed_dir.append(str(p)) or True,
        )
        monkeypatch.setattr(f"{module}.remove_with_sudo", lambda files: True)

        class FakeBackup:
            def backup_moonraker_conf(self) -> None:
                pass

            def backup_file(self, **kwargs) -> bool:
                return True

        monkeypatch.setattr(f"{module}.BackupService", FakeBackup)
        monkeypatch.setattr(
            f"{module}.remove_config_section",
            lambda section, instances: sections.append(section) or instances,
        )
        build_called: List[Any] = []
        monkeypatch.setattr(
            f"{module}.WebClientConfigSetupService",
            lambda name: type(
                "FakeCfgSvc",
                (),
                {
                    "remove_config": lambda self, kl_instances, mr_instances, backup_config=True, svc=None: (
                        build_called.append(name) or type(
                            "Msg", (), {"color": 2, "text": ["x", "config removed"]}
                        )()
                    )
                },
            )(),
        )
        monkeypatch.setattr(
            f"{module}.MessageService",
            lambda: type("MS", (), {"set_message": lambda self, m: None})(),
        )

        result = WebClientSetupService("mainsail").remove(
            remove_client=True, remove_client_cfg=True, backup_config=False
        )

        assert result is True
        assert build_called == ["mainsail"]
        assert "update_manager mainsail" in sections

    def test_remove_failure_returns_false(
        self, bind_client, monkeypatch
    ) -> None:
        module = "components.webui_client.services.web_client_setup_service"
        monkeypatch.setattr(f"{module}.get_instances", lambda model: [])
        monkeypatch.setattr(
            f"{module}.run_remove_routines",
            lambda p: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        monkeypatch.setattr(
            f"{module}.MessageService",
            lambda: type("MS", (), {"set_message": lambda self, m: None})(),
        )

        result = WebClientSetupService("mainsail").remove(
            remove_client=True, remove_client_cfg=False, backup_config=False
        )

        assert result is False