from __future__ import annotations

from typing import Any

from government_release_v162 import install_government_release_v162
from government_theft_quest_v163 import install_government_theft_quest_v163
from government_theft_quest_v163_puzzles import install_theft_quest_puzzles_v163


VERSION = "Reality 163 · Детективное расследование казны"


def install_government_release_v163(core: Any) -> None:
    if getattr(core, "_government_release_v163_installed", False):
        return
    core._government_release_v163_installed = True
    install_government_release_v162(core)
    install_theft_quest_puzzles_v163(core)
    install_government_theft_quest_v163(core)
    core.GOVERNMENT_VERSION = VERSION
