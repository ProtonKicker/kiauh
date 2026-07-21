# ======================================================================= #
#  Copyright (C) 2020 - 2026 Dominik Willner <dev.dw-0@proton.me>         #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #

from __future__ import annotations

import time

from core.spinner import Spinner


class TestSpinnerLifecycle:
    def test_spinner_animates_while_running(self, capsys) -> None:
        spinner = Spinner(message="Working", interval=0.01)
        spinner.start()
        time.sleep(0.05)
        spinner.stop()

        out = capsys.readouterr().out
        assert "Working ..." in out

    def test_spinner_clears_line_on_stop(self, capsys) -> None:
        spinner = Spinner(message="Done", interval=0.01)
        spinner.start()
        time.sleep(0.03)
        spinner.stop()

        out = capsys.readouterr().out
        # the final clear writes spaces and returns to column 0
        assert out.rstrip(" ").endswith("\r")


class TestSpinnerPause:
    def test_pause_sets_pause_event_and_clears_line(self, capsys) -> None:
        spinner = Spinner(message="Hold", interval=0.01)
        spinner.start()
        time.sleep(0.03)

        spinner.pause()

        assert spinner._pause_event.is_set()
        out = capsys.readouterr().out
        # the pause write must be a cleared line ending at column 0
        assert out.rstrip(" ").endswith("\r")

        spinner.resume()
        assert not spinner._pause_event.is_set()
        spinner.stop()

    def test_pause_while_already_paused_is_safe(self) -> None:
        spinner = Spinner(message="Hold", interval=0.01)
        spinner.start()
        spinner.pause()
        # pausing again must not deadlock or raise
        spinner.pause()
        spinner.resume()
        spinner.stop()

    def test_stop_while_paused_joins_cleanly(self) -> None:
        spinner = Spinner(message="Stop", interval=0.01)
        spinner.start()
        spinner.pause()
        spinner.stop()
        assert not spinner._thread.is_alive()


class TestSpinnerRegistry:
    def test_spinner_thread_is_daemon(self) -> None:
        spinner = Spinner(message="Daemon", interval=0.01)
        spinner.start()
        assert spinner._thread.daemon
        spinner.stop()

    def test_stop_all_stops_active_spinners(self) -> None:
        spinner1 = Spinner(message="One", interval=0.01)
        spinner2 = Spinner(message="Two", interval=0.01)
        spinner1.start()
        spinner2.start()

        Spinner.stop_all()

        assert not spinner1._thread.is_alive()
        assert not spinner2._thread.is_alive()
        assert spinner1 not in Spinner._registry
        assert spinner2 not in Spinner._registry

    def test_stop_all_is_safe_when_registry_empty(self) -> None:
        Spinner.stop_all()
        assert Spinner._registry == set()

    def test_stop_is_idempotent(self) -> None:
        spinner = Spinner(message="Again", interval=0.01)
        spinner.start()
        spinner.stop()
        spinner.stop()
        assert spinner not in Spinner._registry
        assert not spinner._thread.is_alive()
