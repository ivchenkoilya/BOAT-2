from __future__ import annotations

from pathlib import Path
from typing import Any

from aiohttp import web


HEIST_DIR = Path(__file__).resolve().parent / "games" / "heist"


def install_heist_asset_routes_v78(core: Any) -> None:
    """Раздаёт внешние CSS/JS-файлы ограбления через aiohttp."""
    if getattr(core, "_heist_asset_routes_v78_installed", False):
        return
    core._heist_asset_routes_v78_installed = True

    original_start_server = core.start_webapp_server

    def file_response(path: Path) -> web.FileResponse:
        return core.web.FileResponse(
            path,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Heist-Assets": "reality-78",
            },
        )

    async def heist_style(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "style.css")

    async def heist_script(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "game.js")

    async def start_server_with_heist_assets(bot: Any):
        previous_application = core.web.Application

        def application_factory(*args: Any, **kwargs: Any):
            app = previous_application(*args, **kwargs)
            app.router.add_get("/games/heist/style.css", heist_style)
            app.router.add_get("/games/heist/game.js", heist_script)
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = previous_application

    core.start_webapp_server = start_server_with_heist_assets
