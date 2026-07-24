from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import government_mandate_luxury_v147 as luxury
import government_v127 as gov

from government_reality_v181_common import VERSION
from government_reality_v181_map import enhance_map_state

APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "reality-v181-map.js"
ASSET_CSS = APP_DIR / "reality-v181-map.css"


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


def _replace_map_assets(source: str) -> str:
    source = re.sub(
        r'\s*<link[^>]+reality-v180-map\.css[^>]*>\s*',
        "\n",
        source,
        flags=re.IGNORECASE,
    )
    source = re.sub(
        r'\s*<script[^>]+reality-v180-map\.js[^>]*></script>\s*',
        "\n",
        source,
        flags=re.IGNORECASE,
    )
    if ASSET_CSS.name not in source:
        source = source.replace(
            "</head>",
            f'  <link rel="stylesheet" href="/government-v181/{ASSET_CSS.name}?v=181">\n</head>',
        )
    if ASSET_JS.name not in source:
        source = source.replace(
            "</body>",
            f'  <script src="/government-v181/{ASSET_JS.name}?v=181"></script>\n</body>',
        )
    return source


def install_government_reality_v181(core: Any) -> None:
    if getattr(core, "_government_reality_v181_installed", False):
        return
    core._government_reality_v181_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION

    previous_state = gov._state

    async def state_v181(core_arg: Any, bot: Any, chat_id: int, user_id: int):
        payload = await previous_state(core_arg, bot, int(chat_id), int(user_id))
        base_map = dict((payload.get("reality180") or {}).get("map") or {})
        payload["version"] = VERSION
        payload["reality181"] = {
            "map": enhance_map_state(base_map, int(chat_id)),
        }
        return payload

    gov._state = state_v181

    previous_inject = luxury._inject_assets

    def inject_v181(source: str) -> str:
        return _replace_map_assets(previous_inject(source))

    luxury._inject_assets = inject_v181

    original_start = core.start_webapp_server

    async def start_v181(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты карты государства Reality 181")
        original_runner = core.web.AppRunner

        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            path = ASSET_JS if name == ASSET_JS.name else ASSET_CSS if name == ASSET_CSS.name else None
            if path is None:
                raise core.web.HTTPNotFound()
            return core.web.FileResponse(
                path,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Government-Reality": "181-map",
                },
            )

        def runner(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/government-v181/{name}") not in keys:
                app.router.add_get("/government-v181/{name}", asset)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_v181
