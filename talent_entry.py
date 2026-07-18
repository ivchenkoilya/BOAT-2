import asyncio

import main as core
from about_updates import install_about_updates
from boss_upgrade_v52 import install_boss_upgrade_v52
from raid_assets_v58 import install_raid_assets
from raid_balance_v58 import install_raid_balance_v58
from raid_v59_fix import install_raid_v59_fix
from raid_v59_recovery import install_raid_v59_recovery
from raid_v60 import install_raid_v60
from raid_v60_guard import install_raid_v60_guard
from raid_v61 import install_raid_v61
from raid_v61_safety import install_raid_v61_safety
from talent_expansion import install_expansion
from talent_explanations import install_explanations
from talent_mastery import install_mastery
from talent_mastery_ui import install_mastery_ui
from talent_menu import install_menu
from talent_rules_patch import install_talent_rules
from talent_system import install
from talent_ux import install_ux
from today_types_expansion import install_today_types
from today_types_in_roles import install_types_in_roles
from webapp_inline_fix import install_inline_webapp_fix

install_boss_upgrade_v52(core)
install_raid_assets(core)
install_today_types(core)
install_types_in_roles(core)
install_expansion(core)
install(core)
install_mastery(core)
install_menu(core)
install_ux(core)
install_explanations(core)
install_mastery_ui(core)
# Сначала задаём базовый урон и механику Reality 60, затем Reality 61
# повышает здоровье, усложняет давление и заменяет награды рейда.
install_raid_balance_v58(core)
install_raid_v59_fix(core)
install_raid_v59_recovery(core)
install_raid_v60(core)
install_raid_v60_guard(core)
install_raid_v61(core)
install_raid_v61_safety(core)
install_talent_rules(core)
install_about_updates(core)
install_inline_webapp_fix(core)

# В main.py есть общий обработчик F.text, зарегистрированный раньше расширений.
# Переносим команды древа и мастерства в начало списка, чтобы общий обработчик
# обычного текста не перехватывал их раньше специальных обработчиков.
_priority_names = {
    "cmd_talents",
    "cmd_buffs",
    "cmd_chat_buffs",
    "cmd_builds",
    "cmd_active_talents",
    "cmd_community_tree",
}
_handlers = core.router.message.handlers
_priority = [
    handler
    for handler in _handlers
    if getattr(handler.callback, "__name__", "") in _priority_names
]
_handlers[:] = _priority + [handler for handler in _handlers if handler not in _priority]

if __name__ == "__main__":
    asyncio.run(core.main())
