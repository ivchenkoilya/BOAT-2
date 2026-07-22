import asyncio

import main as core
import talent_entry  # noqa: F401  # Устанавливает все предыдущие слои проекта.
from godot_rooftop_v153 import install_godot_rooftop
from government_release_v152 import install_government_release_v152


# Godot Web-сборка скачивается один раз в постоянный /data-кеш и подменяет
# старую HTML-игру до запуска aiohttp. При ошибке остаётся прежний вариант.
install_godot_rooftop()
install_government_release_v152(core)


if __name__ == "__main__":
    asyncio.run(core.main())
