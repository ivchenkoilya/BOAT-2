from __future__ import annotations

import html
import json
import secrets
import time
from pathlib import Path
from typing import Any

import government_institutions_v128 as institutions
import government_v127 as gov


VERSION = "Reality 129 · Реформа власти и налог на выигрыш"
APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "reforms-v129.js"

ELECTED_THRESHOLDS = {
    "deputy": 50_000,
    "chair": 100_000,
    "president": 200_000,
}

APPOINTED_OFFICES = {
    "finance",
    "oversight",
    "supreme_court",
    "prosecutor",
    "central_bank",
    "auditor",
    "cec",
    "ombudsman",
    "security",
    "press",
}

WIN_REASON_EXACT = {
    "auto_score_roulette",
    "score_button_roulette",
    "ego_challenge",
}
WIN_REASON_PREFIXES = (
    "bot_game_",
    "miniapp_game_",
    "mini_app_game_",
    "rooftop_game_",
    "roof_game_",
    "heist_game_",
    "bank_heist_",
    "night_hunter_game_",
    "vault_game_",
    "roulette_game_",
)


def _now() -> int:
    return int(time.time())


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _fmt(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _is_win_reason(reason: str) -> bool:
    clean = str(reason or "").casefold().strip()
    return clean in WIN_REASON_EXACT or clean.startswith(WIN_REASON_PREFIXES)


async def _ensure_schema(core: Any) -> None:
    if getattr(core, "_government_reform_v129_schema_ready", False):
        return
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS government_win_tax_v129(
                chat_id INTEGER PRIMARY KEY,
                rate_bps INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL,
                law_id TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS government_win_tax_log_v129(
                tax_id TEXT PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                gross_win INTEGER NOT NULL,
                tax_amount INTEGER NOT NULL,
                rate_bps INTEGER NOT NULL,
                source_reason TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_win_tax_log_chat_v129
            ON government_win_tax_log_v129(chat_id,created_at DESC);
            """
        )
        await conn.commit()
    core._government_reform_v129_schema_ready = True


async def _win_tax_bps(core: Any, chat_id: int) -> int:
    await _ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT rate_bps FROM government_win_tax_v129 WHERE chat_id=?",
        (int(chat_id),),
    )
    row = await cursor.fetchone()
    return max(0, min(10_000, int(row["rate_bps"] if row else 0)))


async def _collect_win_tax(
    core: Any,
    database: Any,
    chat_id: int,
    user_id: int,
    gross_win: int,
    source_reason: str,
) -> int:
    gross = max(0, int(gross_win))
    if gross <= 0:
        return 0
    rate_bps = await _win_tax_bps(core, chat_id)
    if rate_bps <= 0:
        return 0
    tax = gross * rate_bps // 10_000
    if tax <= 0:
        return 0

    await gov._ensure_state(core, int(chat_id))
    conn = database._require_connection()
    now = _now()
    tax_id = secrets.token_urlsafe(10)
    async with database.lock:
        cursor = await conn.execute(
            "SELECT points FROM players WHERE chat_id=? AND user_id=?",
            (int(chat_id), int(user_id)),
        )
        row = await cursor.fetchone()
        available = max(0, int(row["points"] if row else 0))
        actual = min(tax, available)
        if actual <= 0:
            return 0
        await conn.execute(
            "UPDATE players SET points=MAX(0,points-?),updated_at=? WHERE chat_id=? AND user_id=?",
            (actual, now, int(chat_id), int(user_id)),
        )
        await conn.execute(
            "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
            (int(chat_id), int(user_id), -actual, "government_winnings_tax_v129", now),
        )
        await conn.execute(
            "UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?",
            (actual, now, int(chat_id)),
        )
        await conn.execute(
            """INSERT INTO government_treasury_log_v127(
                   chat_id,delta,reason,source_type,source_id,actor_id,created_at
               ) VALUES(?,?,?,?,?,?,?)""",
            (
                int(chat_id), actual, "Налог на выигрыш", "win_tax",
                tax_id, int(user_id), now,
            ),
        )
        await conn.execute(
            """INSERT INTO government_win_tax_log_v129(
                   tax_id,chat_id,user_id,gross_win,tax_amount,rate_bps,source_reason,created_at
               ) VALUES(?,?,?,?,?,?,?,?)""",
            (
                tax_id, int(chat_id), int(user_id), gross, actual,
                rate_bps, str(source_reason), now,
            ),
        )
        await conn.commit()
    return actual


async def _direct_appointment(
    core: Any,
    bot: Any,
    chat_id: int,
    president_id: int,
    office_key: str,
    target_id: int,
    reason: str,
) -> str:
    if int(president_id) != int(core.DEVELOPER_ID) and not await gov._holds(
        core, chat_id, president_id, "president"
    ):
        raise PermissionError("Назначать чиновников может только Президент реальности.")
    if office_key not in APPOINTED_OFFICES or office_key not in gov.OFFICES:
        raise ValueError("Эта должность не назначается президентом.")
    candidate = await gov._player_dict(core, chat_id, target_id)
    if candidate is None:
        raise ValueError("Кандидат не найден в этой беседе.")
    if await gov._has_active_sanctions(core, chat_id, target_id):
        raise PermissionError("Участника с активными санкциями назначить нельзя.")

    now = _now()
    ends_at = now + gov.TERM_SECONDS
    conn = core.db._require_connection()
    await conn.execute(
        """INSERT INTO government_offices_v127(
               chat_id,office_key,seat_no,user_id,starts_at,ends_at,trust,appointed_by
           ) VALUES(?,?,?,?,?,?,50,?)
           ON CONFLICT(chat_id,office_key,seat_no) DO UPDATE SET
               user_id=excluded.user_id,starts_at=excluded.starts_at,
               ends_at=excluded.ends_at,trust=50,appointed_by=excluded.appointed_by""",
        (
            int(chat_id), office_key, 1, int(target_id), now, ends_at,
            int(president_id),
        ),
    )
    await conn.commit()
    spec = gov.OFFICES[office_key]
    clean_reason = str(reason or "Решение Президента реальности").strip()[:500]
    await institutions._log(
        core, chat_id, president_id, "president", "appointment",
        f"Назначен: {spec['title']}", clean_reason, target_id,
        {"office_key": office_key, "ends_at": ends_at},
    )
    await gov._publish(
        bot,
        chat_id,
        "🎖 <b>ПРЕЗИДЕНТСКОЕ НАЗНАЧЕНИЕ</b>\n\n"
        f"Должность: {spec['emoji']} <b>{html.escape(str(spec['title']))}</b>\n"
        f"Назначен: <b>{html.escape(str(candidate['name']))}</b>\n"
        f"Срок полномочий: <b>7 дней</b>\n"
        f"Основание: {html.escape(clean_reason)}.\n\n"
        "🦅 Решение вступило в силу немедленно и не требует голосования Госдумы.",
    )
    return f"{candidate['name']} назначен на должность «{spec['title']}»."


async def _enact_win_tax(core: Any, bot: Any, bill: Any, actor_id: int) -> None:
    await _ensure_schema(core)
    payload = gov._json(bill["payload_json"], {})
    rate = max(0, min(100, _as_int(payload.get("rate"), 0)))
    rate_bps = rate * 100
    bill_id = str(bill["bill_id"])
    chat_id = int(bill["chat_id"])
    now = _now()
    law_number = await gov._next_number(core, chat_id, "law_seq")
    law_id = secrets.token_urlsafe(12)
    conn = core.db._require_connection()
    await conn.execute(
        """INSERT INTO government_win_tax_v129(chat_id,rate_bps,updated_at,law_id)
           VALUES(?,?,?,?) ON CONFLICT(chat_id) DO UPDATE SET
           rate_bps=excluded.rate_bps,updated_at=excluded.updated_at,law_id=excluded.law_id""",
        (chat_id, rate_bps, now, law_id),
    )
    await conn.execute(
        """INSERT INTO government_laws_v127(
               law_id,chat_id,number,title,text,law_type,payload_json,bill_id,enacted_at,active
           ) VALUES(?,?,?,?,?,?,?,?,?,1)""",
        (
            law_id, chat_id, law_number, str(bill["title"]),
            str(bill["description"]), "win_tax",
            json.dumps({"rate": rate}, ensure_ascii=False), bill_id, now,
        ),
    )
    await conn.execute(
        "UPDATE government_bills_v127 SET status='enacted',resolved_at=? WHERE bill_id=?",
        (now, bill_id),
    )
    await conn.commit()
    await gov._publish(
        bot,
        chat_id,
        "⚖️ <b>ЗАКОН О НАЛОГЕ НА ВЫИГРЫШ ВСТУПИЛ В СИЛУ</b>\n\n"
        f"Ставка: <b>{rate}%</b> от положительного игрового выигрыша.\n"
        "Налог автоматически поступает в казну беседы.\n\n"
        "Закон одобрен депутатами и подписан Президентом реальности.",
    )


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


def install_government_reform_v129(core: Any) -> None:
    if getattr(core, "_government_reform_v129_installed", False):
        return
    core._government_reform_v129_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION

    for office_key, threshold in ELECTED_THRESHOLDS.items():
        if office_key in gov.OFFICES:
            gov.OFFICES[office_key]["threshold"] = threshold
    for office_key in APPOINTED_OFFICES:
        if office_key in gov.OFFICES:
            gov.OFFICES[office_key]["threshold"] = 0

    gov.BILL_TYPES["win_tax"] = {"emoji": "🎰", "title": "Налог на выигрыш"}
    for item in institutions.OFFICE_ACTIONS.get("president", []):
        if item.get("key") == "appointment":
            item["title"] = "Назначить чиновника"
            item["hint"] = "Сразу выдать должность без голосования Госдумы"

    original_connect = core.Database.connect

    async def connect_with_reform(self: Any) -> None:
        await original_connect(self)
        core._government_reform_v129_schema_ready = False
        await _ensure_schema(core)

    core.Database.connect = connect_with_reform

    original_state = gov._state

    async def state_with_reform(core_value: Any, bot: Any, chat_id: int, user_id: int) -> dict[str, Any]:
        state = await original_state(core_value, bot, chat_id, user_id)
        state["version"] = VERSION
        state.setdefault("tax", {})["win_rate"] = await _win_tax_bps(core_value, chat_id) / 100
        return state

    gov._state = state_with_reform

    original_enact = gov._enact_bill

    async def enact_with_win_tax(core_value: Any, bot: Any, bill: Any, actor_id: int) -> None:
        if str(bill["bill_type"]) == "win_tax":
            await _enact_win_tax(core_value, bot, bill, actor_id)
            return
        await original_enact(core_value, bot, bill, actor_id)

    gov._enact_bill = enact_with_win_tax

    original_add_points = core.Database.add_points

    async def add_points_with_win_tax(
        self: Any,
        chat_id: int,
        user_id: int,
        delta: int,
        reason: str,
        *,
        update_reward_time: bool = False,
    ) -> Any:
        player = await original_add_points(
            self, chat_id, user_id, delta, reason,
            update_reward_time=update_reward_time,
        )
        if int(delta) > 0 and _is_win_reason(reason):
            await _collect_win_tax(core, self, chat_id, user_id, int(delta), reason)
            refreshed = await self.get_player(chat_id, user_id)
            return refreshed or player
        return player

    core.Database.add_points = add_points_with_win_tax

    original_transfer = core.Database.transfer_points

    async def transfer_with_win_tax(
        self: Any,
        chat_id: int,
        from_user_id: int,
        to_user_id: int,
        amount: int,
        reason: str,
    ) -> tuple[Any, Any, int]:
        source, target, actual = await original_transfer(
            self, chat_id, from_user_id, to_user_id, amount, reason
        )
        if actual > 0 and str(reason).casefold() == "ego_challenge":
            await _collect_win_tax(core, self, chat_id, to_user_id, actual, reason)
            refreshed = await self.get_player(chat_id, to_user_id)
            if refreshed is not None:
                target = refreshed
        return source, target, actual

    core.Database.transfer_points = transfer_with_win_tax

    @core.web.middleware
    async def reform_actions(request: Any, handler: Any):
        path = str(request.path or "")
        if request.method.upper() != "POST" or path not in {
            "/government-v127/api/action",
            "/government-v128/api/action",
        }:
            return await handler(request)
        try:
            data = await request.json()
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
        action = str(data.get("action") or "")

        if path == "/government-v128/api/action" and action == "appointment":
            try:
                user, chat_id, _ = await gov._auth(core, request)
                message = await _direct_appointment(
                    core,
                    request.app["bot"],
                    chat_id,
                    int(user.id),
                    str(data.get("office_key") or ""),
                    _as_int(data.get("target_user_id")),
                    str(data.get("reason") or ""),
                )
                return core.web.json_response({"ok": True, "message": message})
            except PermissionError as exc:
                return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
            except Exception as exc:
                return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

        if path == "/government-v127/api/action" and action == "create_bill":
            bill_type = str(data.get("bill_type") or "")
            if bill_type == "appointment":
                return core.web.json_response(
                    {
                        "ok": False,
                        "reason": "Чиновников теперь назначает президент через вкладку «Полномочия».",
                    },
                    status=400,
                )
            if bill_type == "win_tax":
                try:
                    user, chat_id, _ = await gov._auth(core, request)
                    offices = await gov._user_offices(core, chat_id, int(user.id))
                    is_admin = int(user.id) == int(core.DEVELOPER_ID)
                    if not (is_admin or set(offices) & {"president", "finance", "deputy"}):
                        raise PermissionError(
                            "Налог на выигрыш может предложить президент, министр финансов или депутат."
                        )
                    rate = _as_int((data.get("payload") or {}).get("rate"), -1)
                    if rate < 0 or rate > 100:
                        raise ValueError("Ставка налога на выигрыш должна быть от 0 до 100%.")
                    bill_id = await gov._create_bill(
                        core,
                        request.app["bot"],
                        chat_id,
                        int(user.id),
                        "win_tax",
                        str(data.get("title") or "О налоге на игровой выигрыш"),
                        str(data.get("description") or f"Установить налог на выигрыш в размере {rate}%.") ,
                        {"rate": rate},
                    )
                    return core.web.json_response(
                        {"ok": True, "message": f"Законопроект создан: {bill_id}."}
                    )
                except PermissionError as exc:
                    return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
                except Exception as exc:
                    return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

        return await handler(request)

    previous_application = core.web.Application

    def application_with_reform(*args: Any, **kwargs: Any):
        middlewares = list(kwargs.pop("middlewares", []) or [])
        kwargs["middlewares"] = [reform_actions, *middlewares]
        return previous_application(*args, **kwargs)

    core.web.Application = application_with_reform

    async def asset_js(_: Any):
        return core.web.FileResponse(
            ASSET_JS,
            headers={"Cache-Control": "no-store", "X-Government-Reform": "129"},
        )

    original_start = core.start_webapp_server

    async def start_with_reform(bot: Any):
        if not ASSET_JS.is_file():
            raise RuntimeError("Не найден интерфейс реформы Reality 129")
        original_runner = core.web.AppRunner

        def runner_factory(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/government-v127/reforms-v129.js") not in keys:
                app.router.add_get("/government-v127/reforms-v129.js", asset_js)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_factory
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_reform
