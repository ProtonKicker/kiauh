from __future__ import annotations

from pathlib import Path

from utils.config_utils import (
    add_config_section,
    add_config_section_at_top,
    remove_config_section,
)


class _FakeInstance:
    def __init__(self, cfg_file: Path):
        self.cfg_file = cfg_file


def _write_cfg(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


class TestAddConfigSection:
    def test_creates_section_and_options(self, tmp_path: Path) -> None:
        cfg = tmp_path / "printer.cfg"
        _write_cfg(cfg, "[existing]\noption: value\n")
        instance = _FakeInstance(cfg)

        add_config_section(
            "new_section",
            [instance],
            options=[("opt1", "val1"), ("opt2", ["line1", "line2"])],
        )

        text = cfg.read_text(encoding="utf-8")
        assert "[new_section]" in text
        assert "opt1: val1" in text
        assert "    line1" in text
        assert "    line2" in text

    def test_skips_existing_section(self, tmp_path: Path) -> None:
        cfg = tmp_path / "printer.cfg"
        _write_cfg(cfg, "[section]\noption: value\n")
        instance = _FakeInstance(cfg)

        add_config_section("section", [instance])

        text = cfg.read_text(encoding="utf-8")
        assert text.count("[section]") == 1

    def test_warns_when_file_missing(self, tmp_path: Path) -> None:
        cfg = tmp_path / "missing.cfg"
        instance = _FakeInstance(cfg)

        add_config_section("section", [instance])

        assert not cfg.exists()


class TestAddConfigSectionAtTop:
    def test_prepends_section(self, tmp_path: Path) -> None:
        cfg = tmp_path / "printer.cfg"
        original = "[old]\noption: value\n"
        _write_cfg(cfg, original)
        instance = _FakeInstance(cfg)

        add_config_section_at_top("top_section", [instance])

        text = cfg.read_text(encoding="utf-8")
        lines = text.splitlines()
        assert lines[0] == "[top_section]"
        assert "[old]" in text
        assert text.endswith("\n")


class TestRemoveConfigSection:
    def test_removes_existing(self, tmp_path: Path) -> None:
        cfg = tmp_path / "printer.cfg"
        _write_cfg(cfg, "[keep]\noption: 1\n[drop]\noption: 2\n")
        instance = _FakeInstance(cfg)

        removed = remove_config_section("drop", [instance])

        assert removed == [instance]
        text = cfg.read_text(encoding="utf-8")
        assert "[drop]" not in text
        assert "[keep]" in text

    def test_skips_missing_section(self, tmp_path: Path) -> None:
        cfg = tmp_path / "printer.cfg"
        _write_cfg(cfg, "[keep]\noption: 1\n")
        instance = _FakeInstance(cfg)

        removed = remove_config_section("missing", [instance])

        assert removed == []
        assert cfg.read_text(encoding="utf-8") == "[keep]\noption: 1\n"

    def test_warns_when_file_missing(self, tmp_path: Path) -> None:
        cfg = tmp_path / "missing.cfg"
        instance = _FakeInstance(cfg)

        removed = remove_config_section("section", [instance])

        assert removed == []
