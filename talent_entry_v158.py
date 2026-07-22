import asyncio

import main as core
import talent_entry  # noqa: F401
from government_release_v158 import install_government_release_v158


install_government_release_v158(core)


if __name__ == "__main__":
    asyncio.run(core.main())
