# ======================================================================= #
#  Copyright (C) 2020 - 2026 Dominik Willner <dev.dw-0@proton.me>         #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #

from __future__ import annotations

from typing import Any, List

import pytest
from core.menus.repo_select_menu import RepoSelectMenu


class FakeRepo:
    def __init__(self, url: str = "https://example.com/repo.git", branch: str = "master") -> None:
        self.url = url
        self.branch = branch


@pytest.fixture
def patched_menu(monkeypatch: pytest.MonkeyPatch) -> RepoSelectMenu:
    class FakeSettings:
        class _K:
            repositories: List[Any] = []

        class _M:
            repositories: List[Any] = []

        klipper = _K()
        moonraker = _M()

        def save(self) -> None:
            pass

    monkeypatch.setattr(
        "core.menus.repo_select_menu.KiauhSettings", lambda: FakeSettings()
    )
    monkeypatch.setattr(
        "core.menus.repo_select_menu.run_switch_repo_routine",
        lambda *a, **k: None,
    )

    return RepoSelectMenu("klipper", repos=[FakeRepo()])


class TestRepoSelectMenuConstruction:
    def test_title_for_klipper(self) -> None:
        menu = RepoSelectMenu("klipper", repos=[])
        assert "Klipper" in menu.title

    def test_title_for_moonraker(self) -> None:
        menu = RepoSelectMenu("moonraker", repos=[])
        assert "Moonraker" in menu.title

    def test_options_include_add_remove_back(
        self, patched_menu: RepoSelectMenu
    ) -> None:
        assert "a" in patched_menu.options
        assert "r" in patched_menu.options
        assert "b" in patched_menu.options

    def test_repository_options_are_indexed(
        self, patched_menu: RepoSelectMenu
    ) -> None:
        assert "1" in patched_menu.options


class TestRepoSelectMenuActions:
    def test_select_repository_runs_switch_routine(
        self, patched_menu: RepoSelectMenu, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        called: List[Any] = []
        monkeypatch.setattr(
            "core.menus.repo_select_menu.run_switch_repo_routine",
            lambda name, url, branch: called.append((name, url, branch)),
        )

        repo = FakeRepo("https://github.com/k/klipper.git", "main")
        patched_menu.select_repository(opt_data=repo)

        assert called == [("klipper", "https://github.com/k/klipper.git", "main")]

    def test_remove_repository_does_nothing_when_empty(
        self, patched_menu: RepoSelectMenu, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patched_menu.repos = []
        patched_menu.set_options()
        # should not raise
        patched_menu.remove_repository()
