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
from extensions.base_extension import BaseExtension


class ConcreteExtension(BaseExtension):
    def install_extension(self, **kwargs) -> None:
        pass

    def remove_extension(self, **kwargs) -> None:
        pass


class TestBaseExtension:
    def test_concrete_subclass_can_be_instantiated(self) -> None:
        ext = ConcreteExtension({"name": "test"})
        assert ext.metadata["name"] == "test"

    def test_update_extension_not_implemented(self) -> None:
        ext = ConcreteExtension({"name": "test"})
        with pytest.raises(NotImplementedError):
            ext.update_extension()

    def test_abstract_methods_enforced(self) -> None:
        class PartialExtension(BaseExtension):
            def install_extension(self, **kwargs) -> None:
                pass

        with pytest.raises(TypeError):
            PartialExtension({"name": "test"})
