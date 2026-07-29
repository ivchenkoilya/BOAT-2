import asyncio

import main as core
import talent_entry_v164  # noqa: F401  # Устанавливает Reality 183 и все предыдущие слои.
from hero_expansion_v184 import install_hero_expansion_v184


# Reality 184 устанавливается последним: магазин и единая история влияния
# должны видеть итоговые обработчики экономики, ролей и государственных слоёв.
install_hero_expansion_v184(core)


if __name__ == "__main__":
    asyncio.run(core.main())
