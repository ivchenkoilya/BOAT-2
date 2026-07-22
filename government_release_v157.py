from __future__ import annotations

from typing import Any

from government_election_ui_hardfix_v157 import install_government_election_ui_hardfix_v157
from government_release_v156 import install_government_release_v156


VERSION = "Reality 157 · Подкуп голосов без старого кэша"


def install_government_release_v157(core: Any) -> None:
    if getattr(core, "_government_release_v157_installed", False):
        return
    core._government_release_v157_installed = True
    install_government_release_v156(core)
    install_government_election_ui_hardfix_v157(core)
    core.GOVERNMENT_VERSION = VERSION
