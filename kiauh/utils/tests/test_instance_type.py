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
