from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from components.webui_client.base_data import WebClientType


@dataclass
class FakeClientConfig:
    name: str = "mainsail-config"
    display_name: str = "Mainsail-Config"
    config_dir: Path = Path("/tmp/mainsail-config")
    config_filename: str = "mainsail.cfg"
    config_section: str = "include mainsail.cfg"
    repo_url: str = "https://github.com/mainsail-crew/mainsail-config.git"


@dataclass
class FakeWebClient:
    name: str = "mainsail"
    display_name: str = "Mainsail"
    client: WebClientType = WebClientType.MAINSAIL
    client_dir: Path = Path("/tmp/mainsail")
    config_file: Path = Path("/tmp/mainsail/config.json")
    repo_path: str = "mainsail-crew/mainsail"
    nginx_config: Path = Path("/tmp/nginx/mainsail")
    nginx_access_log: Path = Path("/tmp/log/mainsail-access.log")
    nginx_error_log: Path = Path("/tmp/log/mainsail-error.log")
    download_url: str = "https://example.com/mainsail.zip"
    client_config: Any = field(default_factory=FakeClientConfig)


@pytest.fixture
def client() -> FakeWebClient:
    return FakeWebClient()


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Any:
    from core.settings.kiauh_settings import KiauhSettings

    KiauhSettings._KiauhSettings__instance = None
    KiauhSettings._KiauhSettings__initialized = False
    return KiauhSettings()


