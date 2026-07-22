from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import government_mandate_luxury_v147 as luxury


VERSION = "Reality 155 · Подкуп голосов"
APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "election-bribe-label-v155.js"


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


def _inject_asset(previous_inject: Callable[[str], str], source: str) -> str:
    source = previous_inject(source)
    if "election-bribe-label-v155.js" not in source:
        source = source.replace(
            "</body>",
            '  <script src="/government-v155/election-bribe-label-v155.js?v=155"></script>\n</body>',
        )
    return source


def install_government_election_bribe_label_v155(core: Any) -> None:
    if getattr(core, "_government_election_bribe_label_v155_installed", False):
        return
    core._government_election_bribe_label_v155_installed = True
    core.GOVERNMENT_VERSION = VERSION

    previous_inject = luxury._inject_assets

    def inject_with_bribe_label(source: str) -> str:
        return _inject_asset(previous_inject, source)

    luxury._inject_assets = inject_with_bribe_label

    original_start = core.start_webapp_server

    async def start_with_bribe_label(bot: Any):
        if not ASSET_JS.is_file():
            raise RuntimeError("Не найден интерфейс названия подкупа голосов Reality 155")
        original_runner = core.web.AppRunner

        async def asset(_: Any):
            return core.web.FileResponse(
                ASSET_JS,
                headers={
                    "Cache-Control": "no-store",
                    "X-Government-Election-Bribe-Label": "155",
                },
            )

        def runner_with_bribe_label(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            path = "/government-v155/election-bribe-label-v155.js"
            if ("GET", path) not in keys:
                app.router.add_get(path, asset)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_bribe_label
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_bribe_label
