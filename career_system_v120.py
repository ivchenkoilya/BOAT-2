from __future__ import annotations

from typing import Any

from career_boss_v120 import install_career_boss_v120
from career_gambling_guard_v120 import install_career_gambling_guard_v120
from career_impeachment_v120 import install_career_impeachment_v120
from career_inline_v120 import install_career_inline_v120
from career_model_v120 import install_career_model_v120
from career_rewards_v120 import install_career_rewards_v120
from career_special_roles_v120 import install_career_special_roles_v120
from career_tasks_v120 import install_career_tasks_v120
from career_ui_v120 import install_career_ui_v120


def install_career_system_v120(core: Any) -> None:
    if getattr(core, "_career_system_v120_installed", False):
        return
    core._career_system_v120_installed = True
    install_career_model_v120(core)
    install_career_rewards_v120(core)
    install_career_tasks_v120(core)
    install_career_gambling_guard_v120(core)
    install_career_ui_v120(core)
    install_career_inline_v120(core)
    install_career_boss_v120(core)
    install_career_special_roles_v120(core)
    install_career_impeachment_v120(core)
