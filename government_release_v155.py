from __future__ import annotations

from typing import Any

from government_election_bribe_label_v155 import install_government_election_bribe_label_v155
from government_release_v154 import install_government_release_v154


VERSION = "Reality 155 · Подкуп голосов"


def install_government_release_v155(core: Any) -> None:
    if getattr(core, "_government_release_v155_installed", False):
        return
    core._government_release_v155_installed = True
    install_government_release_v154(core)
    install_government_election_bribe_label_v155(core)
    core.GOVERNMENT_VERSION = VERSION
