from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import government_mandate_luxury_v147 as luxury
import government_v127 as gov

from government_reality_v182_common import VERSION
from government_reality_v182_map import enhance_map_state_v182

APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "reality-v182-map.js"
ASSET_CSS = APP_DIR / "reality-v182-map.css"


def _route_keys(app: Any) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        result.add((str(getattr(route, "method", "") or "").upper(), str(getattr(resource, "canonical", "") or "")))
    return result


def _replace_map_assets(source: str) -> str:
    for version in (180, 181):
        source = re.sub(rf'\s*<link[^>]+reality-v{version}-map\.css[^>]*>\s*', "\n", source, flags=re.IGNORECASE)
        source = re.sub(rf'\s*<script[^>]+reality-v{version}-map\.js[^>]*></script>\s*', "\n", source, flags=re.IGNORECASE)
    if ASSET_CSS.name not in source:
        source = source.replace("</head>", f'  <link rel="stylesheet" href="/government-v182/{ASSET_CSS.name}?v=182">\n</head>')
    if ASSET_JS.name not in source:
        source = source.replace("</body>", f'  <script src="/government-v182/{ASSET_JS.name}?v=182"></script>\n</body>')
    return source


def install_government_reality_v182(core: Any) -> None:
    if getattr(core, "_government_reality_v182_installed", False):
        return
    core._government_reality_v182_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION

    previous_state = gov._state

    async def state_v182(core_arg: Any, bot: Any, chat_id: int, user_id: int):
        payload = await previous_state(core_arg, bot, int(chat_id), int(user_id))
        base_map = dict((payload.get("reality181") or {}).get("map") or (payload.get("reality180") or {}).get("map") or {})
        payload["version"] = VERSION
        payload["reality182"] = {"map": enhance_map_state_v182(base_map, int(chat_id))}
        return payload

    gov._state = state_v182

    previous_inject = luxury._inject_assets

    def inject_v182(source: str) -> str:
        return _replace_map_assets(previous_inject(source))

    luxury._inject_assets = inject_v182

    original_start = core.start_webapp_server

    async def start_v182(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты карты государства Reality 182")
        original_runner = core.web.AppRunner

        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            path = ASSET_JS if name == ASSET_JS.name else ASSET_CSS if name == ASSET_CSS.name else None
            if path is None:
                raise core.web.HTTPNotFound()
            return core.web.FileResponse(path, headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Government-Reality": "182-map",
            })

        def runner(app: Any, *args: Any, **kwargs: Any):
            if ("GET", "/government-v182/{name}") not in _route_keys(app):
                app.router.add_get("/government-v182/{name}", asset)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_v182
