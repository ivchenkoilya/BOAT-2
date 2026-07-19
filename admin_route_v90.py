from __future__ import annotations

from pathlib import Path
from typing import Any


ADMIN_DIR = Path(__file__).resolve().parent / "adminapp_v76"


def install_admin_route_v90(core: Any) -> None:
    """Отдаёт актуальный админ-центр по отдельному URL без старого кэша Telegram."""
    if getattr(core, "_admin_route_v90_installed", False):
        return
    core._admin_route_v90_installed = True

    def response(path: Path):
        return core.web.FileResponse(
            path,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Admin-Center": "reality-90",
                "Clear-Site-Data": '"cache"',
            },
        )

    async def index(_: Any):
        return response(ADMIN_DIR / "index.html")

    async def base_css(_: Any):
        return response(ADMIN_DIR / "admin.css")

    async def base_js(_: Any):
        return response(ADMIN_DIR / "admin.js")

    original_start_server = core.start_webapp_server

    async def start_server_v90(bot: Any):
        previous_application = core.web.Application

        def application_factory(*args: Any, **kwargs: Any):
            app = previous_application(*args, **kwargs)
            app.router.add_get("/admin-v89", index)
            app.router.add_get("/admin-v89/", index)
            app.router.add_get("/admin-v89/base.css", base_css)
            app.router.add_get("/admin-v89/base.js", base_js)
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = previous_application

    core.start_webapp_server = start_server_v90
