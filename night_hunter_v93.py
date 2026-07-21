from __future__ import annotations

from pathlib import Path
from typing import Any

from aiohttp import web

import game_center_v75 as base


VERSION = "Reality 118 · Standalone Factory Escape"
GAME_KEY = "night-hunter"
GAME_PATH = Path(__file__).resolve().parent / "games" / GAME_KEY
STYLE_FILENAMES = (
    "style-v108.css",
    "style-v110.css",
    "style-v115.css",
    "style-v116.css",
    "style-v117.css",
    "style-v118.css",
)
SCRIPT_FILENAMES = (
    "game-v108.js",
    "game-v109.js",
    "game-v110.js",
    "game-v113.js",
    "game-v115.js",
    "game-v116.js",
    "game-v115-loader.js",
    "game-v115-ui.js",
    "game-v115-access.js",
    "horror-v117.js",
    "escape-v118.js",
)
ASSET_FILENAMES = (
    "assets/machine-cnc-blue-v114.svg",
    "assets/machine-cnc-green-v114.svg",
    "assets/machine-cnc-red-v114.svg",
    "assets/machine-laser-v114.svg",
    "assets/machine-press-v114.svg",
    "assets/machine-zero-v114.svg",
)


def install_night_hunter_v93(core: Any) -> None:
    """Подключает самостоятельную игру «Сбежать с завода»."""
    if getattr(core, "_night_hunter_v93_installed", False):
        return
    core._night_hunter_v93_installed = True

    base.GAME_INFO[GAME_KEY] = {
        "title": "Сбежать с завода: 50 заказов до свободы",
        "emoji": "🏭",
        "duration": 1200,
        "max_reward": 180,
    }

    previous_reward = base._base_reward

    def reward_with_night_hunter(game_key: str, score: int) -> int:
        if game_key != GAME_KEY:
            return previous_reward(game_key, score)
        value = max(0, int(score))
        if value <= 0:
            return 0
        if value < 450:
            return 15
        if value < 900:
            return 45
        if value < 1400:
            return 80
        if value < 2000:
            return 120
        if value < 2700:
            return 150
        return 180

    base._base_reward = reward_with_night_hunter

    def response_headers() -> dict[str, str]:
        return {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Night-Hunter": VERSION,
        }

    def file_response(path: Path) -> web.FileResponse:
        return core.web.FileResponse(path, headers=response_headers())

    async def night_index(_: web.Request) -> web.StreamResponse:
        html = (GAME_PATH / "index.html").read_text(encoding="utf-8")
        html = html.replace("Ночной охотник: Последняя смена", "Сбежать с завода: 50 заказов до свободы")
        html = html.replace("ALIVSPORT", "ALIV GYM")
        html = html.replace(
            "REALITY 117 · HORROR CUT · В РАЗРАБОТКЕ",
            "REALITY 118 · STANDALONE FACTORY ESCAPE",
        )
        html = html.replace(
            "На заводе уже началась твоя смена. Камеры показывают, что ты внутри, хотя ты всё ещё стоишь у проходной.",
            "Полный рабочий день оператора ЧПУ. Закрой 50 заказов, дождись 16:35 и решись уйти с завода самостоятельно.",
        )
        html = html.replace(
            "Все рабочие выходят с территории, но один человек стоит против потока и смотрит только на тебя.",
            "Сегодня нужно закрыть 50 заказов. Отец сказал, что потом постарается отпустить тебя в выходной.",
        )
        html = html.replace(
            "На территории уже зарегистрирован сотрудник с твоим именем.",
            "8:00. Рабочий день начался. Друзья уже обсуждают поездку с палатками.",
        )
        html = html.replace(
            '<span class="clock" id="clock">17:42</span>',
            '<span class="clock" id="clock">08:00</span>',
        )
        html = html.replace(
            "/games/night-hunter/game-v115-access.js?v=1173",
            "/games/night-hunter/game-v115-access.js?v=1187",
        )
        html = html.replace(
            "/games/night-hunter/game-v115-access.js?v=1184",
            "/games/night-hunter/game-v115-access.js?v=1187",
        )
        if "style-v118.css" not in html:
            html = html.replace(
                "</head>",
                '  <link rel="stylesheet" href="/games/night-hunter/style-v118.css?v=1187">\n</head>',
            )
        return core.web.Response(
            text=html,
            content_type="text/html",
            charset="utf-8",
            headers=response_headers(),
        )

    def make_static_handler(filename: str):
        async def static_file(_: web.Request) -> web.StreamResponse:
            return file_response(GAME_PATH / filename)

        return static_file

    original_start_server = core.start_webapp_server

    async def start_server_with_night_hunter(bot: Any):
        previous_application = core.web.Application

        def application_factory(*args: Any, **kwargs: Any):
            app = previous_application(*args, **kwargs)
            for path in (
                "/games/night-hunter",
                "/games/night-hunter/",
                "/games/night-hunter/index.html",
            ):
                app.router.add_get(path, night_index)
            for filename in STYLE_FILENAMES + SCRIPT_FILENAMES + ASSET_FILENAMES:
                app.router.add_get(
                    f"/games/night-hunter/{filename}",
                    make_static_handler(filename),
                )
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = previous_application

    core.start_webapp_server = start_server_with_night_hunter