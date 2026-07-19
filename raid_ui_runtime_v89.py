from __future__ import annotations

from typing import Any

from aiohttp import web


_ALLOWED_NAMES = {
    "battle-fx.js",
    "raid-interface-v19.css",
    "raid-interface-v19.js",
    "raid-hotfix-v89.css",
}


def install_raid_ui_runtime_v89(core: Any) -> None:
    """Serve only the current raid UI files as a fallback.

    The production entrypoint normally embeds these files directly in HTML.
    Explicit fallback routes are kept for development and partial deployments,
    without enabling obsolete top-level CSS/JS files from older raid layers.
    """
    if getattr(core, "_raid_ui_runtime_v89_installed", False):
        return
    core._raid_ui_runtime_v89_installed = True

    original_start_server = core.start_webapp_server

    async def raid_asset(request: web.Request) -> web.StreamResponse:
        name = str(request.match_info.get("raid_asset", ""))
        if name not in _ALLOWED_NAMES:
            raise web.HTTPNotFound()
        target = core.WEBAPP_DIR / name
        if not target.is_file():
            raise web.HTTPNotFound()
        return core.web.FileResponse(
            target,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Raid-UI": "reality-89",
            },
        )

    async def start_server_with_raid_assets(bot: Any):
        previous_application = core.web.Application

        def application_factory(*args: Any, **kwargs: Any):
            app = previous_application(*args, **kwargs)
            for name in sorted(_ALLOWED_NAMES):
                app.router.add_get(
                    f"/boss-app/{name}",
                    raid_asset,
                    name=f"raid-ui-v89-{name}",
                )
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = previous_application

    core.start_webapp_server = start_server_with_raid_assets
