import asyncio

import main as core
import talent_entry  # noqa: F401  # Устанавливает все предыдущие слои проекта.
from boss_audio_v154 import install_boss_audio_v154
from boss_balance_v151 import install_boss_balance_v151
from government_release_v150 import install_government_release_v150


install_government_release_v150(core)
# Ставится последним: кулдауны, щиты, лёгкие дебафы и повторная способность
# Былогерия не должны перезаписываться предыдущими слоями проекта.
install_boss_balance_v151(core)
# Собирает проверенный музыкальный цикл в один OGG до запуска веб-сервера.
install_boss_audio_v154()


if __name__ == "__main__":
    asyncio.run(core.main())
