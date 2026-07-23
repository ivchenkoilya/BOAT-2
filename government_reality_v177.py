from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import government_mandate_luxury_v147 as luxury
import government_programs_property_v176_state as state176
import government_programs_property_v176_property as property176
import government_programs_property_v176_programs as programs176
import government_programs_property_v176_funds as funds176
import government_programs_property_v176_common as common176
import government_programs_property_v176 as integration176
import government_treasury_management_v164 as treasury
import government_v127 as gov

from government_reality_v177_common import PROGRAMS, VERSION, ensure_schema, json_value, program_cost
from government_reality_v177_funds import install_fund_bridge, migrate_funds, structures_state
from government_reality_v177_programs import active_effect, emergency_transfer, process_v177_effects, programs_state, run_program
from government_reality_v177_property import (
    bid_voluntary, buy_property, insure_property, pay_property_debt, process_voluntary_auctions,
    property_state_v177, sell_to_state, set_primary, start_voluntary_auction, upgrade_property, process_maintenance_v177,
)
from government_reality_v177_ratings import rate_official, ratings_state

APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "reality-v177.js"
ASSET_CSS = APP_DIR / "reality-v177.css"
_RUNTIME_STARTED = False


def _route_keys(app: Any) -> set[tuple[str, str]]:
    result = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        result.add((str(getattr(route, "method", "") or "").upper(), str(getattr(resource, "canonical", "") or "")))
    return result


async def _runtime(core: Any, bot: Any) -> None:
    await asyncio.sleep(15)
    while True:
        try:
            await process_v177_effects(core, bot)
            await process_voluntary_auctions(core, bot)
        except Exception:
            core.logging.exception("Ошибка фонового цикла Reality 177")
        await asyncio.sleep(60)


def install_government_reality_v177(core: Any) -> None:
    global _RUNTIME_STARTED
    if getattr(core, "_government_reality_v177_installed", False):
        return
    core._government_reality_v177_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION
    install_fund_bridge(core)

    # Make every server path authoritative: even a stale Reality 176 client receives
    # the four-times prices and the Reality 177 transaction/idempotency rules.
    for key in ("anti_crisis", "festival", "social_help", "oversight_operation", "market_intervention", "election_campaign"):
        common176.PROGRAMS[key].update(PROGRAMS[key])
    common176._program_cost = program_cost
    programs176._program_cost = program_cost
    funds176._program_cost = program_cost
    integration176.run_program = run_program
    integration176.buy_property = buy_property
    integration176.process_maintenance = process_maintenance_v177

    # Canonical structure balances are returned to the existing Reality 164 UI.
    treasury._structure_rows = structures_state

    # The Finance Minister may propose funding of structures, but cannot issue personal
    # payments and cannot bypass the Duma limits reserved for the President.
    original_treasury_access = treasury._access
    async def treasury_access_v177(core_arg: Any, chat_id: int, user_id: int):
        access = await original_treasury_access(core_arg, int(chat_id), int(user_id))
        offices = await gov._user_offices(core_arg, int(chat_id), int(user_id))
        is_finance = "finance" in offices
        if is_finance and not access.get("sanctioned"):
            access["can_propose"] = True
            access["can_direct"] = False
            access["is_finance"] = True
        return access
    treasury._access = treasury_access_v177

    original_disburse = treasury._disburse
    async def disburse_v177(core_arg: Any, bot: Any, chat_id: int, actor_id: int, data: dict[str, Any]):
        offices = await gov._user_offices(core_arg, int(chat_id), int(actor_id))
        is_admin = int(actor_id) == int(core_arg.DEVELOPER_ID)
        is_president = "president" in offices
        if "finance" in offices and not (is_admin or is_president) and str(data.get("target_type") or "user") != "structure":
            raise PermissionError("Министр финансов может предлагать переводы только государственным структурам.")
        return await original_disburse(core_arg, bot, int(chat_id), int(actor_id), data)
    treasury._disburse = disburse_v177

    previous_state = gov._state
    async def state_v177(core_arg: Any, bot: Any, chat_id: int, user_id: int):
        await migrate_funds(core_arg)
        payload = await previous_state(core_arg, bot, int(chat_id), int(user_id))
        base_property = await state176.property_state(core_arg, int(chat_id), int(user_id))
        payload["version"] = VERSION
        payload["reality177"] = {
            "programs": await programs_state(core_arg, int(chat_id), int(user_id)),
            "ratings": await ratings_state(core_arg, int(chat_id), int(user_id)),
            "property": await property_state_v177(core_arg, int(chat_id), int(user_id), base_property),
            "emergency_action": bool(await active_effect(core_arg, int(chat_id), "emergency_mode")),
        }
        return payload
    gov._state = state_v177

    # Infrastructure adds a real 15% bonus to positive tax receipts. Protection effects
    # compensate eligible treasury losses after the original operation is recorded.
    original_treasury_log = gov._treasury_log
    async def treasury_log_v177(core_arg: Any, chat_id: int, amount: int, reason: str, source: str, reference_id: str = "", actor_id: int = 0):
        result = await original_treasury_log(core_arg, chat_id, amount, reason, source, reference_id, actor_id)
        source_text = str(source).lower()
        conn = core_arg.db._require_connection()
        if int(amount) > 0 and "tax" in source_text and await active_effect(core_arg, int(chat_id), "infrastructure"):
            bonus = max(1, int(amount) * 15 // 100)
            await conn.execute("UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?", (bonus, gov._now(), int(chat_id)))
        if int(amount) < 0 and any(word in source_text for word in ("theft", "steal", "robbery", "treasury_loss")):
            ratio = 50 if await active_effect(core_arg, int(chat_id), "cyber_defense") else 30 if await active_effect(core_arg, int(chat_id), "emergency_mode") else 0
            if ratio:
                compensation = abs(int(amount)) * ratio // 100
                await conn.execute("UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?", (compensation, gov._now(), int(chat_id)))
        return result
    gov._treasury_log = treasury_log_v177

    previous_enact_bill = gov._enact_bill
    async def enact_bill_rating_v177(core_arg: Any, bot: Any, bill: Any, actor_id: int):
        await previous_enact_bill(core_arg, bot, bill, actor_id)
        try:
            from government_reality_v177_ratings import adjust_rating
            await adjust_rating(core_arg, int(bill["chat_id"]), int(bill["author_id"]), 2, "Принят государственный закон", "law", int(actor_id))
            await core_arg.db._require_connection().commit()
        except Exception:
            core.logging.exception("Не удалось обновить рейтинг автора закона Reality 177")
    gov._enact_bill = enact_bill_rating_v177

    previous_assign_office = gov._assign_office
    async def assign_office_archive_v177(core_arg: Any, chat_id: int, office_key: str, user_id: int, seat_no: int, actor_id: int, term_seconds: int = gov.TERM_SECONDS):
        conn = core_arg.db._require_connection()
        cursor = await conn.execute("SELECT * FROM government_offices_v127 WHERE chat_id=? AND office_key=? AND seat_no=?", (int(chat_id), str(office_key), int(seat_no)))
        old = await cursor.fetchone()
        if old is not None:
            await conn.execute("INSERT OR IGNORE INTO government_official_terms_v177(chat_id,office_key,seat_no,user_id,starts_at,ends_at,final_rating,archived_at) VALUES(?,?,?,?,?,?,?,?)", (int(chat_id), str(old["office_key"]), int(old["seat_no"]), int(old["user_id"]), int(old["starts_at"]), int(old["ends_at"]), int(old["trust"] or 50), gov._now()))
            await conn.commit()
        return await previous_assign_office(core_arg, chat_id, office_key, user_id, seat_no, actor_id, term_seconds)
    gov._assign_office = assign_office_archive_v177

    # Confirmed property violations affect the same canonical trust/rating field.
    original_investigation_action = integration176.investigation_action
    async def investigation_action_rating_v177(core_arg: Any, bot: Any, chat_id: int, actor_id: int, data: dict[str, Any]):
        investigation_id = str(data.get("investigation_id") or "")
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            "SELECT target_user_id FROM government_property_investigations_v176 WHERE investigation_id=? AND chat_id=?",
            (investigation_id, int(chat_id)),
        )
        row = await cursor.fetchone()
        message = await original_investigation_action(core_arg, bot, int(chat_id), int(actor_id), data)
        if row is not None and str(data.get("decision") or "") == "warning":
            from government_reality_v177_ratings import adjust_rating
            await adjust_rating(core_arg, int(chat_id), int(row["target_user_id"]), -3, "Подтверждённое имущественное предупреждение", "oversight", int(actor_id))
            await conn.commit()
        return message
    integration176.investigation_action = investigation_action_rating_v177

    original_property_enact = integration176.enact_property_bill
    async def enact_property_rating_v177(core_arg: Any, bot: Any, bill: Any, actor_id: int):
        payload = json_value(bill["payload_json"], {})
        await original_property_enact(core_arg, bot, bill, int(actor_id))
        if str(bill["bill_type"]) == "property_confiscation":
            from government_reality_v177_ratings import adjust_rating
            await adjust_rating(core_arg, int(bill["chat_id"]), int(payload.get("target_user_id") or 0), -10, "Законная конфискация имущества", "confiscation", int(actor_id))
            await core_arg.db._require_connection().commit()
    integration176.enact_property_bill = enact_property_rating_v177

    previous_inject = luxury._inject_assets
    def inject_v177(source: str) -> str:
        source = previous_inject(source)
        if ASSET_CSS.name not in source:
            source = source.replace("</head>", f'  <link rel="stylesheet" href="/government-v177/{ASSET_CSS.name}?v=177">\n</head>')
        if ASSET_JS.name not in source:
            source = source.replace("</body>", f'  <script src="/government-v177/{ASSET_JS.name}?v=177"></script>\n</body>')
        return source
    luxury._inject_assets = inject_v177

    async def action_api(request: Any):
        try:
            user, chat_id, data = await gov._auth(core, request)
            actor_id = int(user.id)
            action = str(data.get("action") or "")
            bot = request.app["bot"]
            if action == "program_start":
                message = await run_program(core, bot, int(chat_id), actor_id, data)
            elif action == "official_rate":
                message = await rate_official(core, int(chat_id), actor_id, gov._as_int(data.get("target_user_id")), gov._as_int(data.get("value")))
            elif action == "property_sell":
                message = await sell_to_state(core, bot, int(chat_id), actor_id, str(data.get("property_id") or ""), str(data.get("request_id") or ""))
            elif action == "property_auction_start":
                message = await start_voluntary_auction(core, bot, int(chat_id), actor_id, str(data.get("property_id") or ""), gov._as_int(data.get("start_price")), str(data.get("request_id") or ""))
            elif action == "property_auction_bid":
                message = await bid_voluntary(core, int(chat_id), actor_id, str(data.get("auction_id") or ""), gov._as_int(data.get("amount")))
            elif action == "property_upgrade":
                message = await upgrade_property(core, int(chat_id), actor_id, str(data.get("property_id") or ""))
            elif action == "property_insure":
                message = await insure_property(core, int(chat_id), actor_id, str(data.get("property_id") or ""))
            elif action == "property_primary":
                message = await set_primary(core, int(chat_id), actor_id, str(data.get("property_id") or ""))
            elif action == "property_debt_pay":
                message = await pay_property_debt(core, bot, int(chat_id), actor_id, str(data.get("property_id") or ""))
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
    async def start_v177(bot: Any):
        global _RUNTIME_STARTED
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты Reality 177")
        original_runner = core.web.AppRunner
        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            path = ASSET_JS if name == ASSET_JS.name else ASSET_CSS if name == ASSET_CSS.name else None
            if path is None:
                raise core.web.HTTPNotFound()
            return core.web.FileResponse(path, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "X-Government-Reality": "177"})
        def runner(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/government-v177/{name}") not in keys:
                app.router.add_get("/government-v177/{name}", asset)
            if ("POST", "/government-v177/api/action") not in keys:
                app.router.add_post("/government-v177/api/action", action_api)
            return original_runner(app, *args, **kwargs)
        core.web.AppRunner = runner
        try:
            result = await original_start(bot)
        finally:
            core.web.AppRunner = original_runner
        if not _RUNTIME_STARTED:
            _RUNTIME_STARTED = True
            core.spawn_background_task(_runtime(core, bot))
        return result
    core.start_webapp_server = start_v177
