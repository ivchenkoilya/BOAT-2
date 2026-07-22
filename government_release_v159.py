from __future__ import annotations

from typing import Any

from government_mandate_live_refresh_v159 import install_government_mandate_live_refresh_v159
from government_release_v158 import install_government_release_v158


VERSION = "Reality 159 · Живой реестр мандатов"


def install_government_release_v159(core: Any) -> None:
    if getattr(core, "_government_release_v159_installed", False):
        return
    core._government_release_v159_installed = True
    install_government_release_v158(core)
    install_government_mandate_live_refresh_v159(core)
    core.GOVERNMENT_VERSION = VERSION
