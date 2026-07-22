from __future__ import annotations

from typing import Any

from government_release_v159 import install_government_release_v159
from government_sold_vote_history_v160 import install_government_sold_vote_history_v160


VERSION = "Reality 160 · Личная история проданных голосов"


def install_government_release_v160(core: Any) -> None:
    if getattr(core, "_government_release_v160_installed", False):
        return
    core._government_release_v160_installed = True
    install_government_release_v159(core)
    install_government_sold_vote_history_v160(core)
    core.GOVERNMENT_VERSION = VERSION
