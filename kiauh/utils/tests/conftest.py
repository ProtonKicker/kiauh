import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def silence_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "print_info",
        "print_ok",
        "print_warn",
        "print_error",
        "print_status",
        "print_dialog",
    ):
        monkeypatch.setattr(f"core.logger.Logger.{name}", lambda *a, **k: None)
