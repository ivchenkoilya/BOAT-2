from __future__ import annotations

from pathlib import Path
from typing import Any

import government_crisis_v131 as crisis
import government_election_shadow_v153 as shadow
import government_mandate_luxury_v147 as luxury
import government_v127 as gov
from government_theft_quest_v163_core import (
    VERSION,
    accuse,
    backfill_pending,
    cover_action,
    create_case,
    delegate_task,
    ensure_schema,
    mark_caught,
    perform_task,
    resolve_escape,
    serialize,
)


ASSET_JS = Path(__file__).resolve().parent / "governmentapp_v127" / "theft-quest-v163.js"
ASSET_CSS = Path(__file__).resolve().parent / "governmentapp_v127" / "theft-quest-v163.css"


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


async def _legacy_investigation_disabled(*_args: Any, **_kwargs: Any) -> str:
    raise ValueError(
        "Быстрая проверка отключена. Открой уголовное дело Reality 163 и пройди этап своей структуры."
    )


def install_government_theft_quest_v163(core: Any) -> None:
    if getattr(core, "_government_theft_quest_v163_installed", False):
        return
    core._government_theft_quest_v163_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION

    original_connect = core.Database.connect

    async def connect_with_theft_quest(self: Any) -> None:
        await original_connect(self)
        core.db._government_theft_quest_v163_schema = False
        await ensure_schema(core)
        await backfill_pending(core)

    core.Database.connect = connect_with_theft_quest

    previous_start_theft = crisis._start_theft

    async def start_theft_with_case(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
        percent: int,
    ) -> str:
        before = gov._now()
        message = await previous_start_theft(
            core_arg,
            bot,
            int(chat_id),
            int(user_id),
            int(percent),
        )
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT * FROM government_thefts_v131
            WHERE chat_id=? AND thief_id=? AND status='pending' AND started_at>=?
            ORDER BY started_at DESC LIMIT 1
            """,
            (int(chat_id), int(user_id), int(before)),
        )
        theft = await cursor.fetchone()
        if theft is not None:
            await create_case(core_arg, theft)
            return message + " Открыто уголовное дело с четырьмя отдельными этапами расследования."
        return message

    crisis._start_theft = start_theft_with_case

    previous_catch_theft = crisis._catch_theft

    async def catch_theft_with_case(
        core_arg: Any,
        bot: Any,
        theft: Any,
        investigator_id: int,
        immediate: bool = False,
    ) -> None:
        await previous_catch_theft(
            core_arg,
            bot,
            theft,
            int(investigator_id),
            immediate=bool(immediate),
        )
        await mark_caught(core_arg, str(theft["theft_id"]))

    crisis._catch_theft = catch_theft_with_case

    previous_resolve_theft = crisis._resolve_theft

    async def resolve_theft_with_case(core_arg: Any, bot: Any, theft: Any) -> None:
        if await resolve_escape(core_arg, bot, theft):
            return
        await previous_resolve_theft(core_arg, bot, theft)

    crisis._resolve_theft = resolve_theft_with_case

    # Старые обработчики давали мгновенный шанс раскрытия одной кнопкой.
    # Они остаются зарегистрированными ради совместимости маршрутов, но теперь
    # всегда направляют пользователя в полноценное уголовное дело.
    crisis._investigate_theft = _legacy_investigation_disabled
    shadow._investigate_theft_v153 = _legacy_investigation_disabled

    previous_state = gov._state

    async def state_with_theft_quest(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        payload = await previous_state(core_arg, bot, int(chat_id), int(user_id))
        payload["version"] = VERSION
        payload["theft_quest_v163"] = await serialize(core_arg, int(chat_id), int(user_id))
        shadow_state = payload.get("election_shadow_v153")
        if isinstance(shadow_state, dict):
            shadow_state["theft_cases"] = []
        crisis_state = payload.get("crisis_v131")
        if isinstance(crisis_state, dict):
            theft_state = crisis_state.get("theft")
            if isinstance(theft_state, dict):
                for item in theft_state.get("items") or []:
                    if isinstance(item, dict) and str(item.get("status") or "") == "pending":
                        item["can_investigate"] = False
        return payload

    gov._state = state_with_theft_quest

    previous_inject = luxury._inject_assets

    def inject_theft_quest(source: str) -> str:
        source = previous_inject(source)
        if ASSET_CSS.name not in source:
            source = source.replace(
                "</head>",
                f'  <link rel="stylesheet" href="/government-v163/{ASSET_CSS.name}?v=163">\n</head>',
            )
        if ASSET_JS.name not in source:
            source = source.replace(
                "</body>",
                f'  <script src="/government-v163/{ASSET_JS.name}?v=163"></script>\n</body>',
            )
        return source

    luxury._inject_assets = inject_theft_quest

    async def action_api(request: Any):
        try:
            user, chat_id, data = await gov._auth(core, request)
            user_id = int(user.id)
            action = str(data.get("action") or "")
            bot = request.app["bot"]
            if action == "quest_task":
                message = await perform_task(
                    core,
                    chat_id,
                    user_id,
                    str(data.get("theft_id") or ""),
                    str(data.get("office_key") or ""),
                    data,
                )
            elif action == "quest_accuse":
                raw_evidence = data.get("evidence_keys") or []
                evidence_keys = raw_evidence if isinstance(raw_evidence, list) else [raw_evidence]
                message = await accuse(
                    core,
                    bot,
                    chat_id,
                    user_id,
                    str(data.get("theft_id") or ""),
                    int(data.get("suspect_id") or 0),
                    [str(value) for value in evidence_keys],
                )
            elif action == "quest_cover":
                message = await cover_action(
                    core,
                    chat_id,
                    user_id,
                    str(data.get("theft_id") or ""),
                    str(data.get("action_key") or ""),
                    int(data.get("target_id") or 0),
                )
            elif action == "quest_delegate":
                message = await delegate_task(
                    core,
                    chat_id,
                    user_id,
                    str(data.get("theft_id") or ""),
                    str(data.get("office_key") or ""),
                    int(data.get("target_id") or 0),
                )
            else:
                raise ValueError("Неизвестное действие уголовного дела Reality 163.")
            return core.web.json_response({"ok": True, "message": message})
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    original_start_server = core.start_webapp_server

    async def start_with_theft_quest(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты уголовного дела Reality 163")
        original_runner = core.web.AppRunner

        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            path = ASSET_JS if name == ASSET_JS.name else ASSET_CSS if name == ASSET_CSS.name else None
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
                    "X-Government-Theft-Quest": "163",
                },
            )

        def runner_with_theft_quest(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/government-v163/{name}") not in keys:
                app.router.add_get("/government-v163/{name}", asset)
            if ("POST", "/government-v163/api/action") not in keys:
                app.router.add_post("/government-v163/api/action", action_api)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_theft_quest
        try:
            return await original_start_server(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_theft_quest
