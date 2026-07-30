import asyncio

import main as core
import talent_entry_v164  # noqa: F401  # Устанавливает Reality 183 и все предыдущие слои.
from hero_expansion_v184 import install_hero_expansion_v184
from shop_command_hotfix_v185 import install_shop_command_hotfix_v185
from hero_reality_v184_1 import install_reality_v184_1
from hero_reality_v184_2 import install_reality_v184_2
from hero_reality_v184_3 import install_reality_v184_3


# Reality 184 устанавливается последним: магазин и единая история влияния
# должны видеть итоговые обработчики экономики, ролей и государственных слоёв.
install_hero_expansion_v184(core)
# Reality 185 переносит /shop перед старым общим F.text-обработчиком, иначе
# команда может молча поглощаться монолитным роутером.
install_shop_command_hotfix_v185(core)
# Reality 184.1 добавляет live-статистику, исправляет роль и обновляет slash-меню.
install_reality_v184_1(core)
# Reality 184.2 снижает цены и добавляет косметические предметы, иконки и рамки.
install_reality_v184_2(core)
# Reality 184.3 индексирует журналы и гарантирует быстрый ответ live-endpoint.
install_reality_v184_3(core)


if __name__ == "__main__":
    asyncio.run(core.main())
