import asyncio

import main as core
import talent_entry  # noqa: F401
from godot_rooftop_test_v155 import start_godot_rooftop_test_install
from government_release_v152 import install_government_release_v152


start_godot_rooftop_test_install()
install_government_release_v152(core)


if __name__ == "__main__":
    asyncio.run(core.main())
