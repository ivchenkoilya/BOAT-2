from __future__ import annotations

from typing import Any

from government_election_offer_duration_v154 import install_government_election_offer_duration_v154
from government_release_v153 import install_government_release_v153


VERSION = "Reality 154 · Предложения до конца выборов"


def install_government_release_v154(core: Any) -> None:
    if getattr(core, "_government_release_v154_installed", False):
        return
    core._government_release_v154_installed = True
    install_government_release_v153(core)
    install_government_election_offer_duration_v154(core)
    core.GOVERNMENT_VERSION = VERSION
