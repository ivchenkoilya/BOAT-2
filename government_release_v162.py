from __future__ import annotations

from typing import Any

from government_investigation_counter_v162 import install_government_investigation_counter_v162
from government_release_v161 import install_government_release_v161


VERSION = "Reality 162 · Точный счётчик расследований"


def install_government_release_v162(core: Any) -> None:
    if getattr(core, "_government_release_v162_installed", False):
        return
    core._government_release_v162_installed = True
    install_government_release_v161(core)
    install_government_investigation_counter_v162(core)
    core.GOVERNMENT_VERSION = VERSION
