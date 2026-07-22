from __future__ import annotations

from typing import Any

from government_mandate_revocation_v152 import install_government_mandate_revocation_v152
from government_release_v151 import install_government_release_v151


VERSION = "Reality 152 · Причины аннулирования мандатов"


def install_government_release_v152(core: Any) -> None:
    if getattr(core, "_government_release_v152_installed", False):
        return
    core._government_release_v152_installed = True
    install_government_release_v151(core)
    install_government_mandate_revocation_v152(core)
    core.GOVERNMENT_VERSION = VERSION
