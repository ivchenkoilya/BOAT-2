from __future__ import annotations

import html
import json
import math
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import government_v127 as gov
import sanctions_v126 as sanctions


VERSION = "Reality 128 · Госструктуры и полномочия"
APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "powers-v128.js"
ASSET_CSS = APP_DIR / "powers-v128.css"
DAY_SECONDS = 86_400

NEW_OFFICES: dict[str, dict[str, Any]] = {
    "supreme_court": {"emoji": "⚖️", "title": "Председатель Верховного суда", "threshold": 500_000, "seats": 1},
    "prosecutor": {"emoji": "🛡", "title": "Генеральный прокурор", "threshold": 500_000, "seats": 1},
    "central_bank": {"emoji": "🏦", "title": "Председатель Центрального банка", "threshold": 500_000, "seats": 1},
    "auditor": {"emoji": "🧾", "title": "Глава Счётной палаты", "threshold": 200_000, "seats": 1},
    "cec": {"emoji": "🗳", "title": "Председатель ЦИК", "threshold": 200_000, "seats": 1},
    "ombudsman": {"emoji": "🕊", "title": "Уполномоченный по правам участников", "threshold": 200_000, "seats": 1},
    "security": {"emoji": "🛡", "title": "Секретарь Совета безопасности", "threshold": 500_000, "seats": 1},
    "press": {"emoji": "📰", "title": "Пресс-секретарь государства", "threshold": 200_000, "seats": 1},
}

OFFICE_ACTIONS: dict[str, list[dict[str, str]]] = {
    "president": [
        {"key": "decree", "emoji": "📣", "title": "Выпустить указ", "hint": "Один официальный указ в сутки"},
        {"key": "amnesty", "emoji": "🕊", "title": "Амнистировать участника", "hint": "Снять действующие санкции"},
        {"key": "appointment", "emoji": "🎖", "title": "Предложить назначение", "hint": "Кандидатура проходит Госдуму"},
    ],
    "chair": [
        {"key": "extend_bill", "emoji": "⏱", "title": "Продлить голосование", "hint": "Добавить законопроекту 6 часов"},
        {"key": "return_bill", "emoji": "↩️", "title": "Вернуть закон", "hint": "Снять документ с голосования"},
        {"key": "no_confidence", "emoji": "⚠️", "title": "Вотум недоверия", "hint": "Открыть официальное дело"},
    ],
    "deputy": [
        {"key": "amendment", "emoji": "✏️", "title": "Предложить поправку", "hint": "Зафиксировать поправку к закону"},
        {"key": "inspection_request", "emoji": "🔍", "title": "Запросить проверку", "hint": "Передать материалы прокуратуре"},
    ],
    "finance": [
        {"key": "budget_report", "emoji": "📊", "title": "Бюджетный отчёт", "hint": "Опубликовать казну, долги и налоги"},
        {"key": "tax_refund", "emoji": "🧾", "title": "Вернуть налог", "hint": "Исправить ошибочное списание из казны"},
        {"key": "debtors_report", "emoji": "📋", "title": "Список должников", "hint": "Опубликовать налоговую задолженность"},
    ],
    "oversight": [
        {"key": "warning", "emoji": "⚠️", "title": "Выдать предупреждение", "hint": "Официально предупредить участника"},
        {"key": "open_case", "emoji": "📁", "title": "Открыть дело", "hint": "Зафиксировать нарушение"},
        {"key": "inspection_request", "emoji": "🛡", "title": "Передать прокурору", "hint": "Открыть прокурорскую проверку"},
    ],
    "supreme_court": [
        {"key": "court_case", "emoji": "⚖️", "title": "Открыть судебное дело", "hint": "Рассмотреть спор или жалобу"},
        {"key": "court_ruling", "emoji": "📜", "title": "Вынести решение", "hint": "Признать действие законным или незаконным"},
        {"key": "court_compensation", "emoji": "💰", "title": "Назначить компенсацию", "hint": "До 5 000 из казны по делу"},
    ],
    "prosecutor": [
        {"key": "investigation", "emoji": "🔍", "title": "Начать расследование", "hint": "Проверить участника или чиновника"},
        {"key": "treasury_audit", "emoji": "🏦", "title": "Проверить казну", "hint": "Сверить баланс и операции"},
        {"key": "suspend_official", "emoji": "⏸", "title": "Временно отстранить", "hint": "Отключить полномочия на 6 часов"},
    ],
    "central_bank": [
        {"key": "economic_policy", "emoji": "📈", "title": "Экономическая политика", "hint": "Комиссия, лимиты ставок и займов"},
        {"key": "economic_mode", "emoji": "🧊", "title": "Экономический режим", "hint": "Рост, кризис, заморозка или инфляция"},
        {"key": "economic_report", "emoji": "📊", "title": "Экономический обзор", "hint": "Опубликовать действующие ограничения"},
    ],
    "auditor": [
        {"key": "treasury_audit", "emoji": "🔍", "title": "Аудит казны", "hint": "Проверить соответствие журнала балансу"},
        {"key": "tax_audit", "emoji": "🧾", "title": "Аудит налогов", "hint": "Проверить сборы и задолженности"},
        {"key": "budget_audit", "emoji": "💸", "title": "Аудит выплат", "hint": "Проверить бюджетные расходы"},
    ],
    "cec": [
        {"key": "cec_election", "emoji": "🗳", "title": "Открыть выборы", "hint": "Президент, депутаты или председатель"},
        {"key": "recount", "emoji": "🔄", "title": "Пересчитать голоса", "hint": "Опубликовать контрольный подсчёт"},
        {"key": "disqualify", "emoji": "🚫", "title": "Снять кандидата", "hint": "Только при санкциях или несоответствии"},
    ],
    "ombudsman": [
        {"key": "complaints", "emoji": "📨", "title": "Рассмотреть жалобы", "hint": "Передать дело в суд или прокуратуру"},
        {"key": "protection", "emoji": "🛡", "title": "Временная защита", "hint": "Защитить участника от новых санкций на 6 часов"},
        {"key": "public_appeal", "emoji": "📣", "title": "Публичное обращение", "hint": "Опубликовать позицию омбудсмена"},
    ],
    "security": [
        {"key": "security_meeting", "emoji": "🚨", "title": "Созвать Совбез", "hint": "Официальное экстренное заседание"},
        {"key": "emergency", "emoji": "⚠️", "title": "Чрезвычайный режим", "hint": "До 6 часов: лимиты ставок и переводов"},
        {"key": "security_report", "emoji": "🛡", "title": "Решение Совбеза", "hint": "Опубликовать итог заседания"},
    ],
    "press": [
        {"key": "statement", "emoji": "📣", "title": "Официальное заявление", "hint": "До трёх публикаций в сутки"},
        {"key": "poll", "emoji": "📊", "title": "Общественный опрос", "hint": "Запустить Telegram-опрос"},
        {"key": "daily_brief", "emoji": "📰", "title": "Сводка государства", "hint": "Власть, законы, выборы и казна"},
    ],
}


def _now() -> int:
    return int(time.time())


def _fmt(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _json(value: Any, default: Any) -> Any:
    if isinstance(value, type(default)):
        return value
    try:
        parsed = json.loads(str(value or ""))
        return parsed if isinstance(parsed, type(default)) else default
    except Exception:
        return default


def _day_start() -> int:
    now = datetime.now(timezone.utc)
    return int(datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp())


def _route_keys(app: Any) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        keys.add((str(getattr(route, "method", "") or "").upper(), str(getattr(resource, "canonical", "") or "")))
    return keys


async def _log(core: Any, chat_id: int, actor_id: int, office_key: str, action_key: str,
               title: str, detail: str = "", target_user_id: int = 0,
               payload: dict[str, Any] | None = None) -> str:
    action_id = secrets.token_urlsafe(10)
    conn = core.db._require_connection()
    await conn.execute(
        """INSERT INTO government_power_log_v128(
             action_id,chat_id,actor_id,office_key,action_key,title,detail,target_user_id,
             payload_json,created_at
           ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (action_id, int(chat_id), int(actor_id), str(office_key), str(action_key),
         str(title), str(detail), int(target_user_id), json.dumps(payload or {}, ensure_ascii=False), _now()),
    )
    await conn.commit()
    return action_id


async def _quota(core: Any, chat_id: int, actor_id: int, action_key: str, limit: int) -> None:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT COUNT(*) amount FROM government_power_log_v128 WHERE chat_id=? AND actor_id=? AND action_key=? AND created_at>=?",
        (int(chat_id), int(actor_id), str(action_key), _day_start()),
    )
    used = int((await cursor.fetchone())["amount"])
    if used >= int(limit):
        raise ValueError("Дневной лимит этого полномочия уже исчерпан.")


async def _policy(core: Any, chat_id: int) -> dict[str, Any]:
    conn = core.db._require_connection()
    now = _now()
    await conn.execute(
        """INSERT OR IGNORE INTO government_policy_v128(
             chat_id,transfer_fee_bps,max_wager,loan_limit,economic_mode,mode_ends_at,
             emergency_until,updated_at
           ) VALUES(?,0,50000,1000000,'stability',0,0,?)""",
        (int(chat_id), now),
    )
    await conn.commit()
    cursor = await conn.execute("SELECT * FROM government_policy_v128 WHERE chat_id=?", (int(chat_id),))
    row = await cursor.fetchone()
    mode = str(row["economic_mode"] or "stability")
    mode_ends_at = int(row["mode_ends_at"] or 0)
    if mode_ends_at and mode_ends_at <= now:
        mode = "stability"
        mode_ends_at = 0
        await conn.execute(
            "UPDATE government_policy_v128 SET economic_mode='stability',mode_ends_at=0,updated_at=? WHERE chat_id=?",
            (now, int(chat_id)),
        )
        await conn.commit()
    fee_bps = int(row["transfer_fee_bps"] or 0)
    max_wager = int(row["max_wager"] or 50_000)
    loan_limit = int(row["loan_limit"] or 1_000_000)
    emergency_until = int(row["emergency_until"] or 0)
    if mode == "inflation":
        fee_bps += 300
    elif mode == "crisis":
        max_wager = min(max_wager, 5_000)
        loan_limit = min(loan_limit, 50_000)
    elif mode == "freeze":
        max_wager = min(max_wager, 10_000)
    elif mode == "growth":
        max_wager = min(1_000_000, max_wager + max_wager // 2)
    if emergency_until > now:
        max_wager = min(max_wager, 1_000)
        loan_limit = min(loan_limit, 20_000)
    return {
        "transfer_fee_bps": fee_bps,
        "transfer_fee_percent": fee_bps / 100,
        "max_wager": max_wager,
        "loan_limit": loan_limit,
        "economic_mode": mode,
        "mode_ends_at": mode_ends_at,
        "emergency_until": emergency_until,
        "emergency": emergency_until > now,
    }


async def _active_offices(core: Any, chat_id: int, user_id: int) -> list[str]:
    return await gov._user_offices(core, int(chat_id), int(user_id))


async def _require_office(core: Any, chat_id: int, user_id: int, *offices: str) -> str:
    if int(user_id) == int(core.DEVELOPER_ID):
        return offices[0] if offices else "admin"
    held = await _active_offices(core, chat_id, user_id)
    for office in offices:
        if office in held:
            return office
    titles = ", ".join(gov.OFFICES.get(key, {"title": key})["title"] for key in offices)
    raise PermissionError(f"Действие доступно только должности: {titles}.")


async def _player(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    value = await gov._player_dict(core, int(chat_id), int(user_id))
    if value is None:
        raise ValueError("Участник не найден в этой беседе.")
    return value


async def _publish_person(core: Any, bot: Any, chat_id: int, user_id: int) -> str:
    person = await _player(core, chat_id, user_id)
    return f'<a href="tg://user?id={int(user_id)}">{html.escape(str(person["name"]))}</a>'


async def _create_case(core: Any, chat_id: int, actor_id: int, institution: str,
                       case_type: str, title: str, description: str,
                       target_user_id: int = 0, payload: dict[str, Any] | None = None) -> str:
    clean_title = str(title or "").strip()
    clean_description = str(description or "").strip()
    if len(clean_title) < 5 or len(clean_title) > 140:
        raise ValueError("Название дела должно содержать от 5 до 140 символов.")
    if len(clean_description) < 10 or len(clean_description) > 1500:
        raise ValueError("Описание дела должно содержать от 10 до 1500 символов.")
    if target_user_id:
        await _player(core, chat_id, target_user_id)
    case_id = secrets.token_urlsafe(11)
    conn = core.db._require_connection()
    await conn.execute(
        """INSERT INTO government_cases_v128(
             case_id,chat_id,institution,case_type,title,description,target_user_id,status,
             payload_json,created_by,created_at,updated_at,resolved_at
           ) VALUES(?,?,?,?,?,?,?,'open',?,?,?,?,0)""",
        (case_id, int(chat_id), str(institution), str(case_type), clean_title,
         clean_description, int(target_user_id), json.dumps(payload or {}, ensure_ascii=False),
         int(actor_id), _now(), _now()),
    )
    await conn.commit()
    return case_id


async def _create_appointment_bill(core: Any, bot: Any, chat_id: int, actor_id: int,
                                   office_key: str, target_id: int, reason: str) -> str:
    await _require_office(core, chat_id, actor_id, "president")
    if office_key not in {"finance", "oversight", *NEW_OFFICES.keys()}:
        raise ValueError("Эта должность не назначается президентом.")
    candidate = await _player(core, chat_id, target_id)
    spec = gov.OFFICES[office_key]
    if int(candidate["career_points"]) < int(spec["threshold"]):
        raise ValueError(f"Кандидату требуется {_fmt(int(spec['threshold']))} карьерного влияния.")
    if await gov._has_active_sanctions(core, chat_id, target_id):
        raise PermissionError("Кандидат с активными санкциями не может быть назначен.")
    if not await gov._deputy_ids(core, chat_id):
        raise ValueError("Сначала необходимо избрать депутатов Госдумы.")
    number = await gov._next_number(core, chat_id, "bill_seq")
    bill_id = secrets.token_urlsafe(12)
    now = _now()
    title = f"О назначении: {spec['title']}"
    description = str(reason or f"Предлагается назначить {candidate['name']} на должность {spec['title']}.").strip()
    conn = core.db._require_connection()
    await conn.execute(
        """INSERT INTO government_bills_v127(
             bill_id,chat_id,number,title,description,bill_type,payload_json,author_id,
             status,created_at,voting_ends_at,president_review_ends_at,resolved_at
           ) VALUES(?,?,?,?,?,'appointment',?,?,'voting',?,?,0,0)""",
        (bill_id, int(chat_id), int(number), title, description,
         json.dumps({"office_key": office_key, "target_user_id": int(target_id)}, ensure_ascii=False),
         int(actor_id), now, now + gov.BILL_VOTING_SECONDS),
    )
    await conn.commit()
    await gov._publish(
        bot, chat_id,
        f"🎖 <b>КАДРОВОЕ ПРЕДЛОЖЕНИЕ №{number}</b>\n\n"
        f"Должность: {spec['emoji']} <b>{html.escape(str(spec['title']))}</b>\n"
        f"Кандидат: <b>{html.escape(str(candidate['name']))}</b>\n\n"
        f"{html.escape(description)}\n\nГолосование Госдумы длится <b>12 часов</b>.",
    )
    return bill_id


async def _institution_state(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    conn = core.db._require_connection()
    offices = await _active_offices(core, chat_id, user_id)
    is_admin = int(user_id) == int(core.DEVELOPER_ID)
    cursor = await conn.execute(
        """SELECT * FROM government_cases_v128 WHERE chat_id=?
           ORDER BY CASE status WHEN 'open' THEN 0 WHEN 'referred' THEN 1 ELSE 2 END,
                    updated_at DESC LIMIT 50""",
        (int(chat_id),),
    )
    cases = [
        {
            "case_id": str(row["case_id"]), "institution": str(row["institution"]),
            "case_type": str(row["case_type"]), "title": str(row["title"]),
            "description": str(row["description"]), "target_user_id": int(row["target_user_id"]),
            "status": str(row["status"]), "payload": _json(row["payload_json"], {}),
            "created_by": int(row["created_by"]), "created_at": int(row["created_at"]),
            "updated_at": int(row["updated_at"]), "resolved_at": int(row["resolved_at"]),
        }
        for row in await cursor.fetchall()
    ]
    cursor = await conn.execute(
        "SELECT * FROM government_power_log_v128 WHERE chat_id=? ORDER BY created_at DESC LIMIT 60",
        (int(chat_id),),
    )
    logs = [
        {
            "action_id": str(row["action_id"]), "actor_id": int(row["actor_id"]),
            "office_key": str(row["office_key"]), "action_key": str(row["action_key"]),
            "title": str(row["title"]), "detail": str(row["detail"]),
            "target_user_id": int(row["target_user_id"]), "created_at": int(row["created_at"]),
        }
        for row in await cursor.fetchall()
    ]
    cursor = await conn.execute(
        "SELECT user_id,office_key,until_at,reason FROM government_office_suspensions_v128 WHERE chat_id=? AND until_at>?",
        (int(chat_id), _now()),
    )
    suspensions = [dict(row) for row in await cursor.fetchall()]
    cursor = await conn.execute(
        "SELECT user_id,until_at,reason FROM government_protection_v128 WHERE chat_id=? AND until_at>?",
        (int(chat_id), _now()),
    )
    protections = [dict(row) for row in await cursor.fetchall()]
    powers: list[dict[str, str]] = []
    visible_offices = list(offices)
    if is_admin:
        visible_offices = list(dict.fromkeys([*gov.OFFICES.keys(), *visible_offices]))
    for office in visible_offices:
        for action in OFFICE_ACTIONS.get(office, []):
            powers.append({**action, "office_key": office, "office_title": str(gov.OFFICES[office]["title"])})
    return {
        "version": VERSION,
        "my_offices": offices,
        "is_admin": is_admin,
        "office_actions": OFFICE_ACTIONS,
        "my_powers": powers,
        "cases": cases,
        "power_log": logs,
        "policy": await _policy(core, chat_id),
        "suspensions": suspensions,
        "protections": protections,
    }


def _parse_finance_chat(start_param: str | None, request: Any, data: dict[str, Any]) -> int:
    raw = str(data.get("chat_id") or request.query.get("chat_id") or start_param or "")
    if raw.startswith("finance_"):
        raw = raw[8:]
    try:
        value = int(raw)
        return value if value < 0 else 0
    except (TypeError, ValueError):
        return 0


def install_government_institutions_v128(core: Any) -> None:
    if getattr(core, "_government_institutions_v128_installed", False):
        return
    core._government_institutions_v128_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION
    gov.OFFICES.update(NEW_OFFICES)

    original_connect = core.Database.connect

    async def connect_with_institutions(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS government_policy_v128(
                    chat_id INTEGER PRIMARY KEY,transfer_fee_bps INTEGER NOT NULL DEFAULT 0,
                    max_wager INTEGER NOT NULL DEFAULT 50000,loan_limit INTEGER NOT NULL DEFAULT 1000000,
                    economic_mode TEXT NOT NULL DEFAULT 'stability',mode_ends_at INTEGER NOT NULL DEFAULT 0,
                    emergency_until INTEGER NOT NULL DEFAULT 0,updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS government_power_log_v128(
                    action_id TEXT PRIMARY KEY,chat_id INTEGER NOT NULL,actor_id INTEGER NOT NULL,
                    office_key TEXT NOT NULL,action_key TEXT NOT NULL,title TEXT NOT NULL,
                    detail TEXT NOT NULL DEFAULT '',target_user_id INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_power_log_chat_v128
                ON government_power_log_v128(chat_id,created_at DESC);
                CREATE TABLE IF NOT EXISTS government_cases_v128(
                    case_id TEXT PRIMARY KEY,chat_id INTEGER NOT NULL,institution TEXT NOT NULL,
                    case_type TEXT NOT NULL,title TEXT NOT NULL,description TEXT NOT NULL,
                    target_user_id INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'open',
                    payload_json TEXT NOT NULL DEFAULT '{}',created_by INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,resolved_at INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_cases_chat_v128
                ON government_cases_v128(chat_id,status,updated_at DESC);
                CREATE TABLE IF NOT EXISTS government_office_suspensions_v128(
                    chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,office_key TEXT NOT NULL,
                    until_at INTEGER NOT NULL,reason TEXT NOT NULL,created_by INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,PRIMARY KEY(chat_id,user_id,office_key)
                );
                CREATE TABLE IF NOT EXISTS government_protection_v128(
                    chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,until_at INTEGER NOT NULL,
                    reason TEXT NOT NULL,created_by INTEGER NOT NULL,created_at INTEGER NOT NULL,
                    PRIMARY KEY(chat_id,user_id)
                );
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_institutions

    original_user_offices = gov._user_offices

    async def user_offices_without_suspended(core_value: Any, chat_id: int, user_id: int) -> list[str]:
        offices = await original_user_offices(core_value, chat_id, user_id)
        try:
            conn = core_value.db._require_connection()
            cursor = await conn.execute(
                "SELECT office_key FROM government_office_suspensions_v128 WHERE chat_id=? AND user_id=? AND until_at>?",
                (int(chat_id), int(user_id), _now()),
            )
            suspended = {str(row["office_key"]) for row in await cursor.fetchall()}
            return [key for key in offices if key not in suspended]
        except Exception:
            return offices

    gov._user_offices = user_offices_without_suspended

    original_state = gov._state

    async def state_with_institutions(core_value: Any, bot: Any, chat_id: int, user_id: int) -> dict[str, Any]:
        state = await original_state(core_value, bot, chat_id, user_id)
        state["version"] = VERSION
        state["institutions"] = await _institution_state(core_value, chat_id, user_id)
        return state

    gov._state = state_with_institutions

    original_issue_sanctions = sanctions.issue_sanctions

    async def issue_sanctions_with_protection(core_value: Any, chat_id: int, user_id: int,
                                              types: list[str], duration: int, reason: str,
                                              admin_id: int) -> tuple[list[str], int]:
        if int(admin_id) != int(core_value.DEVELOPER_ID):
            conn = core_value.db._require_connection()
            cursor = await conn.execute(
                "SELECT until_at FROM government_protection_v128 WHERE chat_id=? AND user_id=? AND until_at>?",
                (int(chat_id), int(user_id), _now()),
            )
            row = await cursor.fetchone()
            if row is not None:
                raise PermissionError("Участник находится под временной защитой омбудсмена.")
        return await original_issue_sanctions(core_value, chat_id, user_id, types, duration, reason, admin_id)

    sanctions.issue_sanctions = issue_sanctions_with_protection

    original_game = core.prepare_bot_game_result

    async def game_with_policy(user: Any, game_type: str, stake: int | None, chat_id: int) -> Any:
        policy = await _policy(core, int(chat_id))
        amount = max(0, _as_int(stake))
        if amount and amount > int(policy["max_wager"]):
            return core.inline_article(
                f"gov128:wager:{user.id}:{secrets.token_hex(4)}",
                "🏦 Ставка ограничена государством",
                f"Максимум: {_fmt(int(policy['max_wager']))}",
                "🏦 <b>ОГРАНИЧЕНИЕ ЦЕНТРАЛЬНОГО БАНКА</b>\n\n"
                f"Максимальная ставка сейчас: <b>{_fmt(int(policy['max_wager']))}</b> влияния.",
            )
        return await original_game(user, game_type, stake, chat_id)

    core.prepare_bot_game_result = game_with_policy

    original_ego = core.prepare_ego_challenge_result

    async def ego_with_policy(user: Any, query: str, chat_id: int) -> Any:
        policy = await _policy(core, int(chat_id))
        amount = max(0, _as_int(query))
        if amount and amount > int(policy["max_wager"]):
            return core.inline_article(
                f"gov128:ego:{user.id}:{secrets.token_hex(4)}",
                "🏦 Ставка ограничена государством",
                f"Максимум: {_fmt(int(policy['max_wager']))}",
                "🏦 <b>ОГРАНИЧЕНИЕ ЦЕНТРАЛЬНОГО БАНКА</b>\n\n"
                f"Максимальная ставка сейчас: <b>{_fmt(int(policy['max_wager']))}</b> влияния.",
            )
        return await original_ego(user, query, chat_id)

    core.prepare_ego_challenge_result = ego_with_policy

    @core.web.middleware
    async def economic_finance_middleware(request: Any, handler: Any):
        path = str(request.path or "").casefold()
        if request.method.upper() != "POST" or "finance" not in path or "/api/" not in path:
            return await handler(request)
        try:
            data = await request.json()
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
        user, start_param = core._webapp_auth(request)
        chat_id = _parse_finance_chat(start_param, request, data)
        if user is None or chat_id >= 0:
            return await handler(request)
        action = str(data.get("action") or "").casefold()
        policy = await _policy(core, chat_id)
        amount = max(0, _as_int(data.get("amount")))
        if action in {"loan", "request", "loan_request"} and amount > int(policy["loan_limit"]):
            return core.web.json_response(
                {"ok": False, "reason": f"Центральный банк ограничил новые займы суммой {_fmt(int(policy['loan_limit']))}."},
                status=403,
            )
        if action == "transfer":
            if str(policy["economic_mode"]) == "freeze" and amount > 10_000:
                return core.web.json_response(
                    {"ok": False, "reason": "В режиме заморозки запрещены переводы свыше 10 000."}, status=403,
                )
            if bool(policy["emergency"]) and amount > 5_000:
                return core.web.json_response(
                    {"ok": False, "reason": "Во время чрезвычайного режима переводы ограничены 5 000."}, status=403,
                )
            fee = math.ceil(amount * int(policy["transfer_fee_bps"]) / 10_000)
            if fee > 0:
                player = await core.db.get_player(chat_id, int(user.id))
                if player is None or int(player.points) < amount + fee:
                    return core.web.json_response(
                        {"ok": False, "reason": f"Для перевода и комиссии нужно {_fmt(amount + fee)} влияния."}, status=400,
                    )
                response = await handler(request)
                if int(getattr(response, "status", 500)) < 400:
                    conn = core.db._require_connection()
                    async with core.db.lock:
                        cursor = await conn.execute(
                            "UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=? AND points>=?",
                            (fee, _now(), chat_id, int(user.id), fee),
                        )
                        if int(cursor.rowcount or 0) > 0:
                            await conn.execute(
                                "UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?",
                                (fee, _now(), chat_id),
                            )
                            await conn.execute(
                                "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                                (chat_id, int(user.id), -fee, "central_bank_transfer_fee_v128", _now()),
                            )
                            await gov._treasury_log(core, chat_id, fee, "Комиссия Центрального банка", "transfer_fee", str(user.id), int(user.id))
                            await conn.commit()
                return response
        return await handler(request)

    previous_application = core.web.Application

    def application_with_economic_policy(*args: Any, **kwargs: Any):
        middlewares = list(kwargs.pop("middlewares", []) or [])
        kwargs["middlewares"] = [economic_finance_middleware, *middlewares]
        return previous_application(*args, **kwargs)

    core.web.Application = application_with_economic_policy

    async def action_api(request: Any):
        try:
            user, chat_id, data = await gov._auth(core, request)
            user_id = int(user.id)
            action = str(data.get("action") or "")
            bot = request.app["bot"]
            conn = core.db._require_connection()
            message = "Действие выполнено."

            if action == "decree":
                office = await _require_office(core, chat_id, user_id, "president")
                await _quota(core, chat_id, user_id, "decree", 1)
                text = str(data.get("text") or "").strip()
                if len(text) < 10 or len(text) > 900:
                    raise ValueError("Текст указа должен содержать от 10 до 900 символов.")
                await _log(core, chat_id, user_id, office, "decree", "Президентский указ", text)
                await gov._publish(bot, chat_id, f"🦅 <b>УКАЗ ПРЕЗИДЕНТА РЕАЛЬНОСТИ</b>\n\n{html.escape(text)}\n\n🏛 Указ опубликован и внесён в государственный журнал.")
                message = "Президентский указ опубликован."

            elif action == "amnesty":
                office = await _require_office(core, chat_id, user_id, "president")
                await _quota(core, chat_id, user_id, "amnesty", 1)
                target_id = _as_int(data.get("target_user_id"))
                person = await _player(core, chat_id, target_id)
                types = await sanctions.revoke_sanctions(core, chat_id, target_id, user_id, reason="Президентская амнистия")
                await sanctions.send_lift_notice(core, bot, chat_id, target_id, types, False)
                await _log(core, chat_id, user_id, office, "amnesty", "Президентская амнистия", str(data.get("reason") or ""), target_id)
                message = f"Амнистия для {person['name']} исполнена."

            elif action == "appointment":
                bill_id = await _create_appointment_bill(
                    core, bot, chat_id, user_id, str(data.get("office_key") or ""),
                    _as_int(data.get("target_user_id")), str(data.get("reason") or ""),
                )
                await _log(core, chat_id, user_id, "president", "appointment", "Кадровое предложение", bill_id, _as_int(data.get("target_user_id")))
                message = "Кандидатура передана в Госдуму."

            elif action == "extend_bill":
                office = await _require_office(core, chat_id, user_id, "chair")
                bill_id = str(data.get("bill_id") or "")
                cursor = await conn.execute("SELECT * FROM government_bills_v127 WHERE chat_id=? AND bill_id=?", (chat_id, bill_id))
                bill = await cursor.fetchone()
                if bill is None or str(bill["status"]) != "voting":
                    raise ValueError("Законопроект сейчас не находится на голосовании.")
                await conn.execute("UPDATE government_bills_v127 SET voting_ends_at=voting_ends_at+21600 WHERE bill_id=?", (bill_id,))
                await conn.commit()
                await _log(core, chat_id, user_id, office, "extend_bill", "Голосование продлено", str(bill["title"]))
                await gov._publish(bot, chat_id, f"⏱ <b>ГОЛОСОВАНИЕ ПРОДЛЕНО</b>\n\nЗаконопроект №{int(bill['number'])} «{html.escape(str(bill['title']))}» получил дополнительные <b>6 часов</b>.")
                message = "Голосование продлено на 6 часов."

            elif action == "return_bill":
                office = await _require_office(core, chat_id, user_id, "chair")
                bill_id = str(data.get("bill_id") or "")
                reason = str(data.get("reason") or "").strip()
                cursor = await conn.execute("SELECT * FROM government_bills_v127 WHERE chat_id=? AND bill_id=?", (chat_id, bill_id))
                bill = await cursor.fetchone()
                if bill is None or str(bill["status"]) != "voting":
                    raise ValueError("Документ нельзя вернуть на этой стадии.")
                await conn.execute("UPDATE government_bills_v127 SET status='rejected',resolved_at=? WHERE bill_id=?", (_now(), bill_id))
                await conn.commit()
                await _log(core, chat_id, user_id, office, "return_bill", "Закон возвращён на доработку", reason)
                await gov._publish(bot, chat_id, f"↩️ <b>ЗАКОНОПРОЕКТ ВОЗВРАЩЁН</b>\n\n«{html.escape(str(bill['title']))}» снят с голосования председателем Госдумы.\n\nПричина: {html.escape(reason or 'требуется доработка')}.")
                message = "Законопроект возвращён на доработку."

            elif action in {"no_confidence", "inspection_request", "open_case", "court_case", "investigation"}:
                allowed = {
                    "no_confidence": ("chair", "no_confidence"),
                    "inspection_request": ("deputy", "inspection"),
                    "open_case": ("oversight", "violation"),
                    "court_case": ("supreme_court", "court"),
                    "investigation": ("prosecutor", "investigation"),
                }
                office_key, case_type = allowed[action]
                if action == "inspection_request":
                    office = await _require_office(core, chat_id, user_id, "deputy", "oversight")
                else:
                    office = await _require_office(core, chat_id, user_id, office_key)
                case_id = await _create_case(
                    core, chat_id, user_id, office, case_type,
                    str(data.get("title") or "Государственная проверка"),
                    str(data.get("description") or ""), _as_int(data.get("target_user_id")),
                )
                await _log(core, chat_id, user_id, office, action, "Открыто государственное дело", case_id, _as_int(data.get("target_user_id")))
                await gov._publish(bot, chat_id, f"📁 <b>ОТКРЫТО ГОСУДАРСТВЕННОЕ ДЕЛО</b>\n\nНомер: <code>{html.escape(case_id)}</code>\n{html.escape(str(data.get('title') or 'Государственная проверка'))}\n\nМатериалы доступны уполномоченным структурам.")
                message = f"Дело открыто: {case_id}."

            elif action == "amendment":
                office = await _require_office(core, chat_id, user_id, "deputy")
                bill_id = str(data.get("bill_id") or "")
                text = str(data.get("text") or "").strip()
                if len(text) < 10 or len(text) > 800:
                    raise ValueError("Поправка должна содержать от 10 до 800 символов.")
                cursor = await conn.execute("SELECT number,title FROM government_bills_v127 WHERE chat_id=? AND bill_id=?", (chat_id, bill_id))
                bill = await cursor.fetchone()
                if bill is None:
                    raise ValueError("Законопроект не найден.")
                await _log(core, chat_id, user_id, office, "amendment", f"Поправка к законопроекту №{int(bill['number'])}", text, payload={"bill_id": bill_id})
                await gov._publish(bot, chat_id, f"✏️ <b>ДЕПУТАТСКАЯ ПОПРАВКА</b>\n\nК законопроекту №{int(bill['number'])} «{html.escape(str(bill['title']))}» предложено:\n\n{html.escape(text)}")
                message = "Поправка опубликована."

            elif action == "budget_report":
                office = await _require_office(core, chat_id, user_id, "finance")
                state = await gov._ensure_state(core, chat_id)
                cursor = await conn.execute("SELECT COALESCE(SUM(amount),0) total,COUNT(CASE WHEN amount>0 THEN 1 END) people FROM government_tax_debts_v127 WHERE chat_id=?", (chat_id,))
                debt = await cursor.fetchone()
                cursor = await conn.execute("SELECT COUNT(*) amount FROM government_tax_runs_v127 WHERE chat_id=?", (chat_id,))
                runs = int((await cursor.fetchone())["amount"])
                await _log(core, chat_id, user_id, office, "budget_report", "Опубликован бюджетный отчёт")
                await gov._publish(bot, chat_id, "📊 <b>БЮДЖЕТНЫЙ ОТЧЁТ</b>\n\n"
                    f"Казна: <b>{_fmt(int(state['treasury']))}</b>\n"
                    f"Налоговый долг: <b>{_fmt(int(debt['total']))}</b>\n"
                    f"Должников: <b>{int(debt['people'])}</b>\n"
                    f"Проведено налоговых периодов: <b>{runs}</b>.")
                message = "Бюджетный отчёт опубликован."

            elif action == "tax_refund":
                office = await _require_office(core, chat_id, user_id, "finance")
                await _quota(core, chat_id, user_id, "tax_refund", 3)
                target_id = _as_int(data.get("target_user_id"))
                amount = _as_int(data.get("amount"))
                reason = str(data.get("reason") or "Исправление налогового списания").strip()
                if amount <= 0 or amount > 10_000:
                    raise ValueError("Возврат должен быть от 1 до 10 000.")
                person = await _player(core, chat_id, target_id)
                state = await gov._ensure_state(core, chat_id)
                if int(state["treasury"]) < amount:
                    raise ValueError("В казне недостаточно влияния.")
                async with core.db.lock:
                    await conn.execute("UPDATE government_state_v127 SET treasury=treasury-?,updated_at=? WHERE chat_id=?", (amount, _now(), chat_id))
                    await conn.execute("UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?", (amount, _now(), chat_id, target_id))
                    await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)", (chat_id, target_id, amount, "government_tax_refund_v128", _now()))
                    await gov._treasury_log(core, chat_id, -amount, reason, "tax_refund", str(target_id), user_id)
                    await conn.commit()
                await _log(core, chat_id, user_id, office, "tax_refund", "Налоговый возврат", reason, target_id, {"amount": amount})
                await gov._publish(bot, chat_id, f"🧾 <b>НАЛОГОВЫЙ ВОЗВРАТ</b>\n\nУчастник: <b>{html.escape(str(person['name']))}</b>\nВозвращено: <b>{_fmt(amount)}</b> влияния\nПричина: {html.escape(reason)}.")
                message = "Налоговый возврат выполнен."

            elif action == "debtors_report":
                office = await _require_office(core, chat_id, user_id, "finance")
                cursor = await conn.execute(
                    """SELECT d.user_id,d.amount,p.full_name FROM government_tax_debts_v127 d
                       LEFT JOIN players p ON p.chat_id=d.chat_id AND p.user_id=d.user_id
                       WHERE d.chat_id=? AND d.amount>0 ORDER BY d.amount DESC LIMIT 15""", (chat_id,))
                rows = list(await cursor.fetchall())
                lines = [f"{i}. <b>{html.escape(str(row['full_name'] or row['user_id']))}</b> — {_fmt(int(row['amount']))}" for i, row in enumerate(rows, 1)]
                await _log(core, chat_id, user_id, office, "debtors_report", "Опубликован список налоговых должников")
                await gov._publish(bot, chat_id, "📋 <b>НАЛОГОВЫЕ ДОЛЖНИКИ</b>\n\n" + ("\n".join(lines) if lines else "Задолженностей нет."))
                message = "Список должников опубликован."

            elif action == "warning":
                office = await _require_office(core, chat_id, user_id, "oversight")
                await _quota(core, chat_id, user_id, "warning", 3)
                target_id = _as_int(data.get("target_user_id"))
                reason = str(data.get("reason") or "").strip()
                if len(reason) < 5:
                    raise ValueError("Укажи причину предупреждения.")
                person_link = await _publish_person(core, bot, chat_id, target_id)
                await _log(core, chat_id, user_id, office, "warning", "Официальное предупреждение", reason, target_id)
                await gov._publish(bot, chat_id, f"⚠️ <b>ОФИЦИАЛЬНОЕ ПРЕДУПРЕЖДЕНИЕ</b>\n\nУчастник: {person_link}\nОснование: {html.escape(reason)}\n\n🏛 Предупреждение вынесено Надзором за гандонами.")
                message = "Предупреждение опубликовано."

            elif action in {"treasury_audit", "tax_audit", "budget_audit"}:
                office = await _require_office(core, chat_id, user_id, "prosecutor", "auditor")
                state = await gov._ensure_state(core, chat_id)
                cursor = await conn.execute("SELECT COALESCE(SUM(delta),0) total,COUNT(*) operations FROM government_treasury_log_v127 WHERE chat_id=?", (chat_id,))
                treasury_log = await cursor.fetchone()
                cursor = await conn.execute("SELECT COALESCE(SUM(total_paid),0) paid,COALESCE(SUM(debt_added),0) debt,COUNT(*) runs FROM government_tax_runs_v127 WHERE chat_id=?", (chat_id,))
                tax = await cursor.fetchone()
                cursor = await conn.execute("SELECT COALESCE(SUM(-delta),0) spent,COUNT(*) operations FROM government_treasury_log_v127 WHERE chat_id=? AND delta<0", (chat_id,))
                spending = await cursor.fetchone()
                detail = (
                    f"Баланс казны: {_fmt(int(state['treasury']))}; журнал: {_fmt(int(treasury_log['total']))}; "
                    f"операций: {int(treasury_log['operations'])}; налогов собрано: {_fmt(int(tax['paid']))}; "
                    f"новых долгов: {_fmt(int(tax['debt']))}; расходов: {_fmt(int(spending['spent']))}."
                )
                await _log(core, chat_id, user_id, office, action, "Государственный аудит", detail)
                await gov._publish(bot, chat_id, f"🧾 <b>ЗАКЛЮЧЕНИЕ ГОСУДАРСТВЕННОГО АУДИТА</b>\n\n{html.escape(detail)}\n\nСтатус: <b>{'расхождений не найдено' if int(state['treasury']) == int(treasury_log['total']) else 'обнаружено расхождение'}</b>.")
                message = "Аудиторское заключение опубликовано."

            elif action == "suspend_official":
                office = await _require_office(core, chat_id, user_id, "prosecutor")
                target_id = _as_int(data.get("target_user_id"))
                office_key = str(data.get("office_key") or "")
                reason = str(data.get("reason") or "").strip()
                if office_key not in gov.OFFICES:
                    raise ValueError("Неизвестная должность.")
                if target_id == user_id:
                    raise ValueError("Нельзя отстранить самого себя.")
                cursor = await conn.execute("SELECT 1 FROM government_offices_v127 WHERE chat_id=? AND user_id=? AND office_key=? AND ends_at>?", (chat_id, target_id, office_key, _now()))
                if await cursor.fetchone() is None:
                    raise ValueError("Участник не занимает указанную должность.")
                until_at = _now() + 21_600
                await conn.execute(
                    """INSERT INTO government_office_suspensions_v128(chat_id,user_id,office_key,until_at,reason,created_by,created_at)
                       VALUES(?,?,?,?,?,?,?) ON CONFLICT(chat_id,user_id,office_key) DO UPDATE SET
                       until_at=excluded.until_at,reason=excluded.reason,created_by=excluded.created_by,created_at=excluded.created_at""",
                    (chat_id, target_id, office_key, until_at, reason or "Прокурорская проверка", user_id, _now()),
                )
                await conn.commit()
                await _log(core, chat_id, user_id, office, "suspend_official", "Чиновник временно отстранён", reason, target_id, {"office_key": office_key, "until_at": until_at})
                await gov._publish(bot, chat_id, f"⏸ <b>ВРЕМЕННОЕ ОТСТРАНЕНИЕ</b>\n\nПолномочия должности «{html.escape(str(gov.OFFICES[office_key]['title']))}» приостановлены на <b>6 часов</b>.\nОснование: {html.escape(reason or 'прокурорская проверка')}.")
                message = "Полномочия чиновника приостановлены."

            elif action == "court_ruling":
                office = await _require_office(core, chat_id, user_id, "supreme_court")
                case_id = str(data.get("case_id") or "")
                decision = str(data.get("decision") or "")
                text = str(data.get("text") or "").strip()
                if decision not in {"lawful", "unlawful", "dismissed"}:
                    raise ValueError("Неизвестное решение суда.")
                cursor = await conn.execute("SELECT * FROM government_cases_v128 WHERE chat_id=? AND case_id=?", (chat_id, case_id))
                case = await cursor.fetchone()
                if case is None:
                    raise ValueError("Судебное дело не найдено.")
                await conn.execute("UPDATE government_cases_v128 SET status=?,payload_json=?,updated_at=?,resolved_at=? WHERE case_id=?", (decision, json.dumps({"ruling": text}, ensure_ascii=False), _now(), _now(), case_id))
                await conn.commit()
                await _log(core, chat_id, user_id, office, "court_ruling", "Судебное постановление", text, int(case["target_user_id"]), {"case_id": case_id, "decision": decision})
                label = {"lawful": "решение признано законным", "unlawful": "решение признано незаконным", "dismissed": "дело прекращено"}[decision]
                await gov._publish(bot, chat_id, f"⚖️ <b>ПОСТАНОВЛЕНИЕ ВЕРХОВНОГО СУДА</b>\n\nДело: <code>{html.escape(case_id)}</code>\nВердикт: <b>{label}</b>\n\n{html.escape(text or 'Мотивировочная часть внесена в журнал суда.')}.")
                message = "Судебное решение опубликовано."

            elif action == "court_compensation":
                office = await _require_office(core, chat_id, user_id, "supreme_court")
                case_id = str(data.get("case_id") or "")
                target_id = _as_int(data.get("target_user_id"))
                amount = _as_int(data.get("amount"))
                if amount <= 0 or amount > 5_000:
                    raise ValueError("Судебная компенсация должна быть от 1 до 5 000.")
                cursor = await conn.execute("SELECT status FROM government_cases_v128 WHERE chat_id=? AND case_id=?", (chat_id, case_id))
                case = await cursor.fetchone()
                if case is None or str(case["status"]) != "unlawful":
                    raise ValueError("Компенсация доступна только по делу с решением о незаконности.")
                state = await gov._ensure_state(core, chat_id)
                if int(state["treasury"]) < amount:
                    raise ValueError("В казне недостаточно влияния.")
                person = await _player(core, chat_id, target_id)
                async with core.db.lock:
                    await conn.execute("UPDATE government_state_v127 SET treasury=treasury-?,updated_at=? WHERE chat_id=?", (amount, _now(), chat_id))
                    await conn.execute("UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?", (amount, _now(), chat_id, target_id))
                    await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)", (chat_id, target_id, amount, "supreme_court_compensation_v128", _now()))
                    await gov._treasury_log(core, chat_id, -amount, "Судебная компенсация", "court", case_id, user_id)
                    await conn.commit()
                await _log(core, chat_id, user_id, office, "court_compensation", "Назначена судебная компенсация", case_id, target_id, {"amount": amount})
                await gov._publish(bot, chat_id, f"💰 <b>СУДЕБНАЯ КОМПЕНСАЦИЯ</b>\n\nПолучатель: <b>{html.escape(str(person['name']))}</b>\nСумма: <b>{_fmt(amount)}</b> влияния\nДело: <code>{html.escape(case_id)}</code>.")
                message = "Компенсация выплачена."

            elif action in {"economic_policy", "economic_mode"}:
                office = await _require_office(core, chat_id, user_id, "central_bank")
                await _quota(core, chat_id, user_id, action, 2)
                await _policy(core, chat_id)
                if action == "economic_policy":
                    fee_bps = max(0, min(1000, _as_int(data.get("transfer_fee_bps"))))
                    max_wager = max(100, min(1_000_000, _as_int(data.get("max_wager"), 50_000)))
                    loan_limit = max(1_000, min(5_000_000, _as_int(data.get("loan_limit"), 1_000_000)))
                    await conn.execute("UPDATE government_policy_v128 SET transfer_fee_bps=?,max_wager=?,loan_limit=?,updated_at=? WHERE chat_id=?", (fee_bps, max_wager, loan_limit, _now(), chat_id))
                    detail = f"Комиссия {fee_bps / 100:g}%, ставка до {_fmt(max_wager)}, заём до {_fmt(loan_limit)}"
                else:
                    mode = str(data.get("mode") or "stability")
                    if mode not in {"stability", "growth", "crisis", "freeze", "inflation"}:
                        raise ValueError("Неизвестный экономический режим.")
                    duration = max(3600, min(DAY_SECONDS, _as_int(data.get("duration"), 21_600)))
                    ends_at = 0 if mode == "stability" else _now() + duration
                    await conn.execute("UPDATE government_policy_v128 SET economic_mode=?,mode_ends_at=?,updated_at=? WHERE chat_id=?", (mode, ends_at, _now(), chat_id))
                    detail = f"Режим {mode}; срок {_fmt(duration // 3600)} ч."
                await conn.commit()
                await _log(core, chat_id, user_id, office, action, "Решение Центрального банка", detail)
                await gov._publish(bot, chat_id, f"🏦 <b>РЕШЕНИЕ ЦЕНТРАЛЬНОГО БАНКА</b>\n\n{html.escape(detail)}.\n\nНовые параметры применяются к ставкам, переводам и займам.")
                message = "Экономическая политика обновлена."

            elif action == "economic_report":
                office = await _require_office(core, chat_id, user_id, "central_bank")
                policy = await _policy(core, chat_id)
                detail = f"Режим: {policy['economic_mode']}; комиссия: {policy['transfer_fee_percent']:g}%; максимальная ставка: {_fmt(policy['max_wager'])}; лимит займа: {_fmt(policy['loan_limit'])}"
                await _log(core, chat_id, user_id, office, "economic_report", "Экономический обзор", detail)
                await gov._publish(bot, chat_id, f"📊 <b>ЭКОНОМИЧЕСКИЙ ОБЗОР ЦБ</b>\n\n{html.escape(detail)}.")
                message = "Экономический обзор опубликован."

            elif action == "cec_election":
                office = await _require_office(core, chat_id, user_id, "cec")
                office_key = str(data.get("office_key") or "")
                if office_key not in {"president", "deputy", "chair"}:
                    raise ValueError("ЦИК проводит выборы президента, депутатов и председателя.")
                election_id = await gov._start_election(core, bot, chat_id, office_key, int(core.DEVELOPER_ID))
                await _log(core, chat_id, user_id, office, "cec_election", "ЦИК открыл выборы", election_id)
                message = "Избирательная кампания открыта."

            elif action == "recount":
                office = await _require_office(core, chat_id, user_id, "cec")
                election_id = str(data.get("election_id") or "")
                cursor = await conn.execute(
                    """SELECT c.user_id,p.full_name,COUNT(v.voter_id) votes FROM government_candidates_v127 c
                       LEFT JOIN government_election_votes_v127 v ON v.election_id=c.election_id AND v.candidate_id=c.user_id
                       LEFT JOIN government_elections_v127 e ON e.election_id=c.election_id
                       LEFT JOIN players p ON p.chat_id=e.chat_id AND p.user_id=c.user_id
                       WHERE c.election_id=? AND e.chat_id=? GROUP BY c.user_id,p.full_name ORDER BY votes DESC,c.user_id""",
                    (election_id, chat_id),
                )
                rows = list(await cursor.fetchall())
                if not rows:
                    raise ValueError("Кандидаты для пересчёта не найдены.")
                lines = [f"{i}. <b>{html.escape(str(row['full_name'] or row['user_id']))}</b> — {int(row['votes'])}" for i, row in enumerate(rows, 1)]
                await _log(core, chat_id, user_id, office, "recount", "Контрольный пересчёт голосов", election_id)
                await gov._publish(bot, chat_id, "🔄 <b>КОНТРОЛЬНЫЙ ПЕРЕСЧЁТ ЦИК</b>\n\n" + "\n".join(lines))
                message = "Пересчёт опубликован."

            elif action == "disqualify":
                office = await _require_office(core, chat_id, user_id, "cec")
                election_id = str(data.get("election_id") or "")
                candidate_id = _as_int(data.get("candidate_id"))
                cursor = await conn.execute("SELECT e.*,c.user_id FROM government_elections_v127 e JOIN government_candidates_v127 c ON c.election_id=e.election_id WHERE e.chat_id=? AND e.election_id=? AND c.user_id=?", (chat_id, election_id, candidate_id))
                row = await cursor.fetchone()
                if row is None or str(row["phase"]) not in {"nomination", "voting"}:
                    raise ValueError("Кандидат не участвует в активных выборах.")
                person = await _player(core, chat_id, candidate_id)
                spec = gov.OFFICES[str(row["office_key"])]
                sanctioned = await gov._has_active_sanctions(core, chat_id, candidate_id)
                ineligible = int(person["career_points"]) < int(spec["threshold"])
                if not sanctioned and not ineligible:
                    raise PermissionError("Нет законного основания для снятия кандидата.")
                await conn.execute("DELETE FROM government_candidates_v127 WHERE election_id=? AND user_id=?", (election_id, candidate_id))
                await conn.execute("DELETE FROM government_election_votes_v127 WHERE election_id=? AND candidate_id=?", (election_id, candidate_id))
                await conn.commit()
                await _log(core, chat_id, user_id, office, "disqualify", "Кандидат снят с выборов", str(data.get("reason") or ""), candidate_id)
                await gov._publish(bot, chat_id, f"🚫 <b>РЕШЕНИЕ ЦИК</b>\n\nКандидат <b>{html.escape(str(person['name']))}</b> снят с выборов.\nОснование: {'активные санкции' if sanctioned else 'несоответствие карьерному порогу'}.")
                message = "Кандидат снят с выборов."

            elif action == "submit_complaint":
                title = str(data.get("title") or "Жалоба участника")
                case_id = await _create_case(core, chat_id, user_id, "ombudsman", "complaint", title, str(data.get("description") or ""), _as_int(data.get("target_user_id")))
                await _log(core, chat_id, user_id, "citizen", "submit_complaint", "Подана жалоба", case_id, _as_int(data.get("target_user_id")))
                message = f"Жалоба зарегистрирована: {case_id}."

            elif action == "case_refer":
                office = await _require_office(core, chat_id, user_id, "ombudsman", "prosecutor", "supreme_court")
                case_id = str(data.get("case_id") or "")
                destination = str(data.get("destination") or "")
                if destination not in {"prosecutor", "supreme_court", "closed"}:
                    raise ValueError("Неизвестное направление дела.")
                cursor = await conn.execute("SELECT * FROM government_cases_v128 WHERE chat_id=? AND case_id=?", (chat_id, case_id))
                case = await cursor.fetchone()
                if case is None:
                    raise ValueError("Дело не найдено.")
                status = "closed" if destination == "closed" else "referred"
                payload = _json(case["payload_json"], {})
                payload["destination"] = destination
                await conn.execute("UPDATE government_cases_v128 SET institution=?,status=?,payload_json=?,updated_at=?,resolved_at=? WHERE case_id=?", (destination if destination != "closed" else str(case["institution"]), status, json.dumps(payload, ensure_ascii=False), _now(), _now() if status == "closed" else 0, case_id))
                await conn.commit()
                await _log(core, chat_id, user_id, office, "case_refer", "Дело передано", destination, int(case["target_user_id"]), {"case_id": case_id})
                message = "Статус дела обновлён."

            elif action == "protection":
                office = await _require_office(core, chat_id, user_id, "ombudsman")
                await _quota(core, chat_id, user_id, "protection", 2)
                target_id = _as_int(data.get("target_user_id"))
                reason = str(data.get("reason") or "Рассмотрение жалобы").strip()
                person = await _player(core, chat_id, target_id)
                until_at = _now() + 21_600
                await conn.execute(
                    """INSERT INTO government_protection_v128(chat_id,user_id,until_at,reason,created_by,created_at)
                       VALUES(?,?,?,?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET
                       until_at=excluded.until_at,reason=excluded.reason,created_by=excluded.created_by,created_at=excluded.created_at""",
                    (chat_id, target_id, until_at, reason, user_id, _now()),
                )
                await conn.commit()
                await _log(core, chat_id, user_id, office, "protection", "Временная защита участника", reason, target_id)
                await gov._publish(bot, chat_id, f"🛡 <b>ВРЕМЕННАЯ ЗАЩИТА ОМБУДСМЕНА</b>\n\nУчастник: <b>{html.escape(str(person['name']))}</b>\nСрок: <b>6 часов</b>\nОснование: {html.escape(reason)}.\n\nДо окончания защиты новые санкции не вводятся.")
                message = "Временная защита установлена."

            elif action == "public_appeal":
                office = await _require_office(core, chat_id, user_id, "ombudsman")
                text = str(data.get("text") or "").strip()
                if len(text) < 10 or len(text) > 900:
                    raise ValueError("Обращение должно содержать от 10 до 900 символов.")
                await _log(core, chat_id, user_id, office, "public_appeal", "Публичное обращение омбудсмена", text)
                await gov._publish(bot, chat_id, f"🕊 <b>ОБРАЩЕНИЕ ОМБУДСМЕНА</b>\n\n{html.escape(text)}")
                message = "Обращение опубликовано."

            elif action == "security_meeting":
                office = await _require_office(core, chat_id, user_id, "security", "president")
                await _quota(core, chat_id, user_id, "security_meeting", 2)
                reason = str(data.get("reason") or "").strip()
                await _log(core, chat_id, user_id, office, "security_meeting", "Созван Совет безопасности", reason)
                await gov._publish(bot, chat_id, f"🚨 <b>СОЗВАН СОВЕТ БЕЗОПАСНОСТИ</b>\n\nПовестка: {html.escape(reason or 'оперативная обстановка государства')}.")
                message = "Совет безопасности созван."

            elif action == "emergency":
                office = await _require_office(core, chat_id, user_id, "security", "president")
                await _quota(core, chat_id, user_id, "emergency", 1)
                duration = max(3600, min(21_600, _as_int(data.get("duration"), 10_800)))
                reason = str(data.get("reason") or "").strip()
                await _policy(core, chat_id)
                until_at = _now() + duration
                await conn.execute("UPDATE government_policy_v128 SET emergency_until=?,updated_at=? WHERE chat_id=?", (until_at, _now(), chat_id))
                await conn.commit()
                await _log(core, chat_id, user_id, office, "emergency", "Введён чрезвычайный режим", reason, payload={"until_at": until_at})
                await gov._publish(bot, chat_id, f"⚠️ <b>ЧРЕЗВЫЧАЙНЫЙ РЕЖИМ</b>\n\nСрок: <b>{duration // 3600} ч.</b>\nОснование: {html.escape(reason or 'решение Совета безопасности')}\n\nСтавки ограничены 1 000, переводы — 5 000, новые займы — 20 000.")
                message = "Чрезвычайный режим введён."

            elif action == "security_report":
                office = await _require_office(core, chat_id, user_id, "security")
                text = str(data.get("text") or "").strip()
                if len(text) < 10 or len(text) > 900:
                    raise ValueError("Решение должно содержать от 10 до 900 символов.")
                await _log(core, chat_id, user_id, office, "security_report", "Решение Совета безопасности", text)
                await gov._publish(bot, chat_id, f"🛡 <b>РЕШЕНИЕ СОВЕТА БЕЗОПАСНОСТИ</b>\n\n{html.escape(text)}")
                message = "Решение Совбеза опубликовано."

            elif action in {"statement", "public_appeal"}:
                office = await _require_office(core, chat_id, user_id, "press")
                await _quota(core, chat_id, user_id, "statement", 3)
                text = str(data.get("text") or "").strip()
                if len(text) < 10 or len(text) > 900:
                    raise ValueError("Заявление должно содержать от 10 до 900 символов.")
                await _log(core, chat_id, user_id, office, "statement", "Официальное заявление", text)
                await gov._publish(bot, chat_id, f"📰 <b>ОФИЦИАЛЬНОЕ ЗАЯВЛЕНИЕ ГОСУДАРСТВА</b>\n\n{html.escape(text)}")
                message = "Заявление опубликовано."

            elif action == "poll":
                office = await _require_office(core, chat_id, user_id, "press")
                await _quota(core, chat_id, user_id, "poll", 2)
                question = str(data.get("question") or "").strip()
                options = [str(item).strip() for item in data.get("options", []) if str(item).strip()]
                if len(question) < 5 or len(question) > 250 or len(options) < 2 or len(options) > 10:
                    raise ValueError("Укажи вопрос и от 2 до 10 вариантов ответа.")
                await bot.send_poll(chat_id, question, options, is_anonymous=False)
                await _log(core, chat_id, user_id, office, "poll", "Общественный опрос", question, payload={"options": options})
                message = "Общественный опрос запущен."

            elif action == "daily_brief":
                office = await _require_office(core, chat_id, user_id, "press")
                await _quota(core, chat_id, user_id, "daily_brief", 1)
                state = await gov._state(core, bot, chat_id, user_id)
                president = next((item for item in state.get("offices", []) if item["office_key"] == "president"), None)
                active_bills = sum(1 for item in state.get("bills", []) if item["status"] in {"voting", "president_review", "vetoed"})
                active_elections = sum(1 for item in state.get("elections", []) if item["phase"] in {"nomination", "voting"})
                text = (
                    f"Президент: {president['name'] if president else 'не избран'}\n"
                    f"Казна: {_fmt(int(state['treasury']['balance']))}\n"
                    f"Активные законопроекты: {active_bills}\n"
                    f"Активные выборы: {active_elections}\n"
                    f"Действующие законы: {sum(1 for item in state.get('laws', []) if item['active'])}"
                )
                await _log(core, chat_id, user_id, office, "daily_brief", "Государственная сводка", text)
                await gov._publish(bot, chat_id, f"📰 <b>ГОСУДАРСТВЕННАЯ СВОДКА</b>\n\n{html.escape(text)}")
                message = "Государственная сводка опубликована."

            else:
                raise ValueError("Неизвестное полномочие.")

            return core.web.json_response({"ok": True, "message": message})
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    async def asset_js(_: Any):
        return core.web.FileResponse(ASSET_JS, headers={"Cache-Control": "no-store", "X-Government-Powers": "128"})

    async def asset_css(_: Any):
        return core.web.FileResponse(ASSET_CSS, headers={"Cache-Control": "no-store", "X-Government-Powers": "128"})

    original_start = core.start_webapp_server

    async def start_with_institutions(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены файлы полномочий Reality 128")
        original_runner = core.web.AppRunner

        def runner_factory(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/government-v127/powers-v128.js") not in keys:
                app.router.add_get("/government-v127/powers-v128.js", asset_js)
            if ("GET", "/government-v127/powers-v128.css") not in keys:
                app.router.add_get("/government-v127/powers-v128.css", asset_css)
            if ("POST", "/government-v128/api/action") not in keys:
                app.router.add_post("/government-v128/api/action", action_api)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_factory
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_institutions
