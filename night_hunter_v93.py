from __future__ import annotations

from pathlib import Path
from typing import Any

from aiohttp import web

import game_center_v75 as base


VERSION = "Reality 106 · Living Mission"
GAME_KEY = "night-hunter"
GAME_PATH = Path(__file__).resolve().parent / "games" / GAME_KEY
STYLE_FILENAMES = (
    "style.css",
    "style-v101.css",
    "style-v102.css",
    "style-v104.css",
    "style-v105.css",
    "style-v106.css",
)
SCRIPT_FILENAMES = (
    "game-v106.js",
    "game-v106-interactions.js",
    "game-v106-fixes.js",
    "game-v105.js",
    "game-v105-ui.js",
    "game-v104.js",
    "game-v104-story.js",
    "game-v104-fixes.js",
    "game-v102.js",
    "game-v102-art.js",
    "game-v101-art.js",
    "game-v100-a.js",
    "game-v100-b.js",
    "game-v100-c.js",
    "game-v100-d.js",
    "game-v100-e.js",
    "game-v100-f.js",
    "game-v100-g.js",
    "game-v100-h.js",
)


def install_night_hunter_v93(core: Any) -> None:
    """Подключает Reality 106: контекстные действия, анимации и мягкую камеру."""
    if getattr(core, "_night_hunter_v93_installed", False):
        return
    core._night_hunter_v93_installed = True

    base.GAME_INFO[GAME_KEY] = {
        "title": "Ночной охотник: Эвакуация",
        "emoji": "🔫",
        "duration": 360,
        "max_reward": 180,
    }

    previous_reward = base._base_reward

    def reward_with_night_hunter(game_key: str, score: int) -> int:
        if game_key != GAME_KEY:
            return previous_reward(game_key, score)
        value = max(0, int(score))
        if value <= 0:
            return 0
        if value < 250:
            return 15
        if value < 600:
            return 45
        if value < 1000:
            return 80
        if value < 1500:
            return 120
        if value < 2100:
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
