from __future__ import annotations

from pathlib import Path
from typing import Any

import government_mandate_luxury_v147 as luxury


VERSION = "Reality 172 · Компактные полномочия заместителя Надзора"
APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "government-ui-hotfix-v169.js"
ASSET_CSS = APP_DIR / "government-ui-hotfix-v169.css"


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


def install_government_ui_hotfix_v169(core: Any) -> None:
    if getattr(core, "_government_ui_hotfix_v169_installed", False):
        return
    core._government_ui_hotfix_v169_installed = True
    core.GOVERNMENT_VERSION = VERSION

    previous_inject = luxury._inject_assets

    def inject_ui_hotfix(source: str) -> str:
        source = previous_inject(source)
        if ASSET_CSS.name not in source:
            source = source.replace(
                "</head>",
                f'  <link rel="stylesheet" href="/government-v169/{ASSET_CSS.name}?v=172">\n</head>',
            )
        if ASSET_JS.name not in source:
            source = source.replace(
                "</body>",
                f'  <script src="/government-v169/{ASSET_JS.name}?v=172"></script>\n</body>',
            )
        return source

    luxury._inject_assets = inject_ui_hotfix

    original_start = core.start_webapp_server

    async def start_with_ui_hotfix(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты исправления интерфейса Reality 172")

        original_runner = core.web.AppRunner

        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            path = (
                ASSET_JS
                if name == ASSET_JS.name
                else ASSET_CSS
                if name == ASSET_CSS.name
                else None
            )
            if path is None:
                raise core.web.HTTPNotFound()
            content_type = "application/javascript" if path.suffix == ".js" else "text/css"
            return core.web.FileResponse(
                path,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Content-Type": f"{content_type}; charset=utf-8",
                    "X-Government-UI-Hotfix": "172",
                },
            )

        def runner_with_ui_hotfix(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/government-v169/{name}") not in keys:
                app.router.add_get("/government-v169/{name}", asset)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_ui_hotfix
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_ui_hotfix
