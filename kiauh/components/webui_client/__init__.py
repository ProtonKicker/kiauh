# ======================================================================= #
#  Copyright (C) 2020 - 2026 Dominik Willner <dev.dw-0@proton.me>         #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #

from pathlib import Path
from typing import Callable, Dict

from components.webui_client.base_data import BaseWebClient
from components.webui_client.fluidd_data import FluiddData
from components.webui_client.mainsail_data import MainsailData

MODULE_PATH = Path(__file__).resolve().parent

# Shared registry of supported web clients
CLIENTS: Dict[str, Callable[[], BaseWebClient]] = {
    "mainsail": MainsailData,
    "fluidd": FluiddData,
}
