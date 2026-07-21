from __future__ import annotations

import html
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import career_rewards_v120 as career_rewards


VERSION = "Reality 126 · Надзор и санкции"
BASE_DIR = Path(__file__).resolve().parent
ADMIN_SCRIPT = BASE_DIR / "adminapp_v126" / "sanctions-admin.js"
MOSCOW = timezone(timedelta(hours=3))
ALLOWED_DURATIONS = {0, 600, 3_600, 21_600, 86_400, 259_200, 604_800}
SANCTION_TYPES: dict[str, dict[str, str]] = {
    "gambling": {"emoji": "🎲", "title": "Запрет азартных игр", "short": "кубик, монетка и рулетка"},
    "miniapp": {"emoji": "🎮", "title": "Запрет Mini App-игр", "short": "бег по крышам, ограбление и Ночной охотник"},
    "finance": {"emoji": "💸", "title": "Финансовая блокировка", "short": "переводы, займы и погашения"},
    "raid_event": {"emoji": "🌌", "title": "Запрет рейдов и событий", "short": "босс и событие дня"},
    "tasks": {"emoji": "🎯", "title": "Запрет заданий", "short": "действия и тайные задания"},
    "career_freeze": {"emoji": "⭐", "title": "Заморозка карьерных наград", "short": "новое карьерное влияние не начисляется"},
    "full_game": {"emoji": "🔒", "title": "Полная игровая блокировка", "short": "все игровые и экономические функции"},
}

GAMBLING_COMMANDS = {"dice", "coin", "roulette"}
MINIAPP_COMMANDS = {"games", "hunt"}
FINANCE_COMMANDS = {"finance", "money", "bank", "transfer", "loan", "repay", "debts", "credit"}
RAID_COMMANDS = {"boss", "event", "event_start"}
TASK_COMMANDS = {"action", "secret"}
GAMEPLAY_COMMANDS = {
    "influence", "fate", "today", "ego", "aura", "chsv", "power", "hero_day",
    "sabotage", "impeachment", "rebellion", "abilities", "talents", "tree",
}
ACTION_MARKER = re.compile(r"#ACTION_([0-9a-f]{10})", flags=re.IGNORECASE)
_RUNTIME_STARTED = False


def _route_keys(app: Any) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        canonical = str(getattr(resource, "canonical", "") or "")
        result.add((str(getattr(route, "method", "") or "").upper(), canonical))
    return result


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _duration_text(seconds: int) -> str:
    value = max(0, int(seconds))
    labels = {
        0: "бессрочно",
        600: "10 минут",
        3_600: "1 час",
        21_600: "6 часов",
        86_400: "24 часа",
        259_200: "3 дня",
        604_800: "7 дней",
    }
    if value in labels:
        return labels[value]
    if value < 3_600:
        return f"{max(1, value // 60)} мин."
    if value < 86_400:
        return f"{max(1, value // 3_600)} ч."
    return f"{max(1, value // 86_400)} д."


def _remaining_text(expires_at: int) -> str:
    if int(expires_at or 0) <= 0:
        return "бессрочно"
    return _duration_text(max(0, int(expires_at) - int(time.time())))


def _date_text(timestamp: int) -> str:
    if int(timestamp or 0) <= 0:
        return "до отдельного распоряжения"
    return datetime.fromtimestamp(int(timestamp), MOSCOW).strftime("%d.%m.%Y · %H:%M МСК")


def _type_lines(types: list[str]) -> str:
    lines: list[str] = []
    for key in types:
        spec = SANCTION_TYPES.get(key)
        if spec:
            lines.append(f"{spec['emoji']} <b>{html.escape(spec['title'])}</b> — {html.escape(spec['short'])}")
    return "\n".join(lines)


def _plain_type(key: str) -> str:
    spec = SANCTION_TYPES.get(key, {"emoji": "🚫", "title": "Ограничение"})
    return f"{spec['emoji']} {spec['title']}"


def _serialize(row: Any) -> dict[str, Any]:
    key = str(row["sanction_type"])
    spec = SANCTION_TYPES.get(key, {"emoji": "🚫", "title": key, "short": key})
    expires_at = _as_int(row["expires_at"])
    return {
        "id": _as_int(row["sanction_id"]),
        "chat_id": _as_int(row["chat_id"]),
        "user_id": _as_int(row["user_id"]),
        "type": key,
        "emoji": spec["emoji"],
        "title": spec["title"],
        "short": spec["short"],
        "reason": str(row["reason"] or "Решение администрации"),
        "issued_by": _as_int(row["issued_by"]),
        "issued_at": _as_int(row["issued_at"]),
        "expires_at": expires_at,
        "remaining": _remaining_text(expires_at),
        "active": bool(_as_int(row["active"])),
        "revoked_at": _as_int(row["revoked_at"]),
        "revoke_reason": str(row["revoke_reason"] or ""),
    }


async def active_sanctions(core: Any, chat_id: int, user_id: int) -> list[Any]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM sanctions_v126 WHERE chat_id=? AND user_id=? AND active=1 "
        "AND (expires_at=0 OR expires_at>?) ORDER BY CASE sanction_type WHEN 'full_game' THEN 0 ELSE 1 END,issued_at DESC",
        (int(chat_id), int(user_id), int(time.time())),
    )
    return list(await cursor.fetchall())


async def blocking_sanction(core: Any, chat_id: int, user_id: int, category: str) -> Any | None:
    if int(chat_id) >= 0 or int(user_id) <= 0:
        return None
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM sanctions_v126 WHERE chat_id=? AND user_id=? AND active=1 "
        "AND (expires_at=0 OR expires_at>?) AND sanction_type IN (?, 'full_game') "
        "ORDER BY CASE sanction_type WHEN 'full_game' THEN 0 ELSE 1 END,issued_at DESC LIMIT 1",
        (int(chat_id), int(user_id), int(time.time()), str(category)),
    )
    return await cursor.fetchone()


async def _player_link(core: Any, chat_id: int, user_id: int) -> str:
    player = await core.db.get_player(int(chat_id), int(user_id))
    if player is not None:
        return core.player_link(player)
    return f"<b>ID {int(user_id)}</b>"


async def send_issue_notice(
    core: Any,
    bot: Any,
    chat_id: int,
    user_id: int,
    types: list[str],
    duration: int,
    reason: str,
    expires_at: int,
) -> None:
    participant = await _player_link(core, chat_id, user_id)
    await bot.send_message(
        int(chat_id),
        "🚨 <b>САНКЦИОННОЕ ПОСТАНОВЛЕНИЕ</b>\n\n"
        f"В отношении участника {participant} официально введены ограничения.\n\n"
        f"<b>Тип санкций:</b>\n{_type_lines(types)}\n\n"
        f"<b>Срок:</b> {_duration_text(duration)}\n"
        f"<b>Причина:</b> {html.escape(reason)}\n"
        f"<b>Действует до:</b> {_date_text(expires_at)}\n\n"
        "До окончания срока указанные функции будут недоступны. Попытки обойти "
        "ограничения могут привести к ужесточению санкций.\n\n"
        "🏛 <b>Решение принято Надзором за гандонами.</b>",
    )


async def send_lift_notice(
    core: Any,
    bot: Any,
    chat_id: int,
    user_id: int,
    types: list[str],
    automatic: bool,
) -> None:
    participant = await _player_link(core, chat_id, user_id)
    heading = "⏳ <b>СРОК САНКЦИЙ ИСТЁК</b>" if automatic else "✅ <b>САНКЦИИ СНЯТЫ</b>"
    verb = "прекращены в связи с истечением установленного срока" if automatic else "официально прекращены"
    await bot.send_message(
        int(chat_id),
        f"{heading}\n\n"
        f"Ограничения в отношении участника {participant} {verb}.\n\n"
        f"<b>Снятые ограничения:</b>\n{_type_lines(types)}\n\n"
        "Участнику снова доступны соответствующие функции реальности.\n\n"
        "🏛 <b>Постановление Надзора за гандонами исполнено.</b>",
    )


async def issue_sanctions(
    core: Any,
    chat_id: int,
    user_id: int,
    types: list[str],
    duration: int,
    reason: str,
    admin_id: int,
) -> tuple[list[str], int]:
    clean = [key for key in dict.fromkeys(types) if key in SANCTION_TYPES]
    if "full_game" in clean:
        clean = ["full_game"]
    if not clean:
        raise ValueError("Выбери хотя бы один вид санкций.")
    if int(duration) not in ALLOWED_DURATIONS:
        raise ValueError("Недопустимый срок санкций.")
    clean_reason = str(reason or "").strip()
    if len(clean_reason) < 3:
        raise ValueError("Укажи причину санкций.")
    if await core.db.get_player(int(chat_id), int(user_id)) is None:
        raise ValueError("Участник не найден в выбранной беседе.")

    now = int(time.time())
    expires_at = 0 if int(duration) == 0 else now + int(duration)
    conn = core.db._require_connection()
    async with core.db.lock:
        for key in clean:
            await conn.execute(
                "UPDATE sanctions_v126 SET active=0,revoked_at=?,revoked_by=?,revoke_reason='Заменено новым постановлением' "
                "WHERE chat_id=? AND user_id=? AND sanction_type=? AND active=1",
                (now, int(admin_id), int(chat_id), int(user_id), key),
            )
            await conn.execute(
                "INSERT INTO sanctions_v126(chat_id,user_id,sanction_type,reason,issued_by,issued_at,expires_at,active) "
                "VALUES(?,?,?,?,?,?,?,1)",
                (int(chat_id), int(user_id), key, clean_reason, int(admin_id), now, expires_at),
            )
        await conn.commit()
    return clean, expires_at


async def revoke_sanctions(
    core: Any,
    chat_id: int,
    user_id: int,
    admin_id: int,
    sanction_id: int = 0,
    sanction_type: str = "",
    reason: str = "Досрочно снято администрацией",
) -> list[str]:
    conn = core.db._require_connection()
    where = ["chat_id=?", "user_id=?", "active=1", "(expires_at=0 OR expires_at>?)"]
    args: list[Any] = [int(chat_id), int(user_id), int(time.time())]
    if int(sanction_id) > 0:
        where.append("sanction_id=?")
        args.append(int(sanction_id))
    elif sanction_type in SANCTION_TYPES:
        where.append("sanction_type=?")
        args.append(sanction_type)
    cursor = await conn.execute(
        f"SELECT * FROM sanctions_v126 WHERE {' AND '.join(where)} ORDER BY issued_at DESC",
        tuple(args),
    )
    rows = list(await cursor.fetchall())
    if not rows:
        raise ValueError("Активные санкции не найдены.")
    ids = [int(row["sanction_id"]) for row in rows]
    placeholders = ",".join("?" for _ in ids)
    now = int(time.time())
    async with core.db.lock:
        await conn.execute(
            f"UPDATE sanctions_v126 SET active=0,revoked_at=?,revoked_by=?,revoke_reason=? "
            f"WHERE sanction_id IN ({placeholders})",
            (now, int(admin_id), str(reason), *ids),
        )
        await conn.commit()
    return list(dict.fromkeys(str(row["sanction_type"]) for row in rows))


def _command_category(text: str) -> str | None:
    value = str(text or "").strip()
    if not value.startswith("/"):
        return None
    command = value[1:].split(maxsplit=1)[0].split("@", 1)[0].casefold()
    if command in GAMBLING_COMMANDS:
        return "gambling"
    if command in MINIAPP_COMMANDS:
        return "miniapp"
    if command in FINANCE_COMMANDS:
        return "finance"
    if command in RAID_COMMANDS:
        return "raid_event"
    if command in TASK_COMMANDS:
        return "tasks"
    if command in GAMEPLAY_COMMANDS:
        return "gameplay"
    return None


def _callback_category(data: str) -> str | None:
    value = str(data or "").casefold()
    if value.startswith("botgame:"):
        return "gambling"
    if value.startswith("hub121:"):
        action = value[len("hub121:"):]
        if action in {"games:dice", "games:coin", "games:roulette"} or action.startswith("wager:"):
            return "gambling"
        if action in {"games:secret", "games:action"}:
            return "tasks"
        if action not in {"games:menu", "roles:career", "roles:all", "roles:top"}:
            return "gameplay"
        return None
    if value.startswith(("fin112:", "fin118:", "finance:")):
        return "finance"
    if value.startswith(("event", "reality_event", "boss", "raid")):
        return "raid_event"
    if "secret" in value or "action_task" in value or value.startswith("mission"):
        return "tasks"
    return None


async def _blocked_text(core: Any, row: Any) -> str:
    key = str(row["sanction_type"])
    spec = SANCTION_TYPES.get(key, {"emoji": "🚫", "title": "Ограничение"})
    return (
        f"🚫 <b>ДОСТУП ОГРАНИЧЕН</b>\n\n"
        f"Санкция: {spec['emoji']} <b>{html.escape(spec['title'])}</b>\n"
        f"Осталось: <b>{html.escape(_remaining_text(_as_int(row['expires_at'])))}</b>\n"
        f"Причина: <b>{html.escape(str(row['reason'] or 'Решение администрации'))}</b>\n\n"
        "🏛 Решение Надзора за гандонами."
    )


class SanctionMessageMiddleware(BaseMiddleware):
    def __init__(self, core: Any):
        self.core = core

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not event.from_user or int(event.chat.id) >= 0:
            return await handler(event, data)
        category = _command_category(event.text or event.caption or "")
        if category is None:
            return await handler(event, data)
        row = await blocking_sanction(self.core, event.chat.id, event.from_user.id, category)
        if row is None:
            return await handler(event, data)
        await self.core.ephemeral_reply(event, await _blocked_text(self.core, row), delay_seconds=8)
        return None


class SanctionCallbackMiddleware(BaseMiddleware):
    def __init__(self, core: Any):
        self.core = core

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        category = _callback_category(event.data or "")
        if category is None or not event.from_user:
            return await handler(event, data)
        chat_id = int(event.message.chat.id) if event.message and int(event.message.chat.id) < 0 else 0
        if not chat_id and str(event.data or "").startswith("botgame:"):
            game = await self.core.db.get_bot_game(str(event.data).split(":", 1)[1])
            if game is not None:
                chat_id = int(game["chat_id"])
        if not chat_id:
            return await handler(event, data)
        row = await blocking_sanction(self.core, chat_id, event.from_user.id, category)
        if row is None:
            return await handler(event, data)
        spec = SANCTION_TYPES.get(str(row["sanction_type"]), {"title": "Ограничение"})
        await event.answer(
            f"🚫 {spec['title']}\nОсталось: {_remaining_text(_as_int(row['expires_at']))}",
            show_alert=True,
        )
        return None


async def _task_candidate(core: Any, message: Message) -> Any | None:
    if not message.from_user:
        return None
    if message.reply_to_message:
        replied = message.reply_to_message.text or message.reply_to_message.caption or ""
        match = ACTION_MARKER.search(replied)
        if match:
            return await core.db.get_action_task(match.group(1).lower())
    return await core.db.get_open_social_task(int(message.chat.id), int(message.from_user.id))


def _web_category(path: str) -> str | None:
    value = str(path or "").casefold()
    if value.startswith("/admin") or "/api/" not in value:
        return None
    if "finance" in value:
        return "finance"
    if value.startswith("/games/") or any(part in value for part in ("night-hunter", "night_hunter", "rooftop", "heist")):
        return "miniapp"
    if any(part in value for part in ("/boss", "/raid", "/events-v", "/event/")):
        return "raid_event"
    if "/talent" in value:
        return "gameplay"
    return None


async def _request_identity(core: Any, request: Any) -> tuple[Any | None, int]:
    user, start_param = core._webapp_auth(request)
    if user is None:
        return None, 0
    try:
        data = await request.json()
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    chat_id = _as_int(data.get("chat_id") or request.query.get("chat_id"))
    if not chat_id:
        matches = re.findall(r"-\d+", str(start_param or ""))
        if matches:
            chat_id = _as_int(matches[-1])
    return user, chat_id


async def expiry_loop(core: Any, bot: Any) -> None:
    while True:
        try:
            now = int(time.time())
            conn = core.db._require_connection()
            cursor = await conn.execute(
                "SELECT * FROM sanctions_v126 WHERE active=1 AND expires_at>0 AND expires_at<=? "
                "ORDER BY chat_id,user_id,expires_at",
                (now,),
            )
            rows = list(await cursor.fetchall())
            groups: dict[tuple[int, int], list[Any]] = {}
            for row in rows:
                groups.setdefault((int(row["chat_id"]), int(row["user_id"])), []).append(row)
            if rows:
                ids = [int(row["sanction_id"]) for row in rows]
                placeholders = ",".join("?" for _ in ids)
                async with core.db.lock:
                    await conn.execute(
                        f"UPDATE sanctions_v126 SET active=0,revoked_at=?,revoke_reason='Срок санкции истёк' "
                        f"WHERE sanction_id IN ({placeholders})",
                        (now, *ids),
                    )
                    await conn.commit()
                for (chat_id, user_id), group in groups.items():
                    try:
                        await send_lift_notice(
                            core, bot, chat_id, user_id,
                            list(dict.fromkeys(str(row["sanction_type"]) for row in group)),
                            True,
                        )
                    except Exception:
                        core.logging.exception("Не удалось сообщить об окончании санкций")
        except Exception:
            core.logging.exception("Ошибка цикла санкций Reality 126")
        await core.asyncio.sleep(30)


def install_sanctions_v126(core: Any) -> None:
    global _RUNTIME_STARTED
    if getattr(core, "_sanctions_v126_installed", False):
        return
    core._sanctions_v126_installed = True
    core.SANCTIONS_VERSION = VERSION
    core.SANCTION_TYPES = SANCTION_TYPES
    core.get_active_sanctions = lambda chat_id, user_id: active_sanctions(core, chat_id, user_id)
    core.get_blocking_sanction = lambda chat_id, user_id, category: blocking_sanction(core, chat_id, user_id, category)

    original_connect = core.Database.connect

    async def connect_with_sanctions(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sanctions_v126(
                    sanction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    sanction_type TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    issued_by INTEGER NOT NULL,
                    issued_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL DEFAULT 0,
                    active INTEGER NOT NULL DEFAULT 1,
                    revoked_at INTEGER NOT NULL DEFAULT 0,
                    revoked_by INTEGER NOT NULL DEFAULT 0,
                    revoke_reason TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_sanctions_active_v126
                ON sanctions_v126(chat_id,user_id,active,expires_at);
                CREATE INDEX IF NOT EXISTS idx_sanctions_history_v126
                ON sanctions_v126(chat_id,user_id,sanction_id DESC);
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_sanctions

    core.router.message.outer_middleware(SanctionMessageMiddleware(core))
    core.router.callback_query.outer_middleware(SanctionCallbackMiddleware(core))

    original_roulette = core.apply_roulette

    async def apply_roulette_with_sanctions(chat_id: int, user: Any) -> str:
        row = await blocking_sanction(core, int(chat_id), int(user.id), "gambling")
        if row is not None:
            return await _blocked_text(core, row)
        return await original_roulette(chat_id, user)

    core.apply_roulette = apply_roulette_with_sanctions

    original_complete = core.maybe_complete_action_task

    async def complete_task_with_sanctions(message: Message) -> bool:
        if message.from_user and int(message.chat.id) < 0:
            task = await _task_candidate(core, message)
            if task is not None:
                row = await blocking_sanction(core, message.chat.id, message.from_user.id, "tasks")
                if row is not None:
                    await core.ephemeral_reply(message, await _blocked_text(core, row), delay_seconds=8)
                    return True
        return await original_complete(message)

    core.maybe_complete_action_task = complete_task_with_sanctions

    original_award = career_rewards.award

    async def award_with_sanctions(
        core_arg: Any,
        chat_id: int,
        user_id: int,
        amount: int,
        source_type: str,
        source_id: str,
        reason: str,
    ) -> int:
        row = await blocking_sanction(core_arg, int(chat_id), int(user_id), "career_freeze")
        if row is not None:
            return 0
        return await original_award(core_arg, chat_id, user_id, amount, source_type, source_id, reason)

    career_rewards.award = award_with_sanctions
    core.add_career_points = lambda chat_id, user_id, amount, reason, source_id: award_with_sanctions(
        core, chat_id, user_id, amount, "manual", source_id, reason
    )

    @core.web.middleware
    async def sanctions_web_middleware(request: Any, handler: Any):
        category = _web_category(request.path) if request.method.upper() == "POST" else None
        if category is not None:
            user, chat_id = await _request_identity(core, request)
            if user is not None and chat_id < 0:
                row = await blocking_sanction(core, chat_id, int(user.id), category)
                if row is not None:
                    spec = SANCTION_TYPES.get(str(row["sanction_type"]), {"title": "Ограничение"})
                    return core.web.json_response(
                        {
                            "ok": False,
                            "reason": f"Действует санкция: {spec['title']}. Осталось: {_remaining_text(_as_int(row['expires_at']))}.",
                            "sanctioned": True,
                        },
                        status=403,
                    )
        return await handler(request)

    previous_application = core.web.Application

    def application_with_sanctions(*args: Any, **kwargs: Any):
        middlewares = list(kwargs.pop("middlewares", []) or [])
        kwargs["middlewares"] = [sanctions_web_middleware, *middlewares]
        return previous_application(*args, **kwargs)

    core.web.Application = application_with_sanctions

    def admin_error(reason: str, status: int = 400):
        return core.web.json_response({"ok": False, "reason": reason}, status=status)

    def admin_auth(request: Any):
        user, reason = core._webapp_auth(request)
        if user is None:
            return None, admin_error(reason or "Нет авторизации Telegram.", 401)
        if int(user.id) != int(core.DEVELOPER_ID):
            return None, admin_error("Раздел санкций доступен только владельцу бота.", 403)
        return user, None

    async def admin_payload(request: Any) -> dict[str, Any]:
        try:
            data = await request.json()
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    async def sanctions_state(request: Any):
        _, problem = admin_auth(request)
        if problem is not None:
            return problem
        chat_id = _as_int(request.query.get("chat_id"))
        user_id = _as_int(request.query.get("user_id"))
        if chat_id >= 0 or user_id <= 0:
            return admin_error("Выбери беседу и участника.")
        conn = core.db._require_connection()
        cursor = await conn.execute(
            "SELECT * FROM sanctions_v126 WHERE chat_id=? AND user_id=? "
            "ORDER BY sanction_id DESC LIMIT 60",
            (chat_id, user_id),
        )
        rows = list(await cursor.fetchall())
        now = int(time.time())
        active = [_serialize(row) for row in rows if int(row["active"]) and (not int(row["expires_at"]) or int(row["expires_at"]) > now)]
        history = [_serialize(row) for row in rows]
        return core.web.json_response(
            {
                "ok": True,
                "version": VERSION,
                "types": SANCTION_TYPES,
                "durations": [
                    {"seconds": 600, "title": "10 минут"},
                    {"seconds": 3_600, "title": "1 час"},
                    {"seconds": 21_600, "title": "6 часов"},
                    {"seconds": 86_400, "title": "24 часа"},
                    {"seconds": 259_200, "title": "3 дня"},
                    {"seconds": 604_800, "title": "7 дней"},
                    {"seconds": 0, "title": "Бессрочно"},
                ],
                "active": active,
                "history": history,
            }
        )

    async def sanctions_action(request: Any):
        admin, problem = admin_auth(request)
        if problem is not None:
            return problem
        data = await admin_payload(request)
        action = str(data.get("action") or "")
        chat_id = _as_int(data.get("chat_id"))
        user_id = _as_int(data.get("user_id"))
        if chat_id >= 0 or user_id <= 0:
            return admin_error("Выбери беседу и участника.")
        bot = request.app["bot"]
        try:
            if action == "issue":
                values = data.get("types") if isinstance(data.get("types"), list) else []
                duration = _as_int(data.get("duration"))
                reason = str(data.get("reason") or "")
                types, expires_at = await issue_sanctions(
                    core, chat_id, user_id, [str(value) for value in values], duration, reason, int(admin.id)
                )
                await send_issue_notice(core, bot, chat_id, user_id, types, duration, reason.strip(), expires_at)
                message = f"Введены санкции: {', '.join(_plain_type(key) for key in types)}."
            elif action == "revoke":
                types = await revoke_sanctions(
                    core,
                    chat_id,
                    user_id,
                    int(admin.id),
                    sanction_id=_as_int(data.get("sanction_id")),
                    sanction_type=str(data.get("type") or ""),
                )
                await send_lift_notice(core, bot, chat_id, user_id, types, False)
                message = f"Санкции сняты: {', '.join(_plain_type(key) for key in types)}."
            else:
                return admin_error("Неизвестное действие раздела санкций.")
        except Exception as exc:
            return admin_error(str(exc))
        return core.web.json_response({"ok": True, "message": message})

    async def sanctions_script(_: Any):
        return core.web.FileResponse(
            ADMIN_SCRIPT,
            headers={"Cache-Control": "no-store", "X-Sanctions": "reality-126"},
        )

    original_start = core.start_webapp_server

    async def start_with_sanctions(bot: Any):
        global _RUNTIME_STARTED
        if not ADMIN_SCRIPT.is_file():
            raise RuntimeError(f"Не найден интерфейс санкций: {ADMIN_SCRIPT}")
        original_runner = core.web.AppRunner

        def runner_factory(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/admin-v126/sanctions-admin.js") not in keys:
                app.router.add_get("/admin-v126/sanctions-admin.js", sanctions_script)
            if ("GET", "/sanctions-v126/api/state") not in keys:
                app.router.add_get("/sanctions-v126/api/state", sanctions_state)
            if ("POST", "/sanctions-v126/api/action") not in keys:
                app.router.add_post("/sanctions-v126/api/action", sanctions_action)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_factory
        try:
            runner = await original_start(bot)
        finally:
            core.web.AppRunner = original_runner
        if not _RUNTIME_STARTED:
            _RUNTIME_STARTED = True
            core.spawn_background_task(expiry_loop(core, bot))
        return runner

    core.start_webapp_server = start_with_sanctions

    @core.router.message(Command("sanctions"))
    async def cmd_my_sanctions_v126(message: Message) -> None:
        if not message.from_user or int(message.chat.id) >= 0:
            return
        rows = await active_sanctions(core, message.chat.id, message.from_user.id)
        if not rows:
            await message.answer("✅ <b>Активных санкций нет.</b>")
            return
        lines = ["🚫 <b>МОИ АКТИВНЫЕ САНКЦИИ</b>", ""]
        for row in rows:
            key = str(row["sanction_type"])
            lines.append(
                f"{_plain_type(key)}\n"
                f"Осталось: <b>{html.escape(_remaining_text(_as_int(row['expires_at'])))}</b>\n"
                f"Причина: {html.escape(str(row['reason']))}\n"
            )
        lines.append("🏛 Надзор за гандонами.")
        await message.answer("\n".join(lines))
