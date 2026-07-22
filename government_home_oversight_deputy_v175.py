from __future__ import annotations

from pathlib import Path
from typing import Any

import government_mandate_luxury_v147 as luxury


VERSION = "Reality 175 · Заместитель Надзора в составе власти"
ASSET_JS = Path(__file__).resolve().parent / "governmentapp_v127" / "home-oversight-deputy-v175.js"


def _route_keys(app: Any) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        result.add(
            (
                str(getattr(route, "method", "") or "").upper(),
                str(getattr(resource, "canonical", "") or ""),
            )
        )
    return result


def install_government_home_oversight_deputy_v175(core: Any) -> None:
    if getattr(core, "_government_home_oversight_deputy_v175_installed", False):
        return
    core._government_home_oversight_deputy_v175_installed = True
    core.GOVERNMENT_VERSION = VERSION

    previous_inject = luxury._inject_assets

    def inject(source: str) -> str:
        source = previous_inject(source)
        if ASSET_JS.name not in source:
            source = source.replace(
                "</body>",
                f'  <script src="/government-v175/{ASSET_JS.name}?v=175"></script>\n</body>',
            )
        return source

    luxury._inject_assets = inject

    original_start = core.start_webapp_server

    async def start(bot: Any):
        if not ASSET_JS.is_file():
            raise RuntimeError("Не найден интерфейс состава власти Reality 175")

        original_runner = core.web.AppRunner

        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            if name != ASSET_JS.name:
                raise core.web.HTTPNotFound()
            return core.web.FileResponse(
                ASSET_JS,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Content-Type": "application/javascript; charset=utf-8",
                    "X-Government-Home-Deputy": "175",
                },
            )

        def runner(app: Any, *args: Any, **kwargs: Any):
            if ("GET", "/government-v175/{name}") not in _route_keys(app):
                app.router.add_get("/government-v175/{name}", asset)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start
