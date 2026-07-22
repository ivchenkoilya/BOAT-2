import asyncio

import main as core
import talent_entry  # noqa: F401  # Устанавливает все предыдущие слои проекта.
from boss_audio_v154 import install_boss_audio_v154
from boss_rules_v163 import install_boss_rules_v163
from boss_web_v163 import install_boss_web_v163
from economy_rewards_v164 import install_economy_rewards_v164
from finance_fund_link_v167 import install_finance_fund_link_v167
from government_android_webview_hotfix_v166 import install_government_android_webview_hotfix_v166
from government_creator_sanctions_v164 import install_government_creator_sanctions_v164
from government_official_voting_v168 import install_government_official_voting_v168
from government_oversight_deputy_v167 import install_government_oversight_deputy_v167
from government_release_v165 import install_government_release_v165
from government_reliability_laws_v167 import install_government_reliability_laws_v167


# Финальный государственный слой включает запросы госструктур в казну Reality 165.
install_government_release_v165(core)
# Убирает параллельные фоновые загрузки казны и повторные DDL-запросы.
install_government_android_webview_hotfix_v166(core)
# Добавляет владельцу отдельную панель снятия всех санкций в Mini App Правительства.
install_government_creator_sanctions_v164(core)
# Объединяет все запросы состояния, чинит обновление и добавляет президентские редакции законов.
install_government_reliability_laws_v167(core)
# Даёт право голоса всем действующим должностным лицам, включая президента.
install_government_official_voting_v168(core)
# Добавляет заместителя главы Надзора, жалобы, проверки, реестр и отчёты.
install_government_oversight_deputy_v167(core)
# Связывает акции и ставки вкладов с государственными и частными фондами беседы.
install_finance_fund_link_v167(core)
# Финальные правила рейда ставятся после всех старых обёрток боя и героев.
install_boss_rules_v163(core)
install_boss_audio_v154()
install_boss_web_v163(core)
# Экономический баланс должен стоять последним, чтобы старые слои не вернули
# прежние награды Шара и «Увеличить влияние».
install_economy_rewards_v164(core)


if __name__ == "__main__":
    asyncio.run(core.main())
