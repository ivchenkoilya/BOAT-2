from __future__ import annotations

from pathlib import Path
from typing import Any

import finance_investments_v127_core as finance
import government_crisis_v131 as crisis
import government_mandate_luxury_v147 as luxury


VERSION = "Reality 161 · Защита казны и живое обновление"
GOVERNMENT_ASSET = Path(__file__).resolve().parent / "governmentapp_v127" / "government-realtime-v161.js"
FINANCE_ASSET = Path(__file__).resolve().parent / "financeapp_v127" / "finance-realtime-v161.js"


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


def _finance_html() -> str:
    source = (finance.APP_DIR / "index.html").read_text(encoding="utf-8")
    if FINANCE_ASSET.name not in source:
        source = source.replace(
            "</body>",
            f'  <script src="/finance-v161/{FINANCE_ASSET.name}?v=161"></script>\n</body>',
        )
    return source


def install_government_realtime_guard_v161(core: Any) -> None:
    if getattr(core, "_government_realtime_guard_v161_installed", False):
        return
    core._government_realtime_guard_v161_installed = True
    core.GOVERNMENT_VERSION = VERSION

    previous_start_theft = crisis._start_theft

    async def start_theft_for_officials_only(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
        percent: int,
    ) -> str:
        offices = await crisis._offices(core_arg, int(chat_id), int(user_id))
        if not offices:
            raise PermissionError(
                "Операции с государственной казной доступны только действующим чиновникам. "
                "Статус кандидата не является государственной должностью."
            )
        return await previous_start_theft(
            core_arg,
            bot,
            int(chat_id),
            int(user_id),
            int(percent),
        )

    crisis._start_theft = start_theft_for_officials_only

    previous_serialize_crisis = crisis._serialize_crisis

    async def serialize_crisis_with_treasury_guard(
        core_arg: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        payload = await previous_serialize_crisis(core_arg, int(chat_id), int(user_id))
        offices = list(payload.get("offices") or [])
        official = bool(offices)
        theft = payload.setdefault("theft", {})
        theft["requires_active_office"] = True
        theft["can_attempt"] = bool(official and theft.get("can_attempt"))
        if not official:
            theft["rules"] = []
            theft["remaining"] = "нужна действующая государственная должность"
            theft["denial_reason"] = (
                "Кандидат ещё не является чиновником и не имеет доступа к казне."
            )
        return payload

    crisis._serialize_crisis = serialize_crisis_with_treasury_guard

    previous_inject = luxury._inject_assets

    def inject_government_realtime(source: str) -> str:
        source = previous_inject(source)
        if GOVERNMENT_ASSET.name not in source:
            source = source.replace(
                "</body>",
                f'  <script src="/government-v161/{GOVERNMENT_ASSET.name}?v=161"></script>\n</body>',
            )
        return source

    luxury._inject_assets = inject_government_realtime

    original_start = core.start_webapp_server

    async def start_with_realtime_guard(bot: Any):
        if not GOVERNMENT_ASSET.is_file() or not FINANCE_ASSET.is_file():
            raise RuntimeError("Не найдены ассеты живого обновления Reality 161")

        original_runner = core.web.AppRunner

        @core.web.middleware
        async def finance_realtime_middleware(request: Any, handler: Any):
            path = str(request.path or "").rstrip("/") or "/"
            start_param = str(
                request.query.get("tgWebAppStartParam")
                or request.query.get("startapp")
                or ""
            )
            is_finance_entry = path in {"/finance-v127", "/finance-v127/index.html"}
            if request.method.upper() == "GET" and (
                is_finance_entry or start_param.startswith("finance_")
            ):
                return core.web.Response(
                    text=_finance_html(),
                    content_type="text/html",
                    charset="utf-8",
                    headers={
                        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                        "Pragma": "no-cache",
                        "Expires": "0",
                        "X-Finance-Realtime": "161",
                    },
                )
            return await handler(request)

        async def government_asset(_: Any):
            return core.web.FileResponse(
                GOVERNMENT_ASSET,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Government-Realtime": "161",
                },
            )

        async def finance_asset(_: Any):
            return core.web.FileResponse(
                FINANCE_ASSET,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Finance-Realtime": "161",
                },
            )

        def runner(app: Any, *args: Any, **kwargs: Any):
            app.middlewares.insert(0, finance_realtime_middleware)
            keys = _route_keys(app)
            government_path = f"/government-v161/{GOVERNMENT_ASSET.name}"
            finance_path = f"/finance-v161/{FINANCE_ASSET.name}"
            if ("GET", government_path) not in keys:
                app.router.add_get(government_path, government_asset)
            if ("GET", finance_path) not in keys:
                app.router.add_get(finance_path, finance_asset)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_realtime_guard
