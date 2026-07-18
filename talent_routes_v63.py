from __future__ import annotations

from typing import Any

from aiohttp import web

import talent_improvements_v66
import talent_mastery
import talent_system


def install_talent_routes_v63(core: Any) -> None:
    """Подключает окончательные маршруты расширенного Mini App древа.

    Admin Mini App создаёт собственный aiohttp.Application, поэтому все маршруты
    древа добавляются поверх него одним финальным слоем. Страница отдаётся через
    core.web.FileResponse: это важно, потому что talent_ux встраивает туда
    расширенное древо, мастерство и интерфейс Reality 66.
    """
    if getattr(core, "_talent_routes_v66_installed", False):
        return
    core._talent_routes_v66_installed = True

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

    async def auth_payload(
        request: web.Request,
    ) -> tuple[Any, int, dict[str, Any]]:
        user, start_param = core._webapp_auth(request)
        if user is None:
            raise PermissionError(start_param or "Нет авторизации.")
        payload = await core._webapp_json(request)
        chat_id = parse_chat_id(start_param, payload, request)
        if chat_id is None:
            raise ValueError("Не найдена беседа.")
        if await core.db.get_player(chat_id, user.id) is None:
            raise PermissionError(
                "Сначала открой древо командой /talents в нужной беседе."
            )
        return user, chat_id, payload

    def api_exception(error: Exception) -> web.Response:
        status = 403 if isinstance(error, PermissionError) else 400
        return core._webapp_error(str(error), status)

    async def talent_index(request: web.Request) -> web.StreamResponse:
        # core.web.FileResponse заменён talent_ux и встраивает все актуальные
        # CSS/JS-слои. aiohttp.web.FileResponse здесь использовать нельзя.
        return core.web.FileResponse(
            talent_system.TALENT_DIR / "index.html",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Talent-UI": "reality-66",
            },
        )

    async def talent_session(request: web.Request) -> web.Response:
        try:
            user, chat_id, _ = await auth_payload(request)
            return web.json_response(
                await talent_system.talent_state(core.db, chat_id, user.id)
            )
        except (PermissionError, ValueError) as error:
            return api_exception(error)

    async def talent_upgrade(request: web.Request) -> web.Response:
        try:
            user, chat_id, payload = await auth_payload(request)
            state = await talent_system.upgrade_skill(
                core.db,
                chat_id,
                user.id,
                str(payload.get("skill_id") or ""),
            )
            return web.json_response(state)
        except (PermissionError, ValueError) as error:
            return api_exception(error)

    async def talent_activate(request: web.Request) -> web.Response:
        try:
            user, chat_id, payload = await auth_payload(request)
            result = await talent_mastery._activate_ability(
                core.db,
                chat_id,
                user.id,
                str(payload.get("ability_id") or ""),
            )
            result["state"] = await talent_system.talent_state(
                core.db, chat_id, user.id
            )
            return web.json_response(result)
        except (PermissionError, ValueError) as error:
            return api_exception(error)

    async def talent_save_build(request: web.Request) -> web.Response:
        try:
            user, chat_id, payload = await auth_payload(request)
            builds = await talent_mastery._save_build(
                core.db,
                chat_id,
                user.id,
                int(payload.get("slot") or 0),
                str(payload.get("name") or ""),
            )
            return web.json_response({"ok": True, "builds": builds})
        except (PermissionError, ValueError) as error:
            return api_exception(error)

    async def talent_load_build(request: web.Request) -> web.Response:
        try:
            user, chat_id, payload = await auth_payload(request)
            state = await talent_mastery._load_build(
                core.db,
                chat_id,
                user.id,
                int(payload.get("slot") or 0),
            )
            return web.json_response(state)
        except (PermissionError, ValueError) as error:
            return api_exception(error)

    async def talent_reset(request: web.Request) -> web.Response:
        try:
            user, chat_id, _ = await auth_payload(request)
            state = await talent_mastery._reset_build(
                core,
                core.db,
                chat_id,
                user.id,
            )
            return web.json_response(state)
        except (PermissionError, ValueError) as error:
            return api_exception(error)

    async def talent_community_upgrade(request: web.Request) -> web.Response:
        try:
            _, chat_id, payload = await auth_payload(request)
            community = await talent_mastery._community_upgrade(
                core.db,
                chat_id,
                str(payload.get("skill_id") or ""),
            )
            return web.json_response({"ok": True, "community": community})
        except (PermissionError, ValueError) as error:
            return api_exception(error)

    async def talent_focus(request: web.Request) -> web.Response:
        try:
            user, chat_id, payload = await auth_payload(request)
            state = await talent_improvements_v66.set_focus(
                core.db,
                chat_id,
                user.id,
                str(payload.get("branch") or ""),
            )
            return web.json_response(state)
        except (PermissionError, ValueError) as error:
            return api_exception(error)

    async def start_server_with_talent_routes(bot: Any):
        def application_factory(*args: Any, **kwargs: Any):
            app = original_application(*args, **kwargs)
            app.router.add_get("/talents", talent_index)
            app.router.add_get("/talents/", talent_index)
            app.router.add_get("/talents/index.html", talent_index)
            app.router.add_post("/talents/api/session", talent_session)
            app.router.add_post("/talents/api/upgrade", talent_upgrade)
            app.router.add_post("/talents/api/activate", talent_activate)
            app.router.add_post("/talents/api/save-build", talent_save_build)
            app.router.add_post("/talents/api/load-build", talent_load_build)
            app.router.add_post("/talents/api/reset", talent_reset)
            app.router.add_post(
                "/talents/api/community-upgrade",
                talent_community_upgrade,
            )
            app.router.add_post("/talents/api/focus", talent_focus)
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = original_application

    core.start_webapp_server = start_server_with_talent_routes
