from __future__ import annotations

from typing import Any

from aiohttp import web

import talent_system


def install_talent_routes_v63(core: Any) -> None:
    """Возвращает HTTP-маршруты древа после установки Admin Mini App.

    Reality 62 создаёт собственный aiohttp.Application. Из-за этого маршруты,
    которые talent_system добавлял к предыдущему серверу, больше не попадали в
    итоговое приложение и /talents/ отвечал 404. Этот патч добавляет их к уже
    окончательному серверу, не затрагивая рейд и админ-центр.
    """
    if getattr(core, "_talent_routes_v63_installed", False):
        return
    core._talent_routes_v63_installed = True

    original_start_server = core.start_webapp_server
    original_application = core.web.Application

    def parse_chat_id(
        start_param: str | None,
        payload: dict[str, Any],
        request: web.Request,
    ) -> int | None:
        raw = str(start_param or "")
        if raw.startswith(talent_system.TALENT_PREFIX):
            raw = raw[len(talent_system.TALENT_PREFIX):]
        else:
            raw = str(
                payload.get("chat_id")
                or request.query.get("chat_id")
                or ""
            )
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    async def talent_index(request: web.Request) -> web.StreamResponse:
        return web.FileResponse(
            talent_system.TALENT_DIR / "index.html",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    async def talent_session(request: web.Request) -> web.Response:
        user, start_param = core._webapp_auth(request)
        if user is None:
            return core._webapp_error(start_param or "Нет авторизации.", 401)

        payload = await core._webapp_json(request)
        chat_id = parse_chat_id(start_param, payload, request)
        if chat_id is None:
            return core._webapp_error("Не найдена беседа.")

        player = await core.db.get_player(chat_id, user.id)
        if player is None:
            return core._webapp_error(
                "Сначала открой древо командой /talents в нужной беседе.",
                403,
            )

        return web.json_response(
            await talent_system.talent_state(core.db, chat_id, user.id)
        )

    async def talent_upgrade(request: web.Request) -> web.Response:
        user, start_param = core._webapp_auth(request)
        if user is None:
            return core._webapp_error(start_param or "Нет авторизации.", 401)

        payload = await core._webapp_json(request)
        chat_id = parse_chat_id(start_param, payload, request)
        if chat_id is None:
            return core._webapp_error("Не найдена беседа.")
        if await core.db.get_player(chat_id, user.id) is None:
            return core._webapp_error(
                "Игрок не найден в этой беседе.",
                403,
            )

        try:
            state = await talent_system.upgrade_skill(
                core.db,
                chat_id,
                user.id,
                str(payload.get("skill_id") or ""),
            )
        except ValueError as error:
            return core._webapp_error(str(error))

        return web.json_response(state)

    async def start_server_with_talent_routes(bot: Any):
        def application_factory(*args: Any, **kwargs: Any):
            app = original_application(*args, **kwargs)
            app.router.add_get("/talents", talent_index)
            app.router.add_get("/talents/", talent_index)
            app.router.add_get("/talents/index.html", talent_index)
            app.router.add_post("/talents/api/session", talent_session)
            app.router.add_post("/talents/api/upgrade", talent_upgrade)
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = original_application

    core.start_webapp_server = start_server_with_talent_routes
