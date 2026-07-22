import asyncio

import main as core
import talent_entry  # noqa: F401  # Устанавливает все предыдущие слои проекта.
from government_release_v152 import install_government_release_v152


# Godot Web-сборка временно отключена: в Telegram Android она открывается
# чёрным экраном и блокирует игровой центр. До отдельной проверки Web-экспорта
# используется стабильная HTML-версия из games/rooftop.
install_government_release_v152(core)


if __name__ == "__main__":
    asyncio.run(core.main())
