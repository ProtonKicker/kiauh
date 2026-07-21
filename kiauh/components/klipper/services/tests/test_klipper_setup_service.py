# ======================================================================= #
#  Copyright (C) 2020 - 2026 Dominik Willner <dev.dw-0@proton.me>         #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #

from __future__ import annotations

from typing import Any, Dict, List

import pytest
from components.klipper.services.klipper_setup_service import KlipperSetupService


@pytest.fixture
def reset_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(KlipperSetupService, "_KlipperSetupService__cls_instance", None)


class FakeKlipper:
    def __init__(self, suffix: str = "") -> None:
        self.suffix = suffix
        self.create_calls: List[Any] = []

    def create(self) -> None:
        self.create_calls.append(True)


@pytest.fixture
def patched_install_deps(
    monkeypatch: pytest.MonkeyPatch, reset_service
) -> Dict[str, List[Any]]:
    calls: Dict[str, List[Any]] = {
        "klipper_create": [],
        "enable": [],
        "start": [],
    }

    module = "components.klipper.services.klipper_setup_service"

    def fake_klipper(suffix: str = "") -> FakeKlipper:
        instance = FakeKlipper(suffix)
        calls["klipper_create"].append(instance)
        return instance

    monkeypatch.setattr(f"{module}.Klipper", fake_klipper)
    monkeypatch.setattr(
        f"{module}.InstanceManager.enable",
        staticmethod(lambda instance: calls["enable"].append(instance.suffix)),
    )
    monkeypatch.setattr(
        f"{module}.InstanceManager.start",
        staticmethod(lambda instance: calls["start"].append(instance.suffix)),
    )
    monkeypatch.setattr(f"{module}.git_clone_wrapper", lambda *a, **k: None)
    monkeypatch.setattr(f"{module}.install_klipper_packages", lambda: None)
    monkeypatch.setattr(f"{module}.create_python_venv", lambda *a, **k: True)
    monkeypatch.setattr(f"{module}.install_python_requirements", lambda *a, **k: None)
    monkeypatch.setattr(f"{module}.handle_disruptive_system_packages", lambda: None)
    monkeypatch.setattr(f"{module}.check_user_groups", lambda interactive=True: None)
    monkeypatch.setattr(f"{module}.cmd_sysctl_manage", lambda *a, **k: None)

    return calls


class TestKlipperInstallHeadless:
    def test_installs_single_instance_by_default(
        self, patched_install_deps, monkeypatch
    ) -> None:
        service = KlipperSetupService()
        service.install(interactive=False)

        assert len(patched_install_deps["klipper_create"]) == 1
        assert patched_install_deps["enable"] == [""]
        assert patched_install_deps["start"] == [""]

    def test_installs_multiple_instances_by_count(
        self, patched_install_deps, monkeypatch
    ) -> None:
        service = KlipperSetupService()
        service.install(count=2, interactive=False)

        assert len(patched_install_deps["klipper_create"]) == 2
        assert patched_install_deps["enable"] == ["", ""]
        assert patched_install_deps["start"] == ["", ""]

    def test_installs_with_custom_names(
        self, patched_install_deps, monkeypatch
    ) -> None:
        service = KlipperSetupService()
        service.install(custom_names={0: "a", 1: "b"}, interactive=False)

        assert len(patched_install_deps["klipper_create"]) == 2
        instances = patched_install_deps["klipper_create"]
        assert instances[0].suffix == "a"
        assert instances[1].suffix == "b"


class TestKlipperRemoveHeadless:
    def _make_fake_instance(self, suffix: str = ""):
        Path = __import__("pathlib").Path
        return type(
            "FakeInstance",
            (),
            {
                "suffix": suffix,
                "service_file_path": Path(f"klipper-{suffix}.service"),
                "env_file": Path("/tmp/klipper.env"),
                "base": type("Base", (), {"sysd_dir": Path("/tmp")})(),
            },
        )()

    def _patch_remove_internals(self, monkeypatch, removed):
        module = "components.klipper.services.klipper_setup_service"
        monkeypatch.setattr(
            f"{module}.KlipperSetupService._refresh_state",
            lambda self: None,
        )
        monkeypatch.setattr(
            f"{module}.InstanceManager.remove",
            staticmethod(lambda instance: removed["instances"].append(instance.suffix)),
        )
        monkeypatch.setattr(f"{module}.unit_file_exists", lambda *a, **k: False)
        monkeypatch.setattr(
            f"{module}.run_remove_routines",
            lambda path: removed["paths"].append(str(path)) or True,
        )

    def test_removes_explicit_all_services_and_files(
        self, reset_service, monkeypatch
    ) -> None:
        removed: Dict[str, List[Any]] = {"instances": [], "paths": []}
        self._patch_remove_internals(monkeypatch, removed)
        fake_instance = self._make_fake_instance("")
        service = KlipperSetupService()
        service.klipper_list = [fake_instance]
        service.remove(
            remove_service=True,
            remove_dir=True,
            remove_env=True,
            remove_all=True,
            interactive=False,
        )

        assert removed["instances"] == [""]
        assert any("klipper" in p for p in removed["paths"])

    def test_without_explicit_intent_removes_nothing(
        self, reset_service, monkeypatch
    ) -> None:
        # non-interactive remove with no --all and no --instance must
        # NOT call InstanceManager.remove or run_remove_routines and must
        # refuse with a non-zero (False) result.
        removed: Dict[str, List[Any]] = {"instances": [], "paths": []}
        self._patch_remove_internals(monkeypatch, removed)
        fake_instance = self._make_fake_instance("a")
        service = KlipperSetupService()
        service.klipper_list = [fake_instance]
        result = service.remove(
            remove_service=True,
            remove_dir=False,
            remove_env=False,
            interactive=False,
        )

        assert result is False
        assert removed["instances"] == []
        assert removed["paths"] == []

    def test_with_instance_suffix_removes_only_matching(
        self, reset_service, monkeypatch
    ) -> None:
        removed: Dict[str, List[Any]] = {"instances": [], "paths": []}
        self._patch_remove_internals(monkeypatch, removed)
        service = KlipperSetupService()
        service.klipper_list = [
            self._make_fake_instance("a"),
            self._make_fake_instance("b"),
        ]
        service.remove(
            remove_service=True,
            remove_dir=False,
            remove_env=False,
            instance_suffixes=["a"],
            interactive=False,
        )

        assert removed["instances"] == ["a"]


class TestKlipperUpdateHeadless:
    def test_update_runs_expected_steps(self, reset_service, monkeypatch) -> None:
        module = "components.klipper.services.klipper_setup_service"
        calls: List[str] = []

        monkeypatch.setattr(
            f"{module}.backup_klipper_dir", lambda: calls.append("backup")
        )
        monkeypatch.setattr(
            f"{module}.InstanceManager.stop_all",
            staticmethod(lambda instances: calls.append("stop")),
        )
        monkeypatch.setattr(
            f"{module}.git_pull_wrapper", lambda *a, **k: calls.append("pull")
        )
        monkeypatch.setattr(
            f"{module}.install_klipper_packages", lambda: calls.append("packages")
        )
        monkeypatch.setattr(
            f"{module}.install_python_requirements",
            lambda *a, **k: calls.append("requirements"),
        )
        monkeypatch.setattr(
            f"{module}.InstanceManager.start_all",
            staticmethod(lambda instances: calls.append("start")),
        )

        service = KlipperSetupService()
        service.settings.kiauh.backup_before_update = True
        result = service.update(interactive=False)

        assert result is True
        assert calls == ["backup", "stop", "pull", "packages", "requirements", "start"]

    def test_update_cancelled_by_user_returns_false(
        self, reset_service, monkeypatch
    ) -> None:
        module = "components.klipper.services.klipper_setup_service"
        pulled: List[str] = []
        monkeypatch.setattr(
            f"{module}.git_pull_wrapper", lambda *a, **k: pulled.append("pull")
        )
        monkeypatch.setattr(f"{module}.get_confirm", lambda *a, **k: False)

        service = KlipperSetupService()
        result = service.update(interactive=True)

        assert result is False
        assert pulled == []


class FakeMoonraker:
    def __init__(self, suffix: str = "") -> None:
        self.suffix = suffix


class TestKlipperInteractiveMoonrakerMatch:
    def test_installs_exactly_one_klipper_per_moonraker(
        self, reset_service, patched_install_deps, monkeypatch
    ) -> None:
        module = "components.klipper.services.klipper_setup_service"
        monkeypatch.setattr(
            f"{module}.KlipperSetupService._refresh_state",
            lambda self: None,
        )
        monkeypatch.setattr(
            f"{module}.KlipperSetupService._display_moonraker_info",
            lambda self: True,
        )
        monkeypatch.setattr(f"{module}.get_confirm", lambda *a, **k: True)

        service = KlipperSetupService()
        service.klipper_list = []
        service.moonraker_list = [FakeMoonraker(""), FakeMoonraker("b")]

        result = service.install(interactive=True, create_example_cfg=False)

        assert result is True
        assert len(patched_install_deps["klipper_create"]) == 2
        instances = patched_install_deps["klipper_create"]
        assert instances[0].suffix == ""
        assert instances[1].suffix == "b"

    def test_headless_match_moonraker_skips_dialog(
        self, reset_service, patched_install_deps, monkeypatch
    ) -> None:
        module = "components.klipper.services.klipper_setup_service"
        monkeypatch.setattr(
            f"{module}.KlipperSetupService._refresh_state",
            lambda self: None,
        )
        dialog_calls: List[Any] = []
        monkeypatch.setattr(
            f"{module}.KlipperSetupService._display_moonraker_info",
            lambda self: dialog_calls.append(True) or False,
        )

        service = KlipperSetupService()
        service.klipper_list = []
        service.moonraker_list = [FakeMoonraker("a"), FakeMoonraker("b")]

        result = service.install(match_moonraker=True, interactive=False)

        assert result is True
        assert dialog_calls == []
        assert len(patched_install_deps["klipper_create"]) == 2
        instances = patched_install_deps["klipper_create"]
        assert [i.suffix for i in instances] == ["a", "b"]


class TestKlipperVenvNonDestructive:
    """a headless install must not force-recreate an existing Klipper
    venv. ``__install_deps`` must pass ``force=False`` and ``interactive=False``
    to ``create_python_venv`` so an existing venv is left untouched (no prompt,
    no ``rmtree``)."""

    def test_headless_install_does_not_force_recreate_venv(
        self, reset_service, monkeypatch
    ) -> None:
        module = "components.klipper.services.klipper_setup_service"
        monkeypatch.setattr(
            f"{module}.KlipperSetupService._refresh_state",
            lambda self: None,
        )
        venv_calls: List[Any] = []
        monkeypatch.setattr(
            f"{module}.create_python_venv",
            lambda *a, **k: venv_calls.append(k) or True,
        )
        monkeypatch.setattr(f"{module}.git_clone_wrapper", lambda *a, **k: None)
        monkeypatch.setattr(f"{module}.install_klipper_packages", lambda: None)
        monkeypatch.setattr(
            f"{module}.install_python_requirements", lambda *a, **k: None
        )

        service = KlipperSetupService()
        service.klipper_list = []
        service.install(interactive=False)

        assert venv_calls, "create_python_venv should have been called"
        assert venv_calls[0]["force"] is False
        assert venv_calls[0]["interactive"] is False


class TestCheckUserGroups:
    def test_interactive_mode_prompts_before_adding_user(self, monkeypatch) -> None:
        from components.klipper.klipper_utils import check_user_groups

        monkeypatch.setattr(
            "components.klipper.klipper_utils.get_user_groups", lambda: []
        )
        monkeypatch.setattr(
            "components.klipper.klipper_utils.get_current_user", lambda: "tester"
        )

        prompted: List[str] = []
        monkeypatch.setattr(
            "components.klipper.klipper_utils.get_confirm",
            lambda question, *a, **k: prompted.append(question) or True,
        )
        run_calls: List[List[str]] = []
        monkeypatch.setattr(
            "components.klipper.klipper_utils.run",
            lambda cmd, **kwargs: (
                run_calls.append(cmd) or type("R", (), {"returncode": 0})()
            ),
        )

        check_user_groups(interactive=True)

        assert any("group" in q.lower() for q in prompted)
        assert run_calls

    def test_headless_mode_auto_adds_without_prompt(self, monkeypatch) -> None:
        from components.klipper.klipper_utils import check_user_groups

        monkeypatch.setattr(
            "components.klipper.klipper_utils.get_user_groups", lambda: []
        )
        monkeypatch.setattr(
            "components.klipper.klipper_utils.get_current_user", lambda: "tester"
        )

        monkeypatch.setattr(
            "components.klipper.klipper_utils.get_confirm",
            lambda *a, **k: pytest.fail("should not prompt in headless mode"),
        )
        run_calls: List[List[str]] = []
        monkeypatch.setattr(
            "components.klipper.klipper_utils.run",
            lambda cmd, **kwargs: (
                run_calls.append(cmd) or type("R", (), {"returncode": 0})()
            ),
        )

        check_user_groups(interactive=False)

        assert run_calls


class TestKlipperRemoveInteractiveTui:
    """Exercise the interactive (TUI) remove branch so the message-assembly
    path stays covered: the TUI path must remain unchanged."""

    def _make_fake_instance(self, suffix: str = ""):
        Path = __import__("pathlib").Path
        return type(
            "FakeInstance",
            (),
            {
                "suffix": suffix,
                "service_file_path": Path(f"klipper-{suffix}.service"),
                "env_file": Path("/tmp/klipper.env"),
                "base": type("Base", (), {"sysd_dir": Path("/tmp")})(),
            },
        )()

    def test_interactive_remove_sets_completion_message(
        self, reset_service, monkeypatch
    ) -> None:
        module = "components.klipper.services.klipper_setup_service"
        fake_instance = self._make_fake_instance("a")
        removed: Dict[str, List[Any]] = {"instances": [], "paths": []}

        monkeypatch.setattr(
            f"{module}.KlipperSetupService._refresh_state",
            lambda self: None,
        )
        monkeypatch.setattr(
            f"{module}.KlipperSetupService._get_instances_to_remove",
            lambda self: [fake_instance],
        )
        monkeypatch.setattr(
            f"{module}.InstanceManager.remove",
            staticmethod(lambda instance: removed["instances"].append(instance)),
        )
        monkeypatch.setattr(
            f"{module}.KlipperSetupService._delete_klipper_env_file",
            lambda self, inst: None,
        )
        monkeypatch.setattr(f"{module}.unit_file_exists", lambda *a, **k: False)
        monkeypatch.setattr(
            f"{module}.run_remove_routines",
            lambda path: removed["paths"].append(str(path)) or True,
        )
        set_messages: List[Any] = []
        monkeypatch.setattr(
            f"{module}.MessageService",
            lambda: type(
                "MS", (), {"set_message": lambda self, m: set_messages.append(m)}
            )(),
        )

        service = KlipperSetupService()
        service.klipper_list = [fake_instance]
        result = service.remove(
            remove_service=True, remove_dir=True, remove_env=True, interactive=True
        )

        assert result is True
        assert removed["instances"] == [fake_instance]
        assert set_messages, "TUI remove must set the completion message"
        assert any("klipper-a" in line for line in set_messages[0].text)
