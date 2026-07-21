# ======================================================================= #
#  Copyright (C) 2020 - 2026 Dominik Willner <dev.dw-0@proton.me>         #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #

from __future__ import annotations

from typing import TypeVar

from components.klipper.klipper import Klipper
from components.moonraker.moonraker import Moonraker
from utils.instance_type import InstanceType


class TestInstanceType:
    def test_is_typevar(self) -> None:
        assert isinstance(InstanceType, TypeVar)

    def test_bound_classes_include_components(self) -> None:
        bound = InstanceType.__constraints__
        assert Klipper in bound
        assert Moonraker in bound
