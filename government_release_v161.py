from __future__ import annotations

from typing import Any

from government_realtime_guard_v161 import install_government_realtime_guard_v161
from government_release_v160 import install_government_release_v160


VERSION = "Reality 161 · Защита казны и живое обновление"


def install_government_release_v161(core: Any) -> None:
    if getattr(core, "_government_release_v161_installed", False):
        return
    core._government_release_v161_installed = True
    install_government_release_v160(core)
    install_government_realtime_guard_v161(core)
    core.GOVERNMENT_VERSION = VERSION
