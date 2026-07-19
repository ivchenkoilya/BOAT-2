import asyncio

import main as core
from about_admin_v76 import install_about_admin_v76
from about_balance_v74 import install_about_balance_v74
from about_bonus_v73 import install_about_bonus_v73
from about_compact_v72 import install_about_compact_v72
from about_games_v75 import install_about_games_v75
from about_optimizer_v69 import install_about_optimizer_v69
from about_optimizer_v70 import install_about_optimizer_v70
from about_optimizer_v71 import install_about_optimizer_v71
from about_recommendations_v67 import install_about_recommendations_v67
from about_recommendations_v68 import install_about_recommendations_v68
from about_updates import install_about_updates
from admin_attempts_hotfix_v92 import install_admin_attempts_hotfix_v92
from admin_center_v76 import install_admin_center_v76
from admin_night_hunter_v95 import install_admin_night_hunter_v95
from admin_open_v89 import install_admin_open_v89
from admin_webapp_v62 import install_admin_webapp_v62
from boss_upgrade_v52 import install_boss_upgrade_v52
from economy_fate_ui_v74 import install_economy_fate_ui_v74
from game_center_runtime_v75 import install_game_center_runtime_v75
from heist_asset_routes_v78 import install_heist_asset_routes_v78
from heist_reward_v91 import install_heist_reward_v91
from hero_day_v77 import install_hero_day_v77
from influence_balance_v87 import install_influence_balance_v87
from influence_reward_v88 import install_influence_reward_v88
from knowledge_economy_v85 import install_knowledge_economy_v85
from night_hunter_v93 import install_night_hunter_v93
from raid_assets_v58 import install_raid_assets
from raid_balance_v58 import install_raid_balance_v58
from raid_v59_fix import install_raid_v59_fix
from raid_v59_recovery import install_raid_v59_recovery
from raid_v60 import install_raid_v60
from raid_v60_guard import install_raid_v60_guard
from raid_v61 import install_raid_v61
from raid_v61_safety import install_raid_v61_safety
from raid_v64_direct_tree import install_raid_v64_direct_tree
from raid_v65_balance import install_raid_v65_balance
from talent_bonus_display_v73 import install_talent_bonus_display_v73
from talent_expansion import install_expansion
from talent_explanations import install_explanations
from talent_improvements_v66 import install_talent_improvements_v66
from talent_mastery import install_mastery
from talent_mastery_ui import install_mastery_ui
from talent_menu import install_menu
from talent_optimizer_v69 import install_talent_optimizer_v69
from talent_optimizer_v70 import install_talent_optimizer_v70
from talent_optimizer_v71 import install_talent_optimizer_v71
from talent_recommendations_v67 import install_talent_recommendations_v67
from talent_recommendations_v68 import install_talent_recommendations_v68
from talent_routes_v63 import install_talent_routes_v63
from talent_rules_patch import install_talent_rules
from talent_system import install
from talent_ux import install_ux
from talent_v66_finish import install_talent_v66_finish
from today_types_expansion import install_today_types
from today_types_in_roles import install_types_in_roles
from webapp_inline_fix import install_inline_webapp_fix

# Новая шкала задаётся до установки остальных модулей, чтобы все игровые слои
# использовали одинаковые пороги ролей уже во время своей инициализации.
core.DUST_MIN_POINTS = 1000
core.EXTRAS_MIN_POINTS = 3000
core.SECONDARY_MIN_POINTS = 6000
core.HERO_MIN_POINTS = 10000

# Reality 95 и Reality 92 ставятся первыми. Первый слой добавляет интерфейс
# Ночного охотника, второй — персональные лимиты попыток через стабильные API.
install_admin_night_hunter_v95(core)
install_admin_attempts_hotfix_v92(core)

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
# Reality 66 ставится после расширенного древа и мастерства: он использует
# их билды, предпросмотр и особые таланты, а затем добавляет специализацию,
# недельный прогресс, косметические награды и исправление кнопки прокачки.
install_talent_improvements_v66(core)
install_talent_v66_finish(core)
# Reality 67 заменяет одинаковые левые рекомендации настоящими пошаговыми
# сборками: в каждой ветке доступны отдельные левый и правый маршруты.
install_talent_recommendations_v67(core)
# Reality 68 добавляет отмену выбранной сборки и убирает движение узла:
# следующий шаг только спокойно светится, а свободный режим очищает подсказки.
install_talent_recommendations_v68(core)
# Reality 69 добавляет персональный расчёт по статистике игрока.
install_talent_optimizer_v69(core)
# Reality 70 отделяет быстрый ответ от полного фонового перебора.
install_talent_optimizer_v70(core)
# Reality 71 полностью отключает тяжёлый фоновый перебор на рабочем процессе,
# чтобы session и upgrade отвечали сразу и не блокировали весь сервер Amvera.
install_talent_optimizer_v71(core)

# Сначала задаём базовый урон и тактические механики рейда. Reality 61
# устанавливает предыдущий стабильный слой, Reality 64 выдаёт очки древа,
# а Reality 65 поднимает HP до 100 000 и усложняет давление отряда.
# Reality 62 оставляет совместимые старые API админки, Reality 75 добавляет
# игровой центр, Reality 93 подключает третью хоррор-игру, а Reality 76 поверх
# них подключает новый интерфейс и игровые инструменты.
install_raid_balance_v58(core)
install_raid_v59_fix(core)
install_raid_v60(core)
install_raid_v60_guard(core)
install_raid_v61(core)
install_raid_v61_safety(core)
install_raid_v64_direct_tree(core)
install_raid_v65_balance(core)
install_admin_webapp_v62(core)
install_game_center_runtime_v75(core)
install_night_hunter_v93(core)
install_heist_asset_routes_v78(core)
# Reality 91 подменяет только финал игры: ограбление начисляет всю сохранённую
# добычу, а повторная отправка той же сессии не выдаёт очки второй раз.
install_heist_reward_v91(core)
install_admin_center_v76(core)
install_talent_routes_v63(core)
install_raid_v59_recovery(core)
install_talent_rules(core)
install_about_updates(core)
install_about_recommendations_v67(core)
install_about_recommendations_v68(core)
install_about_optimizer_v69(core)
install_about_optimizer_v70(core)
install_about_optimizer_v71(core)
# Reality 72 заменяет разросшуюся цепочку «О боте» компактной карточкой.
install_about_compact_v72(core)
# Reality 73 добавляет актуальное описание видимых бонусов древа.
install_about_bonus_v73(core)
# Reality 74 финально заменяет карточку актуальной экономикой.
install_about_balance_v74(core)
# Reality 75 добавляет игровой центр и серверные награды.
install_about_games_v75(core)
# Reality 76 добавляет в «О боте» новый админ-центр и его игровые инструменты.
install_about_admin_v76(core)
install_inline_webapp_fix(core)
# Reality 73 видит итоговое начисление после старых талантов.
install_talent_bonus_display_v73(core)
# Reality 74 ставится после начислений: меняет пороги ролей, переносит старые
# балансы, стабилизирует ветку Удачи и добавляет расчёт в Шар судьбы.
install_economy_fate_ui_v74(core)
# Reality 77 финально меняет механику Главного героя дня: +500 остаются
# навсегда, снимается только звание, а временная боевая роль работает до
# следующих выборов.
install_hero_day_v77(core)
# Reality 85 видит итоговые игровые начисления, отделяет карьерное влияние
# от ставок и ускоряет полную прокачку древа до 6–8 недель.
install_knowledge_economy_v85(core)
# Reality 87 уменьшает кулдаун «Увеличить влияние» до шести часов и усиливает
# «Заметную личность» до +5% за уровень.
install_influence_balance_v87(core)
# Reality 88 поднимает базовую выплату команды до 50–150 влияния до применения
# всех бонусов Древа знаний.
install_influence_reward_v88(core)
# Финальный слой меняет карточку и кнопку /admin на актуальную Reality 95.
install_admin_open_v89(core)

# В main.py есть общий обработчик F.text, зарегистрированный раньше расширений.
# Переносим команды древа, мастерства и игр в начало списка, чтобы общий
# обработчик обычного текста не перехватывал их раньше специальных обработчиков.
_priority_names = {
    "cmd_talents",
    "cmd_buffs",
    "cmd_chat_buffs",
    "cmd_builds",
    "cmd_active_talents",
    "cmd_community_tree",
    "cmd_games",
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
