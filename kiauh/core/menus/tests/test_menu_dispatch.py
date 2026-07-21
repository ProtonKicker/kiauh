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
from core.menus.main_menu import MainMenu


@pytest.fixture
def fake_menu(monkeypatch: pytest.MonkeyPatch):
    """Provide an isolated fake menu class and a call log for each test."""
    calls: List[Dict[str, Any]] = []

    class FakeMenu:
        def __init__(self, **kwargs: Any) -> None:
            calls.append(kwargs)

        def run(self) -> None:
            pass

    yield FakeMenu, calls


@pytest.fixture
def reset_main_menu(monkeypatch: pytest.MonkeyPatch) -> None:
    # silence status fetching during menu construction if any
    monkeypatch.setattr(
        "core.menus.main_menu.MainMenu._fetch_status", lambda self: None
    )


@pytest.mark.parametrize(
    "option_key, target",
    [
        ("1", "InstallMenu"),
        ("2", "UpdateMenu"),
        ("3", "RemoveMenu"),
        ("4", "AdvancedMenu"),
        ("5", "BackupMenu"),
        ("s", "SettingsMenu"),
        ("e", "ExtensionsMenu"),
    ],
)
def test_main_menu_routes_to_submenu(
    option_key: str,
    target: str,
    monkeypatch: pytest.MonkeyPatch,
    reset_main_menu,
    fake_menu,
) -> None:
    fake_menu_cls, calls = fake_menu
    monkeypatch.setattr(f"core.menus.main_menu.{target}", fake_menu_cls)

    menu = MainMenu()
    option = menu.options[option_key]
    option.method(opt_index=option.opt_index, opt_data=option.opt_data)

    assert len(calls) == 1
    assert calls[0].get("previous_menu") is MainMenu


def test_main_menu_quit_exits(monkeypatch: pytest.MonkeyPatch, reset_main_menu) -> None:
    exits: List[int] = []
    monkeypatch.setattr("core.menus.main_menu.sys.exit", lambda code: exits.append(code))

    menu = MainMenu()
    menu.options["q"].method()

    assert exits == [0]
