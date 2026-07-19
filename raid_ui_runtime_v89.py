from __future__ import annotations

import re
from typing import Any

from aiohttp import web


_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_ALLOWED_SUFFIXES = {
    ".css",
    ".js",
    ".json",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".mp3",
    ".ogg",
    ".wav",
}


def install_raid_ui_runtime_v89(core: Any) -> None:
    """Serve top-level raid assets that the legacy two-file route rejected."""
    if getattr(core, "_raid_ui_runtime_v89_installed", False):
        return
    core._raid_ui_runtime_v89_installed = True

    original_start_server = core.start_webapp_server

    async def raid_asset(request: web.Request) -> web.StreamResponse:
        name = str(request.match_info.get("raid_asset", ""))
        if not _SAFE_NAME.fullmatch(name):
            raise web.HTTPNotFound()

        target = (core.WEBAPP_DIR / name).resolve()
        webapp_root = core.WEBAPP_DIR.resolve()
        if target.parent != webapp_root or target.suffix.lower() not in _ALLOWED_SUFFIXES:
            raise web.HTTPNotFound()
        if not target.is_file():
            raise web.HTTPNotFound()

        headers = {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Raid-UI": "reality-89",
        }

        # Reality 60 originally displayed its attack card for seven seconds.
        # Serve the same controller with a strict three-second warning window.
        if name == "raid-v60.js":
            source = target.read_text(encoding="utf-8")
            source = source.replace(
                'id="raidWarningTimeV60">7</strong>',
                'id="raidWarningTimeV60">3</strong>',
            )
            source = source.replace(
                "const visible=active&&seconds<=7;",
                "const visible=active&&seconds<=3;",
            )
            return core.web.Response(
                text=source,
                content_type="application/javascript",
                headers=headers,
            )

        return core.web.FileResponse(target, headers=headers)

    async def start_server_with_raid_assets(bot: Any):
        previous_application = core.web.Application

        def application_factory(*args: Any, **kwargs: Any):
            app = previous_application(*args, **kwargs)
            # Register before the legacy /boss-app/{style.css|app.js} route.
            # It safely serves every top-level CSS/JS file referenced by index.html.
            app.router.add_get(
                r"/boss-app/{raid_asset:[A-Za-z0-9][A-Za-z0-9_.-]*}",
                raid_asset,
            )
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = previous_application

    core.start_webapp_server = start_server_with_raid_assets
