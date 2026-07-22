from __future__ import annotations

from typing import Any

from government_election_shadow_safety_v153 import install_government_election_shadow_safety_v153
from government_election_shadow_v153 import install_government_election_shadow_v153
from government_release_v152 import install_government_release_v152


VERSION = "Reality 153 · Теневая избирательная система"


def install_government_release_v153(core: Any) -> None:
    if getattr(core, "_government_release_v153_installed", False):
        return
    core._government_release_v153_installed = True
    install_government_release_v152(core)
    install_government_election_shadow_v153(core)
    install_government_election_shadow_safety_v153(core)
    core.GOVERNMENT_VERSION = VERSION
