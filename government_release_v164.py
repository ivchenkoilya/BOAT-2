from __future__ import annotations

from typing import Any

from government_release_v163 import install_government_release_v163
from government_treasury_management_v164 import install_government_treasury_management_v164


VERSION = "Reality 164 · Президентское управление казной"


def install_government_release_v164(core: Any) -> None:
    if getattr(core, "_government_release_v164_installed", False):
        return
    core._government_release_v164_installed = True
    install_government_release_v163(core)
    install_government_treasury_management_v164(core)
    core.GOVERNMENT_VERSION = VERSION
