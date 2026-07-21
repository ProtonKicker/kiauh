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
from core.services.message_service import Message, MessageService
from core.types.color import Color


@pytest.fixture
def reset_message_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MessageService, "_MessageService__cls_instance", None)


class TestMessage:
    def test_default_message_is_empty(self) -> None:
        msg = Message()
        assert msg.title == ""
        assert msg.text == []
        assert msg.color == Color.WHITE
        assert msg.centered is False


class TestMessageService:
    def test_singleton_instance(self, reset_message_service) -> None:
        a = MessageService()
        b = MessageService()
        assert a is b

    def test_set_and_display_message(
        self, reset_message_service, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: List[Any] = []
        monkeypatch.setattr(
            "core.services.message_service.Logger.print_dialog",
            lambda **kwargs: calls.append(kwargs),
        )

        svc = MessageService()
        msg = Message(title="Hello", text=["world"], color=Color.GREEN)
        svc.set_message(msg)
        svc.display_message()

        assert calls[0]["custom_title"] == "Hello"
        assert calls[0]["content"] == ["world"]

    def test_display_without_message_does_nothing(
        self, reset_message_service, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: List[Any] = []
        monkeypatch.setattr(
            "core.services.message_service.Logger.print_dialog",
            lambda **kwargs: calls.append(kwargs),
        )

        svc = MessageService()
        svc.display_message()

        # no message set, so print_dialog should not have been invoked
        assert calls == []
        assert svc._MessageService__message is None
