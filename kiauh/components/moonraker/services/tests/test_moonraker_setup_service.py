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
from components.moonraker.services.moonraker_setup_service import MoonrakerSetupService


class FakeKlipper:
    def __init__(self, suffix: str = "") -> None:
        self.suffix = suffix
        name = f"klipper-{suffix}" if suffix else "klipper"
        self.service_file_path = Path(f"/etc/systemd/system/{name}.service")


class FakeMoonraker:
    def __init__(self, suffix: str = "") -> None:
        self.suffix = suffix
        name = f"moonraker-{suffix}" if suffix else "moonraker"
        self.service_file_path = Path(f"/etc/systemd/system/{name}.service")
        self.env_file = Path(f"/tmp/{name}.env")
        self.port = 7125
        self.base = type("Base", (), {"sysd_dir": Path("/tmp")})()

    def create(self) -> None:
        pass


class FakeKlipperInstanceService:
    def __init__(self, instances: List[FakeKlipper]) -> None:
        self._instances = instances

    def load_instances(self) -> None:
        pass

    def get_all_instances(self) -> List[FakeKlipper]:
        return self._instances


class FakeMoonrakerInstanceService:
    def __init__(self, instances: List[FakeMoonraker]) -> None:
        self._instances = instances
        self.created: List[str] = []

    def load_instances(self) -> None:
        pass

    def get_all_instances(self) -> List[FakeMoonraker]:
        return self._instances

    def create_new_instance(self, suffix: str) -> FakeMoonraker:
        self.created.append(suffix)
        return FakeMoonraker(suffix)

    def get_instance_by_suffix(self, suffix: str) -> FakeMoonraker:
        return FakeMoonraker(suffix)

    def get_instance_port_map(self) -> Dict[str, int]:
        return {}


@pytest.fixture
def reset_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        MoonrakerSetupService, "_MoonrakerSetupService__cls_instance", None
    )


@pytest.fixture
def patch_instance_services(
    monkeypatch: pytest.MonkeyPatch, reset_service
) -> Dict[str, Any]:
    state = {"klipper": [], "moonraker": []}

    def make_kis(*args, **kwargs):
        return FakeKlipperInstanceService(state["klipper"])

    def make_mis(*args, **kwargs):
        return FakeMoonrakerInstanceService(state["moonraker"])

    module = "components.moonraker.services.moonraker_setup_service"
    monkeypatch.setattr(f"{module}.KlipperInstanceService", make_kis)
    monkeypatch.setattr(f"{module}.MoonrakerInstanceService", make_mis)

    return state


class TestMoonrakerInstall:
    def test_installs_for_single_klipper_instance(
        self, patch_instance_services, monkeypatch
    ) -> None:
        patch_instance_services["klipper"] = [FakeKlipper("")]

        setup_calls: List[Any] = []
        module = "components.moonraker.services.moonraker_setup_service"
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._check_requirements",
            lambda self, kl: True,
        )
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._run_setup",
            lambda self, instances, cfg, interactive=True: setup_calls.append((
                instances,
                cfg,
                interactive,
            )),
        )
        monkeypatch.setattr(f"{module}.get_confirm", lambda *a, **k: True)

        service = MoonrakerSetupService()
        service.install()

        assert len(setup_calls) == 1
        instances, cfg, _interactive = setup_calls[0]
        assert len(instances) == 1
        assert instances[0].suffix == ""
        assert cfg is True

    def test_installs_for_selected_klipper_instance(
        self, patch_instance_services, monkeypatch
    ) -> None:
        patch_instance_services["klipper"] = [FakeKlipper("a"), FakeKlipper("b")]

        setup_calls: List[Any] = []
        module = "components.moonraker.services.moonraker_setup_service"
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._check_requirements",
            lambda self, kl: True,
        )
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._run_setup",
            lambda self, instances, cfg, interactive=True: setup_calls.append((
                instances,
                cfg,
                interactive,
            )),
        )
        monkeypatch.setattr(f"{module}.get_selection_input", lambda *a, **k: "1")
        monkeypatch.setattr(f"{module}.get_confirm", lambda *a, **k: True)

        service = MoonrakerSetupService()
        service.install()

        assert len(setup_calls) == 1
        assert setup_calls[0][0][0].suffix == "a"


class TestMoonrakerUpdate:
    def test_update_runs_expected_steps(
        self, patch_instance_services, monkeypatch
    ) -> None:
        patch_instance_services["moonraker"] = [FakeMoonraker("")]

        module = "components.moonraker.services.moonraker_setup_service"
        calls: List[str] = []

        monkeypatch.setattr(f"{module}.get_confirm", lambda *a, **k: True)
        monkeypatch.setattr(
            f"{module}.backup_moonraker_dir", lambda: calls.append("backup")
        )
        monkeypatch.setattr(
            f"{module}.InstanceManager.stop_all",
            staticmethod(lambda instances: calls.append("stop")),
        )
        monkeypatch.setattr(
            f"{module}.git_pull_wrapper", lambda *a, **k: calls.append("pull")
        )
        monkeypatch.setattr(
            f"{module}.install_moonraker_packages", lambda: calls.append("packages")
        )
        monkeypatch.setattr(
            f"{module}.install_python_requirements",
            lambda *a, **k: calls.append("requirements"),
        )
        monkeypatch.setattr(
            f"{module}.InstanceManager.start_all",
            staticmethod(lambda instances: calls.append("start")),
        )

        service = MoonrakerSetupService()
        service.settings.kiauh.backup_before_update = True
        service.update()

        assert calls == ["backup", "stop", "pull", "packages", "requirements", "start"]


class TestMoonrakerRemove:
    def test_removes_selected_instance(
        self, patch_instance_services, monkeypatch
    ) -> None:
        patch_instance_services["moonraker"] = [FakeMoonraker("")]

        module = "components.moonraker.services.moonraker_setup_service"
        removed: Dict[str, List[Any]] = {"instances": [], "paths": []}

        fake_instance = FakeMoonraker("")
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._get_instances_to_remove",
            lambda self: [fake_instance],
        )
        monkeypatch.setattr(
            f"{module}.InstanceManager.remove",
            staticmethod(lambda instance: removed["instances"].append(instance)),
        )
        monkeypatch.setattr(f"{module}.unit_file_exists", lambda *a, **k: False)
        monkeypatch.setattr(f"{module}.remove_polkit_rules", lambda: True)
        monkeypatch.setattr(
            f"{module}.run_remove_routines",
            lambda path: removed["paths"].append(str(path)) or True,
        )

        service = MoonrakerSetupService()
        service.remove(
            remove_service=True, remove_dir=True, remove_env=True, remove_polkit=True
        )

        assert removed["instances"] == [fake_instance]
        assert any("moonraker" in p for p in removed["paths"])


class TestMoonrakerInstallHeadless:
    def test_headless_install_does_not_show_success_dialog(
        self, patch_instance_services, monkeypatch
    ) -> None:
        patch_instance_services["klipper"] = [FakeKlipper("")]

        module = "components.moonraker.services.moonraker_setup_service"
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._check_requirements",
            lambda self, kl: True,
        )
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._install_deps",
            lambda self, interactive: None,
        )
        monkeypatch.setattr(f"{module}.get_confirm", lambda *a, **k: True)
        monkeypatch.setattr(f"{module}.cmd_sysctl_service", lambda *a, **k: None)
        monkeypatch.setattr(f"{module}.cmd_sysctl_manage", lambda *a, **k: None)
        monkeypatch.setattr(
            f"{module}.check_install_dependencies", lambda *a, **k: None
        )
        monkeypatch.setattr(f"{module}.get_ipv4_addr", lambda: "127.0.0.1")
        monkeypatch.setattr(
            f"{module}.Logger.print_dialog",
            lambda *a, **k: pytest.fail("should not show dialog in headless install"),
        )
        errors: List[str] = []
        monkeypatch.setattr(
            f"{module}.Logger.print_error",
            lambda msg, *a, **k: errors.append(str(msg)),
        )

        service = MoonrakerSetupService()
        result = service.install(interactive=False)

        assert errors == [], f"unexpected errors: {errors}"
        assert result is True

    def test_installs_with_explicit_klipper_suffixes(
        self, patch_instance_services, monkeypatch
    ) -> None:
        patch_instance_services["klipper"] = [FakeKlipper("a"), FakeKlipper("b")]

        setup_calls: List[Any] = []
        module = "components.moonraker.services.moonraker_setup_service"
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._check_requirements",
            lambda self, kl: True,
        )
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._run_setup",
            lambda self, instances, cfg, interactive=True: setup_calls.append((
                instances,
                cfg,
                interactive,
            )),
        )

        service = MoonrakerSetupService()
        result = service.install(klipper_suffixes=["a", "b"], interactive=False)

        assert result is True
        assert len(setup_calls) == 1
        instances, cfg, interactive = setup_calls[0]
        assert [i.suffix for i in instances] == ["a", "b"]
        assert cfg is False
        assert interactive is False

    def test_installs_for_all_klipper_instances_when_non_interactive(
        self, patch_instance_services, monkeypatch
    ) -> None:
        patch_instance_services["klipper"] = [FakeKlipper("a"), FakeKlipper("b")]

        setup_calls: List[Any] = []
        module = "components.moonraker.services.moonraker_setup_service"
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._check_requirements",
            lambda self, kl: True,
        )
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._run_setup",
            lambda self, instances, cfg, interactive=True: setup_calls.append((
                instances,
                cfg,
                interactive,
            )),
        )

        service = MoonrakerSetupService()
        result = service.install(interactive=False)

        assert result is True
        assert [i.suffix for i in setup_calls[0][0]] == ["a", "b"]
        assert setup_calls[0][2] is False

    def test_returns_false_when_klipper_is_missing(
        self, patch_instance_services, monkeypatch
    ) -> None:
        patch_instance_services["klipper"] = []

        service = MoonrakerSetupService()
        result = service.install(interactive=False)

        assert result is False

    def test_returns_false_when_setup_raises(
        self, patch_instance_services, monkeypatch
    ) -> None:
        patch_instance_services["klipper"] = [FakeKlipper("")]

        module = "components.moonraker.services.moonraker_setup_service"
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._check_requirements",
            lambda self, kl: True,
        )
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._run_setup",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        service = MoonrakerSetupService()
        result = service.install(interactive=False)

        assert result is False


class TestMoonrakerUpdateHeadless:
    def test_update_runs_without_confirmation(
        self, patch_instance_services, monkeypatch
    ) -> None:
        patch_instance_services["moonraker"] = [FakeMoonraker("")]

        module = "components.moonraker.services.moonraker_setup_service"
        calls: List[str] = []

        monkeypatch.setattr(
            f"{module}.backup_moonraker_dir", lambda: calls.append("backup")
        )
        monkeypatch.setattr(
            f"{module}.InstanceManager.stop_all",
            staticmethod(lambda instances: calls.append("stop")),
        )
        monkeypatch.setattr(
            f"{module}.git_pull_wrapper", lambda *a, **k: calls.append("pull")
        )
        monkeypatch.setattr(
            f"{module}.install_moonraker_packages", lambda: calls.append("packages")
        )
        monkeypatch.setattr(
            f"{module}.install_python_requirements",
            lambda *a, **k: calls.append("requirements"),
        )
        monkeypatch.setattr(
            f"{module}.InstanceManager.start_all",
            staticmethod(lambda instances: calls.append("start")),
        )

        service = MoonrakerSetupService()
        service.settings.kiauh.backup_before_update = True
        service.update(interactive=False)

        assert calls == ["backup", "stop", "pull", "packages", "requirements", "start"]

    def test_update_cancelled_by_user_returns_false(
        self, patch_instance_services, monkeypatch
    ) -> None:
        patch_instance_services["moonraker"] = [FakeMoonraker("")]
        pulled: List[str] = []
        module = "components.moonraker.services.moonraker_setup_service"
        monkeypatch.setattr(
            f"{module}.git_pull_wrapper", lambda *a, **k: pulled.append("pull")
        )
        monkeypatch.setattr(f"{module}.get_confirm", lambda *a, **k: False)

        service = MoonrakerSetupService()
        result = service.update(interactive=True)

        assert result is False
        assert pulled == []


class TestMoonrakerPolkitBehavior:
    def test_install_polkit_failure_logs_error_and_continues(
        self, patch_instance_services, monkeypatch
    ) -> None:
        module = "components.moonraker.services.moonraker_setup_service"

        class FakeResult:
            returncode = 1
            stderr = "polkit install failed"

        monkeypatch.setattr(f"{module}.run", lambda *a, **k: FakeResult())
        monkeypatch.setattr(
            f"{module}.check_file_exist", lambda p, follow_symlinks=False: False
        )

        error_messages: List[str] = []
        monkeypatch.setattr(
            f"{module}.Logger.print_error",
            lambda msg, *a, **k: error_messages.append(str(msg)),
        )

        service = MoonrakerSetupService()
        service._install_polkit()

        assert any("polkit" in m.lower() for m in error_messages)

    def test_install_succeeds_when_polkit_rules_fail(
        self, patch_instance_services, monkeypatch
    ) -> None:
        patch_instance_services["klipper"] = [FakeKlipper("")]

        module = "components.moonraker.services.moonraker_setup_service"
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._check_requirements",
            lambda self, kl: True,
        )

        setup_calls: List[Any] = []
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._run_setup",
            lambda self, instances, cfg, interactive=True: setup_calls.append((
                instances,
                cfg,
                interactive,
            )),
        )

        class FakeResult:
            returncode = 1
            stderr = "polkit install failed"

        monkeypatch.setattr(f"{module}.run", lambda *a, **k: FakeResult())
        monkeypatch.setattr(
            f"{module}.check_file_exist", lambda p, follow_symlinks=False: False
        )
        monkeypatch.setattr(f"{module}.get_confirm", lambda *a, **k: True)

        def fake_install_deps(self, interactive: bool = True) -> None:
            self._install_polkit()

        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._install_deps",
            fake_install_deps,
        )

        service = MoonrakerSetupService()
        result = service.install()

        assert result is True
        assert len(setup_calls) == 1


class TestMoonrakerRemoveHeadless:
    def _patch_remove_internals(self, monkeypatch, removed):
        module = "components.moonraker.services.moonraker_setup_service"
        monkeypatch.setattr(
            f"{module}.InstanceManager.remove",
            staticmethod(lambda instance: removed["instances"].append(instance.suffix)),
        )
        monkeypatch.setattr(
            f"{module}.MoonrakerSetupService._refresh_state",
            lambda self: None,
        )
        monkeypatch.setattr(f"{module}.unit_file_exists", lambda *a, **k: False)
        monkeypatch.setattr(
            f"{module}.remove_polkit_rules",
            lambda: removed["paths"].append("polkit") or True,
        )
        monkeypatch.setattr(
            f"{module}.run_remove_routines",
            lambda path: removed["paths"].append(str(path)) or True,
        )

    def test_removes_all_instances_when_explicit_all(
        self, patch_instance_services, monkeypatch
    ) -> None:
        patch_instance_services["moonraker"] = [FakeMoonraker("a"), FakeMoonraker("b")]

        removed: Dict[str, List[Any]] = {"instances": [], "paths": []}
        self._patch_remove_internals(monkeypatch, removed)

        service = MoonrakerSetupService()
        service.remove(
            remove_service=True,
            remove_dir=True,
            remove_env=True,
            remove_polkit=True,
            remove_all=True,
            interactive=False,
        )

        assert set(removed["instances"]) == {"a", "b"}
        assert "polkit" in removed["paths"]

    def test_without_explicit_intent_removes_nothing(
        self, patch_instance_services, monkeypatch
    ) -> None:
        # non-interactive remove with no --all / --instance must not destroy any instance and must refuse.
        patch_instance_services["moonraker"] = [FakeMoonraker("a"), FakeMoonraker("b")]

        removed: Dict[str, List[Any]] = {"instances": [], "paths": []}
        self._patch_remove_internals(monkeypatch, removed)

        service = MoonrakerSetupService()
        result = service.remove(
            remove_service=True,
            remove_dir=False,
            remove_env=False,
            remove_polkit=False,
            interactive=False,
        )

        assert result is False
        assert removed["instances"] == []
        assert removed["paths"] == []

    def test_with_instance_suffix_removes_only_matching(
        self, patch_instance_services, monkeypatch
    ) -> None:
        patch_instance_services["moonraker"] = [
            FakeMoonraker("a"),
            FakeMoonraker("b"),
        ]

        removed: Dict[str, List[Any]] = {"instances": [], "paths": []}
        self._patch_remove_internals(monkeypatch, removed)

        service = MoonrakerSetupService()
        service.remove(
            remove_service=True,
            remove_dir=False,
            remove_env=False,
            remove_polkit=False,
            instance_suffixes=["a"],
            interactive=False,
        )

        assert removed["instances"] == ["a"]
