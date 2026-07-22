from __future__ import annotations

from typing import Any

from government_election_button_visibility_v158 import install_government_election_button_visibility_v158
from government_release_v157 import install_government_release_v157


VERSION = "Reality 158 · Постоянная кнопка подкупа"


def install_government_release_v158(core: Any) -> None:
    if getattr(core, "_government_release_v158_installed", False):
        return
    core._government_release_v158_installed = True
    install_government_release_v157(core)
    install_government_election_button_visibility_v158(core)
    core.GOVERNMENT_VERSION = VERSION
