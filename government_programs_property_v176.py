from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import finance_investments_v127 as finance_app
import finance_investments_v127_market as investment_market
import finance_investments_v127_ops as investment_ops
import government_mandate_luxury_v147 as luxury
import government_oversight_deputy_v167_actions as oversight_actions
import government_oversight_deputy_v167_data as oversight_data
import government_v127 as gov

from government_programs_property_v176_data import (
    VERSION,
    apply_anti_crisis,
    bid_auction,
    buy_property,
    enact_property_bill,
    ensure_schema,
    expanded_oversight_report,
    investigation_action,
    open_investigation,
    pay_property_debt,
    process_auctions,
    process_expired_effects,
    process_maintenance,
    programs_state,
    property_state,
    refresh_declaration,
    release_temporary_seizures,
    run_program,
    oversight_bonus,
)

APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "programs-property-v176.js"
ASSET_CSS = APP_DIR / "programs-property-v176.css"
_RUNTIME_STARTED = False


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


async def _runtime_loop(core: Any, bot: Any) -> None:
    await asyncio.sleep(12)
    while True:
        try:
            await process_maintenance(core, bot)
            await process_auctions(core, bot)
            await process_expired_effects(core, bot)
            await release_temporary_seizures(core)
        except Exception:
            core.logging.exception("Ошибка фонового цикла Reality 176")
        await asyncio.sleep(60)


def install_government_programs_property_v176(core: Any) -> None:
    global _RUNTIME_STARTED
    if getattr(core, "_government_programs_property_v176_installed", False):
        return
    core._government_programs_property_v176_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION
    gov.BILL_TYPES["property_seizure"] = {"emoji": "🔒", "title": "Временный арест имущества"}
    gov.BILL_TYPES["property_confiscation"] = {"emoji": "⚖️", "title": "Конфискация имущества"}

    original_connect = core.Database.connect

    async def connect_with_reality176(self: Any) -> None:
        await original_connect(self)
        core._government_programs_property_v176_schema_ready = False
        await ensure_schema(core)

    core.Database.connect = connect_with_reality176

    previous_state = gov._state

    async def state_with_reality176(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        payload = await previous_state(core_arg, bot, int(chat_id), int(user_id))
        payload["version"] = VERSION
        payload["reality176"] = {
            "programs": await programs_state(core_arg, int(chat_id), int(user_id)),
            "property": await property_state(core_arg, int(chat_id), int(user_id)),
        }
        return payload

    gov._state = state_with_reality176

    previous_enact_bill = gov._enact_bill

    async def enact_bill_with_property(
        core_arg: Any,
        bot: Any,
        bill: Any,
        actor_id: int,
    ) -> None:
        if str(bill["bill_type"]) in {"property_seizure", "property_confiscation"}:
            await enact_property_bill(core_arg, bot, bill, int(actor_id))
            return
        await previous_enact_bill(core_arg, bot, bill, int(actor_id))

    gov._enact_bill = enact_bill_with_property

    previous_advance_market = investment_market._advance_market

    async def advance_market_with_anti_crisis(core_arg: Any, chat_id: int) -> None:
        conn = core_arg.db._require_connection()
        before: dict[str, int] = {}
        try:
            cursor = await conn.execute(
                "SELECT symbol,price FROM finance_market_v127 WHERE chat_id=?",
                (int(chat_id),),
            )
            before = {str(row["symbol"]): int(row["price"]) for row in await cursor.fetchall()}
        except Exception:
            before = {}
        await previous_advance_market(core_arg, int(chat_id))
        await apply_anti_crisis(core_arg, int(chat_id), before)

    investment_market._advance_market = advance_market_with_anti_crisis
    investment_ops._advance_market = advance_market_with_anti_crisis
    finance_app._advance_market = advance_market_with_anti_crisis

    previous_usage = oversight_data._usage

    async def usage_with_program(
        core_arg: Any,
        chat_id: int,
        actor_id: int,
        action: str,
        period: int,
    ) -> tuple[int, int]:
        used, latest = await previous_usage(core_arg, int(chat_id), int(actor_id), str(action), int(period))
        if str(action) == "deputy_inspection":
            bonus = await oversight_bonus(core_arg, int(chat_id))
            used = max(0, int(used) - int(bonus))
        return int(used), int(latest)

    oversight_data._usage = usage_with_program
    oversight_actions._usage = usage_with_program

    previous_inject = luxury._inject_assets

    def inject_reality176(source: str) -> str:
        source = previous_inject(source)
        if ASSET_CSS.name not in source:
            source = source.replace(
                "</head>",
                f'  <link rel="stylesheet" href="/government-v176/{ASSET_CSS.name}?v=176">\n</head>',
            )
        if ASSET_JS.name not in source:
            source = source.replace(
                "</body>",
                f'  <script src="/government-v176/{ASSET_JS.name}?v=176"></script>\n</body>',
            )
        return source

    luxury._inject_assets = inject_reality176

    async def action_api(request: Any):
        try:
            user, chat_id, data = await gov._auth(core, request)
            actor_id = int(user.id)
            action = str(data.get("action") or "")
            bot = request.app["bot"]
            if action == "program_start":
                message = await run_program(core, bot, int(chat_id), actor_id, data)
            elif action == "oversight_expanded_report":
                message = await expanded_oversight_report(core, bot, int(chat_id), actor_id)
            elif action == "property_buy":
                message = await buy_property(core, bot, int(chat_id), actor_id, str(data.get("item_key") or ""))
            elif action == "property_debt_pay":
                message = await pay_property_debt(core, bot, int(chat_id), actor_id, str(data.get("property_id") or ""))
            elif action == "declaration_refresh":
                message = await refresh_declaration(core, int(chat_id), actor_id)
            elif action == "property_investigation_open":
                message = await open_investigation(core, bot, int(chat_id), actor_id, data)
            elif action == "property_investigation_action":
                message = await investigation_action(core, bot, int(chat_id), actor_id, data)
            elif action == "property_auction_bid":
                message = await bid_auction(
                    core,
                    bot,
                    int(chat_id),
                    actor_id,
                    str(data.get("auction_id") or ""),
                    gov._as_int(data.get("amount")),
                )
            else:
                raise ValueError("Неизвестное действие Reality 176.")
            return core.web.json_response({"ok": True, "message": message})
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    original_start = core.start_webapp_server

    async def start_with_reality176(bot: Any):
        global _RUNTIME_STARTED
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты Reality 176")
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
                    "X-Government-Reality": "176",
                },
            )

        def runner(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/government-v176/{name}") not in keys:
                app.router.add_get("/government-v176/{name}", asset)
            if ("POST", "/government-v176/api/action") not in keys:
                app.router.add_post("/government-v176/api/action", action_api)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner
        try:
            result = await original_start(bot)
        finally:
            core.web.AppRunner = original_runner
        if not _RUNTIME_STARTED:
            _RUNTIME_STARTED = True
            core.spawn_background_task(_runtime_loop(core, bot))
        return result

    core.start_webapp_server = start_with_reality176
