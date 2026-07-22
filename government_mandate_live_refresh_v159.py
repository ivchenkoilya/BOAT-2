from __future__ import annotations

from pathlib import Path
from typing import Any

import government_mandate_luxury_v147 as luxury


VERSION = "Reality 159 · Живой реестр мандатов"
ASSET = Path(__file__).resolve().parent / "governmentapp_v127" / "mandate-live-refresh-v159.js"


def install_government_mandate_live_refresh_v159(core: Any) -> None:
    if getattr(core, "_government_mandate_live_refresh_v159_installed", False):
        return
    core._government_mandate_live_refresh_v159_installed = True
    core.GOVERNMENT_VERSION = VERSION

    previous_inject = luxury._inject_assets

    def inject(source: str) -> str:
        source = previous_inject(source)
        if ASSET.name not in source:
            source = source.replace(
                "</body>",
                f'  <script src="/government-v159/{ASSET.name}?v=159"></script>\n</body>',
            )
        return source

    luxury._inject_assets = inject
    original_start = core.start_webapp_server

    async def start(bot: Any):
        if not ASSET.is_file():
            raise RuntimeError("Missing Reality 159 mandate refresh asset")
        original_runner = core.web.AppRunner

        async def serve(_: Any):
            return core.web.FileResponse(
                ASSET,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Government-Mandate-Refresh": "159",
                },
            )

        def runner(app: Any, *args: Any, **kwargs: Any):
            path = f"/government-v159/{ASSET.name}"
            known = {
                (
                    str(getattr(route, "method", "") or "").upper(),
                    str(getattr(getattr(route, "resource", None), "canonical", "") or ""),
                )
                for route in app.router.routes()
            }
            if ("GET", path) not in known:
                app.router.add_get(path, serve)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start
