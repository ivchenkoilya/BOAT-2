import asyncio

import main as core
import talent_entry  # noqa: F401  # Устанавливает все предыдущие слои проекта.
from boss_audio_v154 import install_boss_audio_v154
from boss_rules_v163 import install_boss_rules_v163
from boss_web_v163 import install_boss_web_v163
from government_release_v162 import install_government_release_v162


install_government_release_v162(core)
# Финальный слой рейда ставится после всех старых обёрток боя и героев.
install_boss_rules_v163(core)
install_boss_audio_v154()
install_boss_web_v163(core)


if __name__ == "__main__":
    asyncio.run(core.main())
