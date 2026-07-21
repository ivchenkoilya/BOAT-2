from __future__ import annotations

from typing import Any

import admin_government_market_v132 as admin_market
import government_v127 as gov


VERSION = "Reality 140 · Рабочий запуск выборов"
ELECTION_ACTIONS = {
    "election_start_now",
    "start_election_now",
    "election_now",
}
ELECTED_OFFICES = {"president", "deputy", "chair"}


def install_admin_election_action_fix_v140(core: Any) -> None:
    """Подключает запуск выборов к фактическому aiohttp-приложению.

    Старые версии добавляли middleware через core.web.Application. В длинной
    цепочке обёрток админ-центра этот middleware мог не попадать в итоговый app,
    поэтому запрос доходил до Reality 132 и отвечал «Неизвестное действие».
    Здесь middleware добавляется непосредственно перед созданием AppRunner.
    """
    if getattr(core, "_admin_election_action_fix_v140_installed", False):
        return
    core._admin_election_action_fix_v140_installed = True
    core.ADMIN_ELECTION_ACTION_VERSION = VERSION

    original_start = core.start_webapp_server

    async def start_with_election_action(bot: Any):
        original_runner = core.web.AppRunner

        @core.web.middleware
        async def election_action(request: Any, handler: Any):
            path = str(request.path or "").rstrip("/")
            if request.method.upper() != "POST" or path != "/admin-v132/api/action":
                return await handler(request)

            try:
                data = await request.json()
                if not isinstance(data, dict):
                    data = {}
            except Exception:
                data = {}

            action = str(data.get("action") or "").strip().casefold()
            if action not in ELECTION_ACTIONS:
                return await handler(request)

            try:
                admin = admin_market._auth(core, request)
                chat_id = admin_market._as_int(data.get("chat_id"))
                office_key = str(data.get("office_key") or "president").strip().casefold()

                if chat_id >= 0:
                    raise ValueError("Сначала выбери групповую беседу.")
                if office_key not in ELECTED_OFFICES:
                    raise ValueError("Для этой должности выборы не проводятся.")

                election_id = await gov._start_election(
                    core,
                    request.app["bot"],
                    chat_id,
                    office_key,
                    int(admin.id),
                )
                spec = gov.OFFICES[office_key]
                message = (
                    f"Выборы «{spec['title']}» запущены. "
                    "Этап выдвижения кандидатов открыт."
                )
                await admin_market._log_admin(
                    core,
                    int(admin.id),
                    chat_id,
                    0,
                    "election_start_now",
                    message,
                    {"office_key": office_key, "election_id": election_id},
                )
                return core.web.json_response(
                    {
                        "ok": True,
                        "message": message,
                        "election_id": election_id,
                    }
                )
            except PermissionError as exc:
                return core.web.json_response(
                    {"ok": False, "reason": str(exc)},
                    status=403,
                )
            except Exception as exc:
                core.logging.exception("Ошибка запуска выборов Reality 140")
                return core.web.json_response(
                    {"ok": False, "reason": str(exc)},
                    status=400,
                )

        def runner_with_election_action(app: Any, *args: Any, **kwargs: Any):
            if not getattr(app, "_reality140_election_action", False):
                app.middlewares.insert(0, election_action)
                app._reality140_election_action = True
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_election_action
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_election_action
