import asyncio

import main as core
from talent_system import install

install(core)

if __name__ == "__main__":
    asyncio.run(core.main())
