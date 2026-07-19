from __future__ import annotations

from pathlib import Path
from typing import Any

from aiohttp import web

import game_center_v75 as base


VERSION = "Reality 95 · Живая охота"
GAME_KEY = "night-hunter"
GAME_PATH = Path(__file__).resolve().parent / "games" / GAME_KEY
PART_FILENAMES = tuple(f"game-v95-{letter}.part" for letter in "abcdefg")


def install_night_hunter_v93(core: Any) -> None:
    """Adds the third Mini App game without replacing the stable game runtime."""
    if getattr(core, "_night_hunter_v93_installed", False):
        return
    core._night_hunter_v93_installed = True

    base.GAME_INFO[GAME_KEY] = {
        "title": "Ночной охотник",
        "emoji": "🔦",
        "duration": 150,
        "max_reward": 130,
    }

    previous_reward = base._base_reward

    def reward_with_night_hunter(game_key: str, score: int) -> int:
        if game_key != GAME_KEY:
            return previous_reward(game_key, score)
        value = max(0, int(score))
        if value <= 0:
            return 0
        if value < 35:
            return 15
        if value < 80:
            return 35
        if value < 130:
            return 60
        if value < 190:
            return 90
        if value < 245:
            return 110
        return 130

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

    async def night_style(_: web.Request) -> web.StreamResponse:
        return file_response(GAME_PATH / "style.css")

    async def night_script(_: web.Request) -> web.StreamResponse:
        return file_response(GAME_PATH / "game.js")

    def make_part_handler(filename: str):
        async def night_part(_: web.Request) -> web.StreamResponse:
            return file_response(GAME_PATH / filename)

        return night_part

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
            app.router.add_get("/games/night-hunter/style.css", night_style)
            app.router.add_get("/games/night-hunter/game.js", night_script)
            for filename in PART_FILENAMES:
                app.router.add_get(
                    f"/games/night-hunter/{filename}",
                    make_part_handler(filename),
                )
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = previous_application

    core.start_webapp_server = start_server_with_night_hunter
