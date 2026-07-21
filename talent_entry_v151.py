import asyncio

import main as core
import talent_entry  # noqa: F401  # Устанавливает все предыдущие слои проекта.
from government_release_v151 import install_government_release_v151


install_government_release_v151(core)


if __name__ == "__main__":
    asyncio.run(core.main())
