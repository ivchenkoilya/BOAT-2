from __future__ import annotations

import html
import json
import secrets
from pathlib import Path
from typing import Any

import government_mandate_luxury_v147 as luxury
import government_mandates_v143 as mandates
import government_treasury_requests_v165 as treasury_requests
import government_v127 as gov

from government_oversight_deputy_v167_actions import _case, _complaint, _inspection, _report, _sanction, _warning
from government_oversight_deputy_v167_data import OFFICE_KEY, OFFICE_SPEC, VERSION, _access, _person, _routes, _state

ASSET_JS = Path(__file__).resolve().parent / "governmentapp_v127" / "oversight-deputy-v167.js"
ASSET_CSS = Path(__file__).resolve().parent / "governmentapp_v127" / "oversight-deputy-v167.css"

def _appointment_support(core: Any) -> None:
    previous = gov._create_bill
    async def create(core_arg: Any, bot: Any, chat_id: int, author_id: int, bill_type: str, title: str, description: str, payload: dict[str, Any]) -> str:
        if bill_type != "appointment" or str((payload or {}).get("office_key") or "") != OFFICE_KEY:
            return await previous(core_arg, bot, chat_id, author_id, bill_type, title, description, payload)
        access = await _access(core_arg, chat_id, author_id)
        if not access["can_propose_appointment"]:
            raise PermissionError("Кандидатуру предлагает Президент или глава Надзора.")
        target_id, reason = gov._as_int(payload.get("target_user_id")), str(description or "").strip()
        candidate = await _person(core_arg, chat_id, target_id)
        if int(candidate["career_points"]) < OFFICE_SPEC["threshold"] or await gov._has_active_sanctions(core_arg, chat_id, target_id):
            raise ValueError("Кандидат не соответствует требованиям должности.")
        if not await gov._deputy_ids(core_arg, chat_id) or not 10 <= len(reason) <= 1200:
            raise ValueError("Нужна действующая Госдума и обоснование 10–1200 символов.")
        number, bill_id, now = await gov._next_number(core_arg, chat_id, "bill_seq"), secrets.token_urlsafe(12), gov._now()
        conn = core_arg.db._require_connection()
        await conn.execute(
            """
            INSERT INTO government_bills_v127(
              bill_id,chat_id,number,title,description,bill_type,payload_json,author_id,
              status,created_at,voting_ends_at,president_review_ends_at,resolved_at
            ) VALUES(?,?,?,?,?,'appointment',?,?,'voting',?,?,0,0)
            """,
            (bill_id, chat_id, number, str(title)[:120], reason,
             json.dumps({"office_key": OFFICE_KEY, "target_user_id": target_id}, ensure_ascii=False),
             author_id, now, now + gov.BILL_VOTING_SECONDS),
        )
        await conn.commit()
        await gov._publish(bot, chat_id, f"🎖 <b>КАДРОВОЕ ПРЕДЛОЖЕНИЕ №{number}</b>\n\nДолжность: {OFFICE_SPEC['emoji']} <b>{OFFICE_SPEC['title']}</b>\nКандидат: <b>{html.escape(candidate['name'])}</b>\n\n{html.escape(reason)}")
        return bill_id
    gov._create_bill = create

def install_government_oversight_deputy_v167(core: Any) -> None:
    if getattr(core, "_government_oversight_deputy_v167_installed", False):
        return
    core._government_oversight_deputy_v167_installed = True
    core.GOVERNMENT_VERSION = gov.VERSION = VERSION
    gov.OFFICES[OFFICE_KEY] = dict(OFFICE_SPEC)
    mandates.MANDATE_POWERS[OFFICE_KEY] = [
        "принимать жалобы", "открывать одну проверку каждые 24 часа",
        "выдавать предупреждения", "вести публичный реестр",
        "передавать дела прокурору и предлагать санкции через Госдуму",
        "публиковать еженедельный отчёт",
    ]
    roles = list(treasury_requests.STRUCTURE_REQUEST_ROLES.get("oversight", ()))
    treasury_requests.STRUCTURE_REQUEST_ROLES["oversight"] = tuple(dict.fromkeys([*roles, OFFICE_KEY]))
    _appointment_support(core)

    previous_state = gov._state
    async def state(core_arg: Any, bot: Any, chat_id: int, user_id: int) -> dict[str, Any]:
        payload = await previous_state(core_arg, bot, chat_id, user_id)
        payload["version"] = VERSION
        payload["oversight_deputy_v167"] = await _state(core_arg, chat_id, user_id)
        return payload
    gov._state = state

    previous_inject = luxury._inject_assets
    def inject(source: str) -> str:
        source = previous_inject(source)
        if ASSET_CSS.name not in source:
            source = source.replace("</head>", f'  <link rel="stylesheet" href="/government-v167/{ASSET_CSS.name}?v=167">\n</head>')
        if ASSET_JS.name not in source:
            source = source.replace("</body>", f'  <script src="/government-v167/{ASSET_JS.name}?v=167"></script>\n</body>')
        return source
    luxury._inject_assets = inject

    async def action_api(request: Any):
        try:
            user, chat_id, data = await gov._auth(core, request)
            action, actor, bot = str(data.get("action") or ""), int(user.id), request.app["bot"]
            if action == "complaint_create": message = await _complaint(core, bot, chat_id, actor, data)
            elif action == "inspection_open": message = await _inspection(core, bot, chat_id, actor, data)
            elif action == "warning_issue": message = await _warning(core, bot, chat_id, actor, data)
            elif action == "case_close": message = await _case(core, bot, chat_id, actor, data, "close")
            elif action == "case_refer": message = await _case(core, bot, chat_id, actor, data, "refer")
            elif action == "sanction_propose": message = await _sanction(core, bot, chat_id, actor, data)
            elif action == "weekly_report": message = await _report(core, bot, chat_id, actor)
            elif action == "appointment_propose":
                target_id, reason = gov._as_int(data.get("target_user_id")), str(data.get("reason") or "")
                bill = await gov._create_bill(core, bot, chat_id, actor, "appointment", "О назначении заместителя главы Надзора", reason, {"office_key": OFFICE_KEY, "target_user_id": target_id})
                message = f"Кандидатура передана в Госдуму: {bill}."
            else: raise ValueError("Неизвестное действие заместителя Надзора.")
            return core.web.json_response({"ok": True, "message": message})
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    original_start = core.start_webapp_server
    async def start(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты заместителя Надзора Reality 167")
        original_runner = core.web.AppRunner
        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            path = ASSET_JS if name == ASSET_JS.name else ASSET_CSS if name == ASSET_CSS.name else None
            if path is None: raise core.web.HTTPNotFound()
            return core.web.FileResponse(path, headers={"Cache-Control": "no-store", "X-Government-Oversight-Deputy": "167"})
        def runner(app: Any, *args: Any, **kwargs: Any):
            keys = _routes(app)
            if ("GET", "/government-v167/{name}") not in keys: app.router.add_get("/government-v167/{name}", asset)
            if ("POST", "/government-v167/api/action") not in keys: app.router.add_post("/government-v167/api/action", action_api)
            return original_runner(app, *args, **kwargs)
        core.web.AppRunner = runner
        try: return await original_start(bot)
        finally: core.web.AppRunner = original_runner
    core.start_webapp_server = start
