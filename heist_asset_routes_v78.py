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
                "X-Heist-Assets": "reality-91",
            },
        )

    async def heist_style(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "style.css")

    async def heist_script(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "game.js")

    async def heist_enhance_style(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "enhance-v83.css")

    async def heist_pre_script(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "pre-v83.js")

    async def heist_enhance_script(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "enhance-v83.js")

    async def heist_v84_style(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "style-v84.css")

    async def heist_v84_script(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "game-v84.js")

    async def heist_v86_ui_style(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "ui-v86.css")

    async def heist_v86_ui_script(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "ui-v86.js")

    async def heist_v87_loader(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "loader-v87.js")

    async def heist_v87_polish_style(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "polish-v87.css")

    async def heist_v87_polish_script(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "polish-v87.js")

    async def heist_v88_loader(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "loader-v88.js")

    async def heist_v88_patch_1(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "patch-v88-1.js")

    async def heist_v88_patch_2(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "patch-v88-2.js")

    async def heist_v88_patch_3(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "patch-v88-3.js")

    async def heist_v88_patch_4(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "patch-v88-4.js")

    async def heist_v88_patch_5(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "patch-v88-5.js")

    async def heist_v88_polish_style(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "polish-v88.css")

    async def heist_v88_polish_script(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "polish-v88.js")

    async def heist_v90_loader(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "loader-v90.js")

    async def heist_v90_patch(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "patch-v90.js")

    async def heist_v90_hotfix(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "patch-v90-hotfix.js")

    async def heist_v90_polish_style(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "polish-v90.css")

    async def heist_v91_loader(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "loader-v91.js")

    async def heist_v91_patch(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "patch-v91.js")

    async def heist_v91_polish_style(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "polish-v91.css")

    async def heist_v91_polish_script(_: web.Request) -> web.StreamResponse:
        return file_response(HEIST_DIR / "polish-v91.js")

    async def start_server_with_heist_assets(bot: Any):
        previous_application = core.web.Application

        def application_factory(*args: Any, **kwargs: Any):
            app = previous_application(*args, **kwargs)
            app.router.add_get("/games/heist/style.css", heist_style)
            app.router.add_get("/games/heist/game.js", heist_script)
            app.router.add_get("/games/heist/enhance-v83.css", heist_enhance_style)
            app.router.add_get("/games/heist/pre-v83.js", heist_pre_script)
            app.router.add_get("/games/heist/enhance-v83.js", heist_enhance_script)
            app.router.add_get("/games/heist/style-v84.css", heist_v84_style)
            app.router.add_get("/games/heist/game-v84.js", heist_v84_script)
            app.router.add_get("/games/heist/ui-v86.css", heist_v86_ui_style)
            app.router.add_get("/games/heist/ui-v86.js", heist_v86_ui_script)
            app.router.add_get("/games/heist/loader-v87.js", heist_v87_loader)
            app.router.add_get("/games/heist/polish-v87.css", heist_v87_polish_style)
            app.router.add_get("/games/heist/polish-v87.js", heist_v87_polish_script)
            app.router.add_get("/games/heist/loader-v88.js", heist_v88_loader)
            app.router.add_get("/games/heist/patch-v88-1.js", heist_v88_patch_1)
            app.router.add_get("/games/heist/patch-v88-2.js", heist_v88_patch_2)
            app.router.add_get("/games/heist/patch-v88-3.js", heist_v88_patch_3)
            app.router.add_get("/games/heist/patch-v88-4.js", heist_v88_patch_4)
            app.router.add_get("/games/heist/patch-v88-5.js", heist_v88_patch_5)
            app.router.add_get("/games/heist/polish-v88.css", heist_v88_polish_style)
            app.router.add_get("/games/heist/polish-v88.js", heist_v88_polish_script)
            app.router.add_get("/games/heist/loader-v90.js", heist_v90_loader)
            app.router.add_get("/games/heist/patch-v90.js", heist_v90_patch)
            app.router.add_get("/games/heist/patch-v90-hotfix.js", heist_v90_hotfix)
            app.router.add_get("/games/heist/polish-v90.css", heist_v90_polish_style)
            app.router.add_get("/games/heist/loader-v91.js", heist_v91_loader)
            app.router.add_get("/games/heist/patch-v91.js", heist_v91_patch)
            app.router.add_get("/games/heist/polish-v91.css", heist_v91_polish_style)
            app.router.add_get("/games/heist/polish-v91.js", heist_v91_polish_script)
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = previous_application

    core.start_webapp_server = start_server_with_heist_assets
