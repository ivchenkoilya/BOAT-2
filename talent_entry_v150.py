import asyncio

import main as core
import talent_entry  # noqa: F401  # Устанавливает все предыдущие слои проекта.
from government_release_v150 import install_government_release_v150


install_government_release_v150(core)


if __name__ == "__main__":
    asyncio.run(core.main())
