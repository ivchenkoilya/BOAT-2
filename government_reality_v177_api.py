from __future__ import annotations

from typing import Any

import government_programs_property_v176 as reality176
import government_programs_property_v176_state as state176
import government_v127 as gov

from government_reality_v177_programs import emergency_transfer, run_program
from government_reality_v177_property import (
    bid_voluntary,
    buy_property,
    insure_property,
    pay_property_debt,
    sell_to_state,
    set_primary,
    start_voluntary_auction,
    upgrade_property,
)
from government_reality_v177_ratings import rate_official

ROUTE = "/government-v177/api/extended-action"


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


def install_government_reality_v177_api(core: Any) -> None:
    if getattr(core, "_government_reality_v177_api_installed", False):
        return
    core._government_reality_v177_api_installed = True

    async def action_api(request: Any):
        try:
            user, chat_id, data = await gov._auth(core, request)
            actor_id = int(user.id)
            action = str(data.get("action") or "")
            bot = request.app["bot"]

            if action == "program_start":
                message = await run_program(core, bot, int(chat_id), actor_id, data)
            elif action == "official_rate":
                message = await rate_official(
                    core,
                    int(chat_id),
                    actor_id,
                    gov._as_int(data.get("target_user_id")),
                    gov._as_int(data.get("value")),
                )
            elif action == "property_buy":
                message = await buy_property(
                    core, bot, int(chat_id), actor_id, str(data.get("item_key") or "")
                )
            elif action == "property_sell":
                message = await sell_to_state(
                    core,
                    bot,
                    int(chat_id),
                    actor_id,
                    str(data.get("property_id") or ""),
                    str(data.get("request_id") or ""),
                )
            elif action == "property_auction_start":
                message = await start_voluntary_auction(
                    core,
                    bot,
                    int(chat_id),
                    actor_id,
                    str(data.get("property_id") or ""),
                    gov._as_int(data.get("start_price")),
                    str(data.get("request_id") or ""),
                )
            elif action == "property_auction_bid":
                if str(data.get("auction_type") or "state") == "voluntary":
                    message = await bid_voluntary(
                        core,
                        int(chat_id),
                        actor_id,
                        str(data.get("auction_id") or ""),
                        gov._as_int(data.get("amount")),
                    )
                else:
                    message = await reality176.bid_auction(
                        core,
                        bot,
                        int(chat_id),
                        actor_id,
                        str(data.get("auction_id") or ""),
                        gov._as_int(data.get("amount")),
                    )
            elif action == "property_upgrade":
                message = await upgrade_property(
                    core, int(chat_id), actor_id, str(data.get("property_id") or "")
                )
            elif action == "property_insure":
                message = await insure_property(
                    core, int(chat_id), actor_id, str(data.get("property_id") or "")
                )
            elif action == "property_primary":
                message = await set_primary(
                    core, int(chat_id), actor_id, str(data.get("property_id") or "")
                )
            elif action == "property_debt_pay":
                message = await pay_property_debt(
                    core,
                    bot,
                    int(chat_id),
                    actor_id,
                    str(data.get("property_id") or ""),
                )
            elif action == "declaration_refresh":
                message = await state176.refresh_declaration(core, int(chat_id), actor_id)
            elif action == "property_investigation_open":
                message = await reality176.open_investigation(
                    core, bot, int(chat_id), actor_id, data
                )
            elif action == "property_investigation_action":
                message = await reality176.investigation_action(
                    core, bot, int(chat_id), actor_id, data
                )
            elif action == "oversight_expanded_report":
                message = await reality176.expanded_oversight_report(
                    core, bot, int(chat_id), actor_id
                )
            elif action == "emergency_transfer":
                message = await emergency_transfer(core, bot, int(chat_id), actor_id)
            else:
                raise ValueError("Неизвестное действие Reality 177.")

            return core.web.json_response({"ok": True, "message": message})
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    original_start = core.start_webapp_server

    async def start_with_extended_api(bot: Any):
        original_runner = core.web.AppRunner

        def runner(app: Any, *args: Any, **kwargs: Any):
            if ("POST", ROUTE) not in _route_keys(app):
                app.router.add_post(ROUTE, action_api)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_extended_api
