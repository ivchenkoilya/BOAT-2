from __future__ import annotations

from typing import Any

from government_release_v164 import install_government_release_v164
from government_treasury_requests_v165 import install_government_treasury_requests_v165

VERSION = "Reality 165 · Запросы госструктур в казну"


def install_government_release_v165(core: Any) -> None:
    if getattr(core, "_government_release_v165_installed", False):
        return
    core._government_release_v165_installed = True
    install_government_release_v164(core)
    install_government_treasury_requests_v165(core)
    core.GOVERNMENT_VERSION = VERSION
