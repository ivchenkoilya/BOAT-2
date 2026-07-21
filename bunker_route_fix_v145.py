from __future__ import annotations

import secrets
import time
from typing import Any, Awaitable, Callable

from aiohttp import web

import bunker_game_v144 as bunker


VERSION = "Reality 145 · Direct Bunker Routes"
_UNLOCK_TOKENS: dict[str, int] = {}


def _route_exists(app: web.Application, method: str, path: str) -> bool:
    expected_method = method.upper()
    for route in app.router.routes():
        canonical = getattr(route.resource, "canonical", None)
        if canonical == path and str(route.method).upper() == expected_method:
            return True
    return False


def _add_get(
    app: web.Application,
    path: str,
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]],
) -> None:
    if not _route_exists(app, "GET", path):
        app.router.add_get(path, handler)


def _add_post(
    app: web.Application,
    path: str,
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]],
) -> None:
    if not _route_exists(app, "POST", path):
        app.router.add_post(path, handler)


def install_bunker_route_fix_v145(core: Any) -> None:
    """Финально регистрирует маршруты «Бункера» в итоговом aiohttp-приложении."""
    if getattr(core, "_bunker_route_fix_v145_installed", False):
        return
    core._bunker_route_fix_v145_installed = True

    def response_headers() -> dict[str, str]:
        return {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Bunker-Game": VERSION,
        }

    async def bunker_index(_: web.Request) -> web.StreamResponse:
        page = bunker.GAME_PATH / "index.html"
        if not page.is_file():
            raise web.HTTPNotFound(text="Файл игры «Бункер» не найден.")
        return core.web.FileResponse(page, headers=response_headers())

    async def unlock_bunker(request: web.Request) -> web.StreamResponse:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        pin = str(payload.get("pin") or "").strip()
        if pin != bunker.ADMIN_PIN:
            return core.web.json_response(
                {"ok": False, "reason": "Неверный PIN-код."},
                status=403,
                headers=response_headers(),
            )
        now = int(time.time())
        token = secrets.token_urlsafe(24)
        _UNLOCK_TOKENS[token] = now + 12 * 60 * 60
        for key, expires_at in list(_UNLOCK_TOKENS.items()):
            if expires_at <= now:
                _UNLOCK_TOKENS.pop(key, None)
        return core.web.json_response(
            {"ok": True, "token": token, "version": VERSION},
            headers=response_headers(),
        )

    async def verify_bunker(request: web.Request) -> web.StreamResponse:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        token = str(payload.get("token") or "")
        valid = bool(token and _UNLOCK_TOKENS.get(token, 0) > int(time.time()))
        return core.web.json_response(
            {"ok": valid, "version": VERSION},
            status=200 if valid else 403,
            headers=response_headers(),
        )

    async def bunker_health(_: web.Request) -> web.StreamResponse:
        page = bunker.GAME_PATH / "index.html"
        return core.web.json_response(
            {
                "ok": page.is_file(),
                "version": VERSION,
                "page": str(page.name),
            },
            status=200 if page.is_file() else 500,
            headers=response_headers(),
        )

    original_start_server = core.start_webapp_server

    async def start_server_with_direct_bunker_routes(bot: Any):
        previous_application = core.web.Application

        def application_factory(*args: Any, **kwargs: Any):
            app = previous_application(*args, **kwargs)

            for path in (
                "/games/bunker",
                "/games/bunker/",
                "/games/bunker/index.html",
                "/bunker",
                "/bunker/",
            ):
                _add_get(app, path, bunker_index)

            for path in (
                "/games/bunker/api/unlock",
                "/bunker/api/unlock",
            ):
                _add_post(app, path, unlock_bunker)

            for path in (
                "/games/bunker/api/verify",
                "/bunker/api/verify",
            ):
                _add_post(app, path, verify_bunker)

            for path in (
                "/games/bunker/health",
                "/bunker/health",
            ):
                _add_get(app, path, bunker_health)

            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = previous_application

    core.start_webapp_server = start_server_with_direct_bunker_routes
