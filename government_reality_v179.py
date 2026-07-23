from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import government_institutions_v128 as institutions
import government_mandate_luxury_v147 as luxury
import government_programs_property_v176 as integration176
import government_reality_v177 as integration177
import government_reality_v177_api as api177
import government_reality_v177_programs as programs177
import government_reality_v177_property as property177
import government_reality_v177_property_state as property_state177
import government_v127 as gov

from government_reality_v179_common import VERSION, WEEK, ensure_schema
from government_reality_v179_construction import (
    approve_project,
    construction_state,
    contribute_project,
    effects_snapshot,
    fund_project,
    pay_building_debt,
    process_construction,
    propose_project,
)
from government_reality_v179_treasury import contribute_v179, install_treasury_v179
from government_reality_v179_trust import presidential_state_adjustment, trust_state

APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "reality-v179.js"
ASSET_CSS = APP_DIR / "reality-v179.css"
_RUNTIME_STARTED = False


def _route_keys(app: Any) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        result.add((str(getattr(route, "method", "") or "").upper(), str(getattr(resource, "canonical", "") or "")))
    return result


async def _apply_program_building_bonus(core: Any, chat_id: int, data: dict[str, Any]) -> None:
    request_id = str(data.get("request_id") or "")
    if not request_id:
        return
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT run_id FROM government_program_requests_v177 WHERE request_id=?",
        (request_id,),
    )
    request_row = await cursor.fetchone()
    if request_row is None:
        return
    run_id = str(request_row["run_id"])
    cursor = await conn.execute(
        "SELECT 1 FROM government_program_building_bonus_v179 WHERE run_id=?",
        (run_id,),
    )
    if await cursor.fetchone() is not None:
        return
    cursor = await conn.execute(
        "SELECT program_key,cost,payload_json FROM government_programs_v176 WHERE run_id=?",
        (run_id,),
    )
    run = await cursor.fetchone()
    if run is None:
        return
    key = str(run["program_key"])
    effects = await effects_snapshot(core, int(chat_id))
    percent = 0
    if key == "education_grants":
        percent = int(effects["education_bonus_percent"])
    elif key in {"social_help", "emergency_social"}:
        percent = int(effects["social_bonus_percent"])
    elif key in {"festival", "information_campaign"}:
        percent = int(effects["festival_bonus_percent"])
    elif key == "science_project":
        percent = int(effects["science_bonus_percent"])
    if percent <= 0:
        return
    bonus = max(1, int(run["cost"] or 0) * percent // 100)
    payload = json.loads(str(run["payload_json"] or "{}"))
    recipients = [int(item) for item in payload.get("recipients", []) if int(item)]
    now = gov._now()
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT 1 FROM government_program_building_bonus_v179 WHERE run_id=?",
            (run_id,),
        )
        if await cursor.fetchone() is not None:
            return
        cursor = await conn.execute(
            "SELECT treasury FROM government_state_v127 WHERE chat_id=?",
            (int(chat_id),),
        )
        state = await cursor.fetchone()
        available = int(state["treasury"] if state else 0)
        actual = min(available, bonus)
        detail = "Инфраструктурный эффект не выплачен: общая казна пуста"
        if actual > 0 and recipients:
            each, remainder = divmod(actual, len(recipients))
            await conn.execute(
                "UPDATE government_state_v127 SET treasury=treasury-?,updated_at=? WHERE chat_id=?",
                (actual, now, int(chat_id)),
            )
            for index, user_id in enumerate(recipients):
                value = each + (1 if index < remainder else 0)
                await conn.execute(
                    "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                    (value, now, int(chat_id), int(user_id)),
                )
                await conn.execute(
                    "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                    (int(chat_id), int(user_id), value, f"building_program_bonus_{key}_v179", now),
                )
            detail = f"Инфраструктура усилила выплаты на {actual}"
        elif actual > 0 and key == "science_project":
            await conn.execute(
                "UPDATE government_state_v127 SET treasury=treasury-?,updated_at=? WHERE chat_id=?",
                (actual, now, int(chat_id)),
            )
            await conn.execute(
                """INSERT INTO government_structure_funds_v164(chat_id,structure_key,balance,updated_at)
                VALUES(?, 'event_fund', ?, ?) ON CONFLICT(chat_id,structure_key) DO UPDATE SET
                balance=government_structure_funds_v164.balance+excluded.balance,updated_at=excluded.updated_at""",
                (int(chat_id), actual, now),
            )
            detail = f"Научный институт вернул {actual} в Фонд развития"
        else:
            actual = 0
        await conn.execute(
            "INSERT INTO government_program_building_bonus_v179(run_id,chat_id,program_key,amount,detail,created_at) VALUES(?,?,?,?,?,?)",
            (run_id, int(chat_id), key, actual, detail, now),
        )
        await conn.commit()


async def _prepare_housing_subsidies(core: Any) -> None:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    cursor = await conn.execute(
        """SELECT p.*,COALESCE(m.upgrade_level,0) upgrade_level
        FROM government_property_v176 p
        LEFT JOIN government_property_meta_v177 m ON m.property_id=p.property_id
        WHERE p.status='owned' AND p.next_maintenance_at<=?""",
        (now,),
    )
    rows = list(await cursor.fetchall())
    if not rows:
        return
    from government_programs_property_v176_common import PROPERTY_ITEMS
    for row in rows:
        effects = await effects_snapshot(core, int(row["chat_id"]))
        discount = int(effects["property_maintenance_discount_percent"])
        if discount <= 0:
            continue
        spec = PROPERTY_ITEMS.get(str(row["item_key"]))
        if spec is None:
            continue
        period_start = int(row["next_maintenance_at"]) - WEEK
        base = max(1, int(row["purchase_price"]) * int(spec["maintenance_bp"]) // 10_000)
        full_amount = max(1, base * (100 + int(row["upgrade_level"] or 0) * 10) // 100)
        subsidy = max(1, full_amount * discount // 100)
        async with core.db.lock:
            cursor2 = await conn.execute(
                "SELECT 1 FROM government_property_housing_subsidies_v179 WHERE property_id=? AND period_start=?",
                (str(row["property_id"]), period_start),
            )
            if await cursor2.fetchone() is not None:
                continue
            cursor2 = await conn.execute(
                "SELECT treasury FROM government_state_v127 WHERE chat_id=?",
                (int(row["chat_id"]),),
            )
            state = await cursor2.fetchone()
            actual = min(subsidy, int(state["treasury"] if state else 0))
            if actual <= 0:
                continue
            await conn.execute(
                "UPDATE government_state_v127 SET treasury=treasury-?,updated_at=? WHERE chat_id=?",
                (actual, now, int(row["chat_id"])),
            )
            await conn.execute(
                "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                (actual, now, int(row["chat_id"]), int(row["owner_id"])),
            )
            await conn.execute(
                """INSERT INTO government_property_housing_subsidies_v179(
                property_id,period_start,chat_id,owner_id,amount,created_at) VALUES(?,?,?,?,?,?)""",
                (str(row["property_id"]), period_start, int(row["chat_id"]), int(row["owner_id"]), actual, now),
            )
            await gov._treasury_log(
                core,
                int(row["chat_id"]),
                -actual,
                "Скидка жилого комплекса на содержание имущества",
                "housing_maintenance_subsidy_v179",
                str(row["property_id"]),
                int(row["owner_id"]),
            )
            await conn.commit()


async def _runtime(core: Any, bot: Any) -> None:
    await asyncio.sleep(15)
    while True:
        try:
            await process_construction(core, bot)
            conn = core.db._require_connection()
            cursor = await conn.execute("SELECT chat_id FROM government_state_v127")
            for row in await cursor.fetchall():
                await presidential_state_adjustment(core, int(row["chat_id"]))
        except Exception:
            core.logging.exception("Ошибка фонового цикла Reality 179")
        await asyncio.sleep(60)


def install_government_reality_v179(core: Any) -> None:
    global _RUNTIME_STARTED
    if getattr(core, "_government_reality_v179_installed", False):
        return
    core._government_reality_v179_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION
    install_treasury_v179(core)

    original_connect = core.Database.connect

    async def connect_v179(self: Any) -> None:
        await original_connect(self)
        core._government_reality_v179_schema_ready = False
        await ensure_schema(core)

    core.Database.connect = connect_v179

    previous_state = gov._state

    async def state_v179(core_arg: Any, bot: Any, chat_id: int, user_id: int):
        payload = await previous_state(core_arg, bot, int(chat_id), int(user_id))
        payload["version"] = VERSION
        payload["reality179"] = {
            "construction": await construction_state(core_arg, int(chat_id), int(user_id)),
            "trust": await trust_state(core_arg, int(chat_id)),
        }
        return payload

    gov._state = state_v179

    previous_enact = gov._enact_bill

    async def enact_v179(core_arg: Any, bot: Any, bill: Any, actor_id: int):
        payload = gov._json(bill["payload_json"], {})
        await previous_enact(core_arg, bot, bill, int(actor_id))
        project_id = str(payload.get("construction_project_id") or "")
        if project_id:
            await approve_project(core_arg, bot, int(bill["chat_id"]), project_id, int(actor_id))

    gov._enact_bill = enact_v179

    previous_treasury_log = gov._treasury_log

    async def treasury_log_v179(core_arg: Any, chat_id: int, amount: int, reason: str, source: str, reference_id: str = "", actor_id: int = 0):
        result = await previous_treasury_log(core_arg, chat_id, amount, reason, source, reference_id, actor_id)
        source_text = str(source).lower()
        if int(amount) < 0 and any(word in source_text for word in ("theft", "steal", "robbery", "treasury_loss")):
            effects = await effects_snapshot(core_arg, int(chat_id))
            ratio = int(effects["treasury_loss_reduction_percent"])
            if ratio > 0:
                compensation = abs(int(amount)) * ratio // 100
                if compensation > 0:
                    conn = core_arg.db._require_connection()
                    await conn.execute(
                        "UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?",
                        (compensation, gov._now(), int(chat_id)),
                    )
                    await previous_treasury_log(
                        core_arg,
                        int(chat_id),
                        compensation,
                        "Компенсация полицейской инфраструктуры",
                        "police_loss_protection_v179",
                        str(reference_id),
                        int(actor_id),
                    )
                    await conn.commit()
        return result

    gov._treasury_log = treasury_log_v179

    previous_program = programs177.run_program

    async def run_program_v179(core_arg: Any, bot: Any, chat_id: int, actor_id: int, data: dict[str, Any]) -> str:
        result = await previous_program(core_arg, bot, int(chat_id), int(actor_id), data)
        try:
            await _apply_program_building_bonus(core_arg, int(chat_id), data)
        except Exception:
            core_arg.logging.exception("Не удалось применить инфраструктурный бонус Reality 179")
        return result

    programs177.run_program = run_program_v179
    integration177.run_program = run_program_v179
    api177.run_program = run_program_v179

    previous_property_maintenance = property_state177.process_maintenance_v177

    async def property_maintenance_v179(core_arg: Any, bot: Any) -> None:
        await _prepare_housing_subsidies(core_arg)
        await previous_property_maintenance(core_arg, bot)

    property_state177.process_maintenance_v177 = property_maintenance_v179
    property177.process_maintenance_v177 = property_maintenance_v179
    integration177.process_maintenance_v177 = property_maintenance_v179
    integration176.process_maintenance = property_maintenance_v179

    previous_policy = institutions._policy

    async def policy_v179(core_arg: Any, chat_id: int) -> dict[str, Any]:
        policy = dict(await previous_policy(core_arg, int(chat_id)))
        effects = await effects_snapshot(core_arg, int(chat_id))
        discount = int(effects["bank_fee_discount_percent"])
        if discount > 0:
            policy["transfer_fee_bps"] = max(0, int(policy.get("transfer_fee_bps", 0)) * (100 - discount) // 100)
        return policy

    institutions._policy = policy_v179

    previous_inject = luxury._inject_assets

    def inject_v179(source: str) -> str:
        source = previous_inject(source)
        if ASSET_CSS.name not in source:
            source = source.replace("</head>", f'  <link rel="stylesheet" href="/government-v179/{ASSET_CSS.name}?v=179">\n</head>')
        if ASSET_JS.name not in source:
            source = source.replace("</body>", f'  <script src="/government-v179/{ASSET_JS.name}?v=179"></script>\n</body>')
        return source

    luxury._inject_assets = inject_v179

    async def action_api(request: Any):
        try:
            user, chat_id, data = await gov._auth(core, request)
            actor_id = int(user.id)
            action = str(data.get("action") or "")
            bot = request.app["bot"]
            if action == "construction_propose":
                message = await propose_project(core, bot, int(chat_id), actor_id, data)
            elif action == "construction_contribute":
                message = await contribute_project(core, int(chat_id), actor_id, data)
            elif action == "construction_fund":
                message = await fund_project(core, int(chat_id), actor_id, data)
            elif action == "construction_debt_pay":
                message = await pay_building_debt(core, int(chat_id), actor_id, data)
            else:
                raise ValueError("Неизвестное действие Reality 179.")
            return core.web.json_response({"ok": True, "message": message})
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    @core.web.middleware
    async def reality179_middleware(request: Any, handler: Any):
        if request.method.upper() == "POST" and str(request.path or "") == "/government-v150/api/contribute":
            try:
                user, chat_id, data = await gov._auth(core, request)
                amount, title = await contribute_v179(core, int(chat_id), int(user.id), data)
                return core.web.json_response({"ok": True, "message": f"Вклад {gov._fmt(amount)} влияния зачислен в «{title}»."})
            except PermissionError as exc:
                return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
            except Exception as exc:
                return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)
        return await handler(request)

    previous_application = core.web.Application

    def application_v179(*args: Any, **kwargs: Any):
        app = previous_application(*args, **kwargs)
        app.middlewares.insert(0, reality179_middleware)
        return app

    core.web.Application = application_v179

    original_start = core.start_webapp_server

    async def start_v179(bot: Any):
        global _RUNTIME_STARTED
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты Reality 179")
        original_runner = core.web.AppRunner

        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            path = ASSET_JS if name == ASSET_JS.name else ASSET_CSS if name == ASSET_CSS.name else None
            if path is None:
                raise core.web.HTTPNotFound()
            return core.web.FileResponse(path, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "X-Government-Reality": "179"})

        def runner(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/government-v179/{name}") not in keys:
                app.router.add_get("/government-v179/{name}", asset)
            if ("POST", "/government-v179/api/action") not in keys:
                app.router.add_post("/government-v179/api/action", action_api)
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

    core.start_webapp_server = start_v179
