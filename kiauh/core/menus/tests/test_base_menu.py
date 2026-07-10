from __future__ import annotations

from typing import List, Type

import pytest
from core.menus import FooterType, Option
from core.menus.base_menu import (
    BaseMenu,
    MenuTitleStyle,
    PostInitCaller,
    print_back_footer,
    print_back_help_footer,
    print_blank_footer,
    print_header,
    print_quit_footer,
)


class ConcreteMenu(BaseMenu, metaclass=PostInitCaller):
    title = "Concrete"
    footer_type = FooterType.BACK

    def set_previous_menu(self, previous_menu: Type[BaseMenu] | None) -> None:
        self.previous_menu = previous_menu

    def set_options(self) -> None:
        self.options = {
            "1": Option(method=lambda **k: None),
        }

    def print_menu(self) -> None:
        pass


@pytest.fixture
def concrete(monkeypatch: pytest.MonkeyPatch) -> ConcreteMenu:
    monkeypatch.setattr("core.menus.base_menu.print_header", lambda: None)
    return ConcreteMenu()


class TestBaseMenuHelpers:
    def test_print_header_outputs_banner(self, capsys) -> None:
        print_header()
        captured = capsys.readouterr()
        assert "KIAUH" in captured.out

    def test_print_quit_footer(self, capsys) -> None:
        print_quit_footer()
        assert "Quit" in capsys.readouterr().out

    def test_print_back_footer(self, capsys) -> None:
        print_back_footer()
        assert "Back" in capsys.readouterr().out

    def test_print_back_help_footer(self, capsys) -> None:
        print_back_help_footer()
        out = capsys.readouterr().out
        assert "Back" in out
        assert "Help" in out

    def test_print_blank_footer(self, capsys) -> None:
        print_blank_footer()
        assert "╝" in capsys.readouterr().out


class TestBaseMenuLifecycle:
    def test_direct_instantiation_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            BaseMenu()

    def test_options_include_back_for_back_footer(self, concrete: ConcreteMenu) -> None:
        assert "b" in concrete.options

    def test_go_back_does_nothing_without_previous_menu(
        self, concrete: ConcreteMenu
    ) -> None:
        concrete.previous_menu = None
        # should not raise
        concrete._BaseMenu__go_back()

    def test_exit_calls_system_exit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        exits: List[int] = []
        monkeypatch.setattr("core.menus.base_menu.sys.exit", lambda c: exits.append(c))

        menu = ConcreteMenu()
        menu._BaseMenu__exit()

        assert exits == [0]


class TestMenuTitleStyle:
    def test_style_values(self) -> None:
        assert MenuTitleStyle.PLAIN.value == "plain"
        assert MenuTitleStyle.STYLED.value == "styled"
