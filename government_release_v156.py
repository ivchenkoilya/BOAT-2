from __future__ import annotations

from typing import Any

from government_election_message_v156 import install_government_election_message_v156
from government_release_v155 import install_government_release_v155


VERSION = "Reality 156 · Подкуп голосов"


def install_government_release_v156(core: Any) -> None:
    if getattr(core, "_government_release_v156_installed", False):
        return
    core._government_release_v156_installed = True
    install_government_release_v155(core)
    install_government_election_message_v156(core)
    core.GOVERNMENT_VERSION = VERSION
