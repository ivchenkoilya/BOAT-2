from __future__ import annotations

from pathlib import Path
from typing import Any

from aiohttp import web


VERSION = "Reality 95 · Три игры"
BASE_SCRIPT = Path(__file__).resolve().parent / "adminapp_v89" / "admin-v89.js"
PATCH_SCRIPT = Path(__file__).resolve().parent / "adminapp_v95" / "night-hunter-admin.js"


def install_admin_night_hunter_v95(core: Any) -> None:
    """Adds Night Hunter controls to the existing stable admin panel."""
    if getattr(core, "_admin_night_hunter_v95_installed", False):
        return
    core._admin_night_hunter_v95_installed = True
    core.ADMIN_CENTER_VERSION = VERSION

    @web.middleware
    async def night_hunter_admin_middleware(
        request: web.Request,
        handler: Any,
    ) -> web.StreamResponse:
        if request.method == "GET" and request.path in {
            "/admin-v89/admin-v89.js",
            "/admin-v76/admin-v89.js",
        }:
            script = BASE_SCRIPT.read_text(encoding="utf-8")
            patch = PATCH_SCRIPT.read_text(encoding="utf-8")
            return web.Response(
                text=f"{script}\n\n{patch}\n",
                content_type="application/javascript",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Admin-Center": "reality-95-night-hunter",
                },
            )
        return await handler(request)

    original_application = core.web.Application

    def application_with_night_hunter(*args: Any, **kwargs: Any):
        middlewares = list(kwargs.pop("middlewares", []) or [])
        kwargs["middlewares"] = [night_hunter_admin_middleware, *middlewares]
        return original_application(*args, **kwargs)

    core.web.Application = application_with_night_hunter
