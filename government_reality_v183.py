from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import government_mandate_luxury_v147 as luxury
import government_v127 as gov

from government_reality_v183_common import CLIENT_BUILD, VERSION
from government_reality_v183_map import enhance_map_state_v183

APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "reality-v183-map-20260724.js"
ASSET_CSS = APP_DIR / "reality-v183-map-20260724.css"
ASSET_SVG = APP_DIR / "reality-v183-buildings-20260724.svg"


def _route_keys(app: Any) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        result.add((str(getattr(route, "method", "") or "").upper(), str(getattr(resource, "canonical", "") or "")))
    return result


def _replace_map_assets(source: str) -> str:
    for version in (180, 181, 182):
        source = re.sub(rf'\s*<link[^>]+reality-v{version}-map[^>]*\.css[^>]*>\s*', "\n", source, flags=re.IGNORECASE)
        source = re.sub(rf'\s*<script[^>]+reality-v{version}-map[^>]*\.js[^>]*></script>\s*', "\n", source, flags=re.IGNORECASE)
    if ASSET_CSS.name not in source:
        source = source.replace("</head>", f'  <link rel="stylesheet" href="/government-v183/{ASSET_CSS.name}?build={CLIENT_BUILD}">\n</head>')
    if ASSET_JS.name not in source:
        source = source.replace("</body>", f'  <script src="/government-v183/{ASSET_JS.name}?build={CLIENT_BUILD}"></script>\n</body>')
    return source


def install_government_reality_v183(core: Any) -> None:
    if getattr(core, "_government_reality_v183_installed", False):
        return
    core._government_reality_v183_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION

    previous_state = gov._state

    async def state_v183(core_arg: Any, bot: Any, chat_id: int, user_id: int):
        payload = await previous_state(core_arg, bot, int(chat_id), int(user_id))
        base_map = dict((payload.get("reality182") or {}).get("map") or {})
        construction = dict((payload.get("reality179") or {}).get("construction") or {})
        payload["version"] = VERSION
        payload["reality183"] = {"map": enhance_map_state_v183(base_map, construction)}
        return payload

    gov._state = state_v183

    previous_inject = luxury._inject_assets

    def inject_v183(source: str) -> str:
        return _replace_map_assets(previous_inject(source))

    luxury._inject_assets = inject_v183

    original_start = core.start_webapp_server

    async def start_v183(bot: Any):
        for path in (ASSET_JS, ASSET_CSS, ASSET_SVG):
            if not path.is_file():
                raise RuntimeError(f"Не найден ассет Reality 183: {path.name}")
        original_runner = core.web.AppRunner

        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            paths = {ASSET_JS.name: ASSET_JS, ASSET_CSS.name: ASSET_CSS, ASSET_SVG.name: ASSET_SVG}
            path = paths.get(name)
            if path is None:
                raise core.web.HTTPNotFound()
            headers = {
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Government-Reality": CLIENT_BUILD,
            }
            if path.suffix == ".svg":
                headers["Content-Type"] = "image/svg+xml; charset=utf-8"
            return core.web.FileResponse(path, headers=headers)

        def runner(app: Any, *args: Any, **kwargs: Any):
            if ("GET", "/government-v183/{name}") not in _route_keys(app):
                app.router.add_get("/government-v183/{name}", asset)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_v183
