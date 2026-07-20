from __future__ import annotations

from pathlib import Path
from typing import Any

from aiohttp import web

import game_center_v75 as base


VERSION = "Reality 108 · Factory Loop"
GAME_KEY = "night-hunter"
GAME_PATH = Path(__file__).resolve().parent / "games" / GAME_KEY
STYLE_FILENAMES = ("style-v108.css",)
SCRIPT_FILENAMES = ("game-v108.js",)


def install_night_hunter_v93(core: Any) -> None:
    """Подключает Reality 108: мистическую заводскую смену без оружия."""
    if getattr(core, "_night_hunter_v93_installed", False):
        return
    core._night_hunter_v93_installed = True

    base.GAME_INFO[GAME_KEY] = {
        "title": "Ночной охотник: Последняя смена",
        "emoji": "🔦",
        "duration": 1200,
        "max_reward": 180,
    }

    previous_reward = base._base_reward

    def reward_with_night_hunter(game_key: str, score: int) -> int:
        if game_key != GAME_KEY:
            return previous_reward(game_key, score)
        value = max(0, int(score))
        if value <= 0:
            return 0
        if value < 450:
            return 15
        if value < 900:
            return 45
        if value < 1400:
            return 80
        if value < 2000:
            return 120
        if value < 2700:
            return 150
        return 180

    base._base_reward = reward_with_night_hunter

    def file_response(path: Path) -> web.FileResponse:
        return core.web.FileResponse(
            path,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Night-Hunter": VERSION,
            },
        )

    async def night_index(_: web.Request) -> web.StreamResponse:
        return file_response(GAME_PATH / "index.html")

    def make_static_handler(filename: str):
        async def static_file(_: web.Request) -> web.StreamResponse:
            return file_response(GAME_PATH / filename)

        return static_file

    original_start_server = core.start_webapp_server

    async def start_server_with_night_hunter(bot: Any):
        previous_application = core.web.Application

        def application_factory(*args: Any, **kwargs: Any):
            app = previous_application(*args, **kwargs)
            for path in (
                "/games/night-hunter",
                "/games/night-hunter/",
                "/games/night-hunter/index.html",
            ):
                app.router.add_get(path, night_index)
            for filename in STYLE_FILENAMES + SCRIPT_FILENAMES:
                app.router.add_get(
                    f"/games/night-hunter/{filename}",
                    make_static_handler(filename),
                )
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = previous_application

    core.start_webapp_server = start_server_with_night_hunter
