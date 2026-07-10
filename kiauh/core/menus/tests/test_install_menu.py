# ======================================================================= #
#  Copyright (C) 2020 - 2026 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

from typing import Any, List

import core.menus.install_menu as install_menu_module
import pytest
from core.menus.install_menu import InstallMenu


@pytest.fixture
def menu(monkeypatch: pytest.MonkeyPatch) -> InstallMenu:
    # Avoid the heavyweight singleton setup services loading real instances.
    monkeypatch.setattr(install_menu_module, "KlipperSetupService", lambda: object())
    monkeypatch.setattr(install_menu_module, "MoonrakerSetupService", lambda: object())
    return InstallMenu()


def _fake_data(client_dir_exists: bool) -> Any:
    return type(
        "Client",
        (),
        {
            "client_dir": type(
                "P",
                (),
                {"exists": lambda self: client_dir_exists},
            )(),
        },
    )()


class TestInstallMenuWiring:
    def test_options_expose_every_install_entry(self, menu: InstallMenu) -> None:
        for key in ("1", "2", "3", "4", "5", "6", "7", "8"):
            assert key in menu.options

    def test_set_previous_menu_defaults_to_main_menu(
        self, menu: InstallMenu, monkeypatch
    ) -> None:
        # importing MainMenu here avoids an import cycle in the module under test
        from core.menus.main_menu import MainMenu

        menu.set_previous_menu(None)
        assert menu.previous_menu is MainMenu

    def test_install_mainsail_when_absent_calls_setup_service(
        self, menu: InstallMenu, monkeypatch
    ) -> None:
        calls: List[Any] = []
        monkeypatch.setattr(
            install_menu_module, "MainsailData", lambda: _fake_data(False)
        )
        monkeypatch.setattr(
            install_menu_module,
            "WebClientSetupService",
            lambda name: type(
                "S", (), {"install": lambda self: calls.append(name) or True}
            )(),
        )

        menu.install_mainsail()

        assert calls == ["mainsail"]

    def test_install_mainsail_when_present_opens_client_install_menu(
        self, menu: InstallMenu, monkeypatch
    ) -> None:
        opened: List[Any] = []
        monkeypatch.setattr(
            install_menu_module, "MainsailData", lambda: _fake_data(True)
        )

        class _FakeClientInstallMenu:
            def __init__(self, client, previous_menu) -> None:
                opened.append((client, previous_menu))

            def run(self) -> None:
                pass

        monkeypatch.setattr(
            install_menu_module, "ClientInstallMenu", _FakeClientInstallMenu
        )

        menu.install_mainsail()

        assert len(opened) == 1

    def test_install_fluidd_when_absent_calls_setup_service(
        self, menu: InstallMenu, monkeypatch
    ) -> None:
        calls: List[Any] = []
        monkeypatch.setattr(
            install_menu_module, "FluiddData", lambda: _fake_data(False)
        )
        monkeypatch.setattr(
            install_menu_module,
            "WebClientSetupService",
            lambda name: type(
                "S", (), {"install": lambda self: calls.append(name) or True}
            )(),
        )

        menu.install_fluidd()

        assert calls == ["fluidd"]

    def test_install_mainsail_config_delegates_to_config_service(
        self, menu: InstallMenu, monkeypatch
    ) -> None:
        calls: List[Any] = []
        monkeypatch.setattr(
            install_menu_module,
            "WebClientConfigSetupService",
            lambda name: type(
                "S", (), {"install": lambda self: calls.append(name) or True}
            )(),
        )

        menu.install_mainsail_config()

        assert calls == ["mainsail"]

    def test_install_fluidd_config_delegates_to_config_service(
        self, menu: InstallMenu, monkeypatch
    ) -> None:
        calls: List[Any] = []
        monkeypatch.setattr(
            install_menu_module,
            "WebClientConfigSetupService",
            lambda name: type(
                "S", (), {"install": lambda self: calls.append(name) or True}
            )(),
        )

        menu.install_fluidd_config()

        assert calls == ["fluidd"]

    def test_install_klipperscreen_and_crowsnest_delegates(
        self, menu: InstallMenu, monkeypatch
    ) -> None:
        calls: List[str] = []
        monkeypatch.setattr(
            install_menu_module, "install_klipperscreen", lambda: calls.append("ks")
        )
        monkeypatch.setattr(
            install_menu_module, "install_crowsnest", lambda: calls.append("cn")
        )

        menu.install_klipperscreen()
        menu.install_crowsnest()

        assert calls == ["ks", "cn"]