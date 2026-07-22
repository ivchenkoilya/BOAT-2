from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import government_mandate_luxury_v147 as luxury


VERSION = "Reality 164 · Снятие всех санкций создателем"
APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "creator-sanctions-v164.js"
ASSET_CSS = APP_DIR / "creator-sanctions-v164.css"


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


def _with_assets(previous_inject: Callable[[str], str], source: str) -> str:
    source = previous_inject(source)
    if "creator-sanctions-v164.css" not in source:
        source = source.replace(
            "</head>",
            '  <link rel="stylesheet" href="/government-v164/creator-sanctions-v164.css?v=164">\n</head>',
        )
    if "creator-sanctions-v164.js" not in source:
        source = source.replace(
            "</body>",
            '  <script src="/government-v164/creator-sanctions-v164.js?v=164"></script>\n</body>',
        )
    return source


def install_government_creator_sanctions_v164(core: Any) -> None:
    if getattr(core, "_government_creator_sanctions_v164_installed", False):
        return
    core._government_creator_sanctions_v164_installed = True
    core.GOVERNMENT_VERSION = VERSION

    previous_inject = luxury._inject_assets

    def inject_with_creator_sanctions(source: str) -> str:
        return _with_assets(previous_inject, source)

    luxury._inject_assets = inject_with_creator_sanctions

    async def asset(request: Any):
        name = str(request.match_info.get("name") or "")
        if name == "creator-sanctions-v164.js":
            path = ASSET_JS
            content_type = "application/javascript"
        elif name == "creator-sanctions-v164.css":
            path = ASSET_CSS
            content_type = "text/css"
        else:
            raise core.web.HTTPNotFound()
        return core.web.FileResponse(
            path,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "Content-Type": f"{content_type}; charset=utf-8",
                "X-Government-Creator-Sanctions": "164",
            },
        )

    original_start = core.start_webapp_server

    async def start_with_creator_sanctions(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты снятия санкций Reality 164")
        original_runner = core.web.AppRunner

        def runner_with_creator_sanctions(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            route = "/government-v164/{name}"
            if ("GET", route) not in keys:
                app.router.add_get(route, asset)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_creator_sanctions
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_creator_sanctions
