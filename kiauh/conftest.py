# ======================================================================= #
#  Copyright (C) 2020 - 2026 Dominik Willner <dev.dw-0@proton.me>         #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def silence_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Suppress logger output so tests produce clean, assertion-focused output."""
    for name in (
        "print_info",
        "print_ok",
        "print_warn",
        "print_error",
        "print_status",
        "print_dialog",
    ):
        monkeypatch.setattr(f"core.logger.Logger.{name}", lambda *a, **k: None)
