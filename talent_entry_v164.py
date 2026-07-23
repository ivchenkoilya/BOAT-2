import asyncio

import main as core
import talent_entry  # noqa: F401  # Устанавливает все предыдущие слои проекта.
from boss_audio_v154 import install_boss_audio_v154
from boss_rules_v163 import install_boss_rules_v163
from boss_web_v163 import install_boss_web_v163
from economy_rewards_v164 import install_economy_rewards_v164
from finance_fund_link_v167 import install_finance_fund_link_v167
from godot_rooftop_test_button_v155 import install_godot_test_button
from godot_rooftop_test_routes_v170 import install_godot_rooftop_test_routes
from godot_rooftop_test_v155 import start_godot_rooftop_test_install
from government_android_webview_hotfix_v166 import install_government_android_webview_hotfix_v166
from government_creator_sanctions_v164 import install_government_creator_sanctions_v164
from government_home_oversight_deputy_v175 import install_government_home_oversight_deputy_v175
from government_official_voting_v168 import install_government_official_voting_v168
from government_oversight_deputy_v167 import install_government_oversight_deputy_v167
from government_president_direct_deputy_v173 import install_government_president_direct_deputy_v173
from government_programs_property_v176 import install_government_programs_property_v176
from government_reality_v177 import install_government_reality_v177
from government_reality_v177_api import install_government_reality_v177_api
from government_reality_v177_safety import install_government_reality_v177_safety
from government_release_v165 import install_government_release_v165
from government_reliability_laws_v167 import install_government_reliability_laws_v167
from government_ui_hotfix_v169 import install_government_ui_hotfix_v169
from government_universal_voting_v174 import install_government_universal_voting_v174


# Финальный государственный слой включает запросы госструктур в казну Reality 165.
install_government_release_v165(core)
# Убирает параллельные фоновые загрузки казны и повторные DDL-запросы.
install_government_android_webview_hotfix_v166(core)
# Добавляет владельцу отдельную панель снятия всех санкций в Mini App Правительства.
install_government_creator_sanctions_v164(core)
# Объединяет все запросы состояния, чинит обновление и добавляет президентские редакции законов.
install_government_reliability_laws_v167(core)
# Добавляет заместителя главы Надзора, жалобы, проверки, реестр и отчёты.
install_government_oversight_deputy_v167(core)
# Даёт право голоса всем действующим должностным лицам, включая новую должность Надзора.
install_government_official_voting_v168(core)
# Связывает акции и ставки вкладов с государственными и частными фондами беседы.
install_finance_fund_link_v167(core)
# Исправляет мобильную вёрстку ополчения и выводит новую должность во вкладке «Полномочия».
install_government_ui_hotfix_v169(core)
# Президент назначает заместителя главы Надзора напрямую, без Госдумы и карьерного порога.
install_government_president_direct_deputy_v173(core)
# Снимает старый депутатский фильтр middleware: любая действующая должность голосует по любому проекту.
install_government_universal_voting_v174(core)
# Показывает назначенного заместителя главы Надзора в основном составе власти.
install_government_home_oversight_deputy_v175(core)
# Госпрограммы, имущество чиновников, декларации Надзора и государственные аукционы.
install_government_programs_property_v176(core)
# Reality 177 объединяет фонды, повышает цены программ, добавляет новые программы,
# рейтинг власти и отдельный мобильный раздел имущества с безопасными операциями.
install_government_reality_v177(core)
install_government_reality_v177_api(core)
# Закрывает одновременное повторное исполнение одноразовых экстренных действий.
install_government_reality_v177_safety(core)
# Финальные правила рейда ставятся после всех старых обёрток боя и героев.
install_boss_rules_v163(core)
install_boss_audio_v154()
install_boss_web_v163(core)
# Экономический баланс должен стоять последним, чтобы старые слои не вернули
# прежние награды Шара и «Увеличить влияние».
install_economy_rewards_v164(core)

# Godot-тест получает собственные aiohttp-маршруты. Это нужно, потому что
# создание новой папки во время запуска само по себе не расширяет старый
# список обслуживаемых игровых адресов.
install_godot_rooftop_test_routes(core)
install_godot_test_button()
start_godot_rooftop_test_install()


if __name__ == "__main__":
    asyncio.run(core.main())
