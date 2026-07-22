import asyncio

import main as core
import talent_entry  # noqa: F401  # Устанавливает все предыдущие слои проекта.
from government_release_v157 import install_government_release_v157


install_government_release_v157(core)


if __name__ == "__main__":
    asyncio.run(core.main())
