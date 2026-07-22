import asyncio

import main as core
import talent_entry  # noqa: F401
from government_release_v159 import install_government_release_v159


install_government_release_v159(core)


if __name__ == "__main__":
    asyncio.run(core.main())
