from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiogram.types import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from career_model_v120 import (
    CAREER_CENTER,
    CAREER_DUST,
    CAREER_EXTRAS,
    CAREER_HERO,
    CAREER_SECONDARY,
    fmt,
)


VERSION = "Reality 123 · Карьерный админ-центр"
ADMIN_DIR = Path(__file__).resolve().parent / "adminapp_v123"
ROLE_PRESETS = {
    "decoration": {"emoji": "🪑", "title": "Декорация", "points": 0},
    "dust": {"emoji": "🌫", "title": "Пыль", "points": CAREER_DUST},
    "extras": {"emoji": "👥", "title": "Массовка", "points": CAREER_EXTRAS},
    "secondary": {"emoji": "🎭", "title": "Второстепенная роль", "points": CAREER_SECONDARY},
    "hero": {"emoji": "👑", "title": "Главный герой", "points": CAREER_HERO},
    "center": {"emoji": "🌌", "title": "Центр Вселенной", "points": CAREER_CENTER},
}


def _route_keys(app: Any) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        canonical = str(getattr(resource, "canonical", "") or "")
        keys.add((str(getattr(route, "method", "") or "").upper(), canonical))
    return keys


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _career_role(value: int) -> dict[str, Any]:
    points = max(0, int(value))
    if points >= CAREER_CENTER:
        key = "center"
    elif points >= CAREER_HERO:
        key = "hero"
    elif points >= CAREER_SECONDARY:
        key = "secondary"
    elif points >= CAREER_EXTRAS:
        key = "extras"
    elif points >= CAREER_DUST:
        key = "dust"
    else:
        key = "decoration"
    spec = ROLE_PRESETS[key]
    order = ["decoration", "dust", "extras", "secondary", "hero", "center"]
    index = order.index(key)
    next_key = order[index + 1] if index + 1 < len(order) else None
    next_points = int(ROLE_PRESETS[next_key]["points"]) if next_key else points
    floor = int(spec["points"])
    if next_key:
        span = max(1, next_points - floor)
        progress = max(0.0, min(1.0, (points - floor) / span))
        remaining = max(0, next_points - points)
    else:
        progress = 1.0
        remaining = 0
    return {
        "key": key,
        "emoji": spec["emoji"],
        "title": spec["title"],
        "floor": floor,
        "next_key": next_key,
        "next_title": ROLE_PRESETS[next_key]["title"] if next_key else None,
        "next_points": next_points if next_key else None,
        "remaining": remaining,
        "progress": round(progress, 4),
    }


def _day_bounds() -> tuple[int, int]:
    current = datetime.now(timezone.utc)
    start = int(datetime(current.year, current.month, current.day, tzinfo=timezone.utc).timestamp())
    return start, start + 86400


def install_admin_career_v123(core: Any) -> None:
    if getattr(core, "_admin_career_v123_installed", False):
        return
    core._admin_career_v123_installed = True
    core.ADMIN_CENTER_VERSION = VERSION

    original_start_server = core.start_webapp_server

    def error(reason: str, status: int = 400):
        return core.web.json_response({"ok": False, "reason": reason}, status=status)

    def auth(request: Any):
        user, reason = core._webapp_auth(request)
        if user is None:
            return None, error(reason or "Нет авторизации Telegram.", 401)
        if int(user.id) != int(core.DEVELOPER_ID):
            return None, error("Админ-центр доступен только владельцу бота.", 403)
        return user, None

    async def payload(request: Any) -> dict[str, Any]:
        try:
            data = await request.json()
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    async def table_exists(conn: Any, name: str) -> bool:
        cursor = await conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (name,),
        )
        return await cursor.fetchone() is not None

    async def chat_rows() -> list[Any]:
        conn = core.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT chat_id,COUNT(*) users,MAX(updated_at) updated_at,
                   COALESCE(SUM(points),0) wallet_total,
                   COALESCE(SUM(career_points),0) career_total
            FROM players WHERE chat_id<0
            GROUP BY chat_id ORDER BY updated_at DESC LIMIT 40
            """
        )
        return list(await cursor.fetchall())

    async def resolve_chat(requested: int) -> int:
        rows = await chat_rows()
        available = {int(row["chat_id"]) for row in rows}
        if requested in available:
            return requested
        latest = await core.db.admin_latest_group_player(core.DEVELOPER_ID)
        if latest is not None and int(latest.chat_id) in available:
            return int(latest.chat_id)
        return int(rows[0]["chat_id"]) if rows else 0

    async def chat_title(bot: Any, chat_id: int) -> str:
        try:
            chat = await bot.get_chat(chat_id)
            return str(chat.title or chat.full_name or chat_id)
        except Exception:
            return str(chat_id)

    async def player_row(chat_id: int, user_id: int) -> Any | None:
        conn = core.db._require_connection()
        cursor = await conn.execute(
            "SELECT * FROM players WHERE chat_id=? AND user_id=? LIMIT 1",
            (chat_id, user_id),
        )
        return await cursor.fetchone()

    async def resolve_target(chat_id: int, requested: int) -> Any | None:
        if not chat_id:
            return None
        if requested:
            found = await player_row(chat_id, requested)
            if found is not None:
                return found
        own = await player_row(chat_id, int(core.DEVELOPER_ID))
        if own is not None:
            return own
        conn = core.db._require_connection()
        cursor = await conn.execute(
            "SELECT * FROM players WHERE chat_id=? ORDER BY career_points DESC,points DESC LIMIT 1",
            (chat_id,),
        )
        return await cursor.fetchone()

    def serialize_player(row: Any) -> dict[str, Any]:
        career = _as_int(row["career_points"])
        return {
            "chat_id": _as_int(row["chat_id"]),
            "user_id": _as_int(row["user_id"]),
            "username": str(row["username"] or ""),
            "full_name": str(row["full_name"] or f"Участник {row['user_id']}"),
            "points": _as_int(row["points"]),
            "career_points": career,
            "message_count": _as_int(row["message_count"]),
            "updated_at": _as_int(row["updated_at"]),
            "role": _career_role(career),
        }

    async def quick_users(chat_id: int, query: str = "", limit: int = 30) -> list[dict[str, Any]]:
        conn = core.db._require_connection()
        clean = query.strip().lstrip("@").casefold()
        if clean:
            like = f"%{clean}%"
            cursor = await conn.execute(
                """
                SELECT * FROM players WHERE chat_id=? AND (
                    CAST(user_id AS TEXT)=? OR lower(COALESCE(username,'')) LIKE ?
                    OR lower(full_name) LIKE ?)
                ORDER BY career_points DESC,points DESC LIMIT ?
                """,
                (chat_id, clean, like, like, limit),
            )
        else:
            cursor = await conn.execute(
                "SELECT * FROM players WHERE chat_id=? ORDER BY career_points DESC,points DESC LIMIT ?",
                (chat_id, limit),
            )
        return [serialize_player(row) for row in await cursor.fetchall()]

    async def wallet_history(chat_id: int, user_id: int, limit: int = 20) -> list[dict[str, Any]]:
        conn = core.db._require_connection()
        if not await table_exists(conn, "score_log"):
            return []
        cursor = await conn.execute(
            "SELECT id,delta,reason,created_at FROM score_log WHERE chat_id=? AND user_id=? ORDER BY id DESC LIMIT ?",
            (chat_id, user_id, limit),
        )
        return [
            {
                "id": _as_int(row["id"]),
                "delta": _as_int(row["delta"]),
                "reason": str(row["reason"] or "Операция"),
                "created_at": _as_int(row["created_at"]),
            }
            for row in await cursor.fetchall()
        ]

    async def career_history(chat_id: int, user_id: int, limit: int = 20) -> list[dict[str, Any]]:
        conn = core.db._require_connection()
        if not await table_exists(conn, "career_log_v120"):
            return []
        cursor = await conn.execute(
            """
            SELECT id,delta,reason,source_type,source_id,created_at
            FROM career_log_v120 WHERE chat_id=? AND user_id=?
            ORDER BY id DESC LIMIT ?
            """,
            (chat_id, user_id, limit),
        )
        return [
            {
                "id": _as_int(row["id"]),
                "delta": _as_int(row["delta"]),
                "reason": str(row["reason"] or "Карьерная операция"),
                "source_type": str(row["source_type"] or "system"),
                "source_id": str(row["source_id"] or ""),
                "created_at": _as_int(row["created_at"]),
            }
            for row in await cursor.fetchall()
        ]

    async def finance_summary(chat_id: int, user_id: int) -> dict[str, int]:
        conn = core.db._require_connection()
        result = {"borrowed": 0, "lent": 0, "overdue": 0, "active_loans": 0}
        if not await table_exists(conn, "finance_loans_v112"):
            return result
        cursor = await conn.execute(
            """
            SELECT
              COALESCE(SUM(CASE WHEN borrower_id=? AND status IN ('active','overdue') THEN remaining_due ELSE 0 END),0) borrowed,
              COALESCE(SUM(CASE WHEN lender_id=? AND status IN ('active','overdue') THEN remaining_due ELSE 0 END),0) lent,
              COALESCE(SUM(CASE WHEN borrower_id=? AND status='overdue' THEN remaining_due ELSE 0 END),0) overdue,
              COALESCE(SUM(CASE WHEN (borrower_id=? OR lender_id=?) AND status IN ('active','overdue') THEN 1 ELSE 0 END),0) active_loans
            FROM finance_loans_v112 WHERE chat_id=?
            """,
            (user_id, user_id, user_id, user_id, user_id, chat_id),
        )
        row = await cursor.fetchone()
        if row:
            result = {key: _as_int(row[key]) for key in result}
        return result

    async def talent_summary(chat_id: int, user_id: int) -> dict[str, int]:
        conn = core.db._require_connection()
        result = {"total": 0, "spent": 0, "available": 0}
        if not await table_exists(conn, "talent_profiles"):
            return result
        cursor = await conn.execute(
            "SELECT total_points,spent_points FROM talent_profiles WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        row = await cursor.fetchone()
        if row:
            result["total"] = _as_int(row["total_points"])
            result["spent"] = _as_int(row["spent_points"])
            result["available"] = max(0, result["total"] - result["spent"])
        return result

    async def admin_history(limit: int = 30) -> list[dict[str, Any]]:
        conn = core.db._require_connection()
        if not await table_exists(conn, "admin_action_log_v62"):
            return []
        cursor = await conn.execute(
            """
            SELECT action_id,chat_id,target_user_id,action,detail,created_at
            FROM admin_action_log_v62 ORDER BY action_id DESC LIMIT ?
            """,
            (limit,),
        )
        return [
            {
                "id": _as_int(row["action_id"]),
                "chat_id": _as_int(row["chat_id"]),
                "target_user_id": _as_int(row["target_user_id"]),
                "action": str(row["action"]),
                "detail": str(row["detail"]),
                "created_at": _as_int(row["created_at"]),
            }
            for row in await cursor.fetchall()
        ]

    async def log_admin(admin_id: int, chat_id: int, user_id: int, action: str, detail: str, payload_data: dict[str, Any]) -> None:
        conn = core.db._require_connection()
        if not await table_exists(conn, "admin_action_log_v62"):
            return
        async with core.db.lock:
            await conn.execute(
                """
                INSERT INTO admin_action_log_v62(
                    admin_id,chat_id,target_user_id,action,detail,payload_json,reversible,created_at
                ) VALUES(?,?,?,?,?,?,0,?)
                """,
                (admin_id, chat_id, user_id or None, action, detail, json.dumps(payload_data, ensure_ascii=False), int(time.time())),
            )
            await conn.commit()

    async def state_api(request: Any):
        admin, problem = auth(request)
        if problem is not None:
            return problem
        requested_chat = _as_int(request.query.get("chat_id"))
        requested_user = _as_int(request.query.get("user_id"))
        chat_id = await resolve_chat(requested_chat)
        target_row = await resolve_target(chat_id, requested_user)
        target = serialize_player(target_row) if target_row is not None else None
        bot = request.app["bot"]
        chats = []
        for row in await chat_rows():
            item_chat_id = _as_int(row["chat_id"])
            chats.append(
                {
                    "chat_id": item_chat_id,
                    "title": await chat_title(bot, item_chat_id),
                    "users": _as_int(row["users"]),
                    "wallet_total": _as_int(row["wallet_total"]),
                    "career_total": _as_int(row["career_total"]),
                }
            )
        start, end = _day_bounds()
        conn = core.db._require_connection()
        career_today = 0
        wallet_today = 0
        if await table_exists(conn, "career_log_v120"):
            cursor = await conn.execute(
                "SELECT COALESCE(SUM(CASE WHEN delta>0 THEN delta ELSE 0 END),0) amount FROM career_log_v120 WHERE chat_id=? AND created_at>=? AND created_at<?",
                (chat_id, start, end),
            )
            row = await cursor.fetchone()
            career_today = _as_int(row["amount"] if row else 0)
        if await table_exists(conn, "score_log"):
            cursor = await conn.execute(
                "SELECT COALESCE(SUM(CASE WHEN delta>0 THEN delta ELSE 0 END),0) amount FROM score_log WHERE chat_id=? AND created_at>=? AND created_at<?",
                (chat_id, start, end),
            )
            row = await cursor.fetchone()
            wallet_today = _as_int(row["amount"] if row else 0)
        selected_chat = next((item for item in chats if item["chat_id"] == chat_id), None)
        user_id = _as_int((target or {}).get("user_id"))
        return core.web.json_response(
            {
                "ok": True,
                "version": VERSION,
                "admin": {"user_id": int(admin.id), "name": admin.full_name},
                "chats": chats,
                "selected_chat": selected_chat or {"chat_id": chat_id, "title": str(chat_id), "users": 0, "wallet_total": 0, "career_total": 0},
                "target": target,
                "quick_users": await quick_users(chat_id) if chat_id else [],
                "wallet_history": await wallet_history(chat_id, user_id) if target else [],
                "career_history": await career_history(chat_id, user_id) if target else [],
                "finance": await finance_summary(chat_id, user_id) if target else {},
                "talents": await talent_summary(chat_id, user_id) if target else {},
                "admin_history": await admin_history(),
                "today": {"wallet": wallet_today, "career": career_today},
                "role_presets": ROLE_PRESETS,
                "legacy_url": f"/admin-v76/?chat_id={chat_id}&user_id={user_id}&from=123",
            }
        )

    async def users_api(request: Any):
        _, problem = auth(request)
        if problem is not None:
            return problem
        chat_id = await resolve_chat(_as_int(request.query.get("chat_id")))
        query = str(request.query.get("q") or "")
        return core.web.json_response({"ok": True, "users": await quick_users(chat_id, query, 50)})

    async def set_career(chat_id: int, user_id: int, value: int, reason: str, source_id: str) -> tuple[int, int]:
        conn = core.db._require_connection()
        row = await player_row(chat_id, user_id)
        if row is None:
            raise ValueError("Участник не найден в выбранной беседе.")
        before = _as_int(row["career_points"])
        after = max(0, min(100_000_000, int(value)))
        created_at = int(time.time())
        async with core.db.lock:
            await conn.execute(
                "UPDATE players SET career_points=?,career_initialized=1,updated_at=? WHERE chat_id=? AND user_id=?",
                (after, created_at, chat_id, user_id),
            )
            await conn.execute(
                """
                INSERT INTO career_log_v120(chat_id,user_id,delta,reason,source_type,source_id,created_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (chat_id, user_id, after - before, reason, "admin", source_id, created_at),
            )
            await conn.commit()
        return before, after

    async def action_api(request: Any):
        admin, problem = auth(request)
        if problem is not None:
            return problem
        data = await payload(request)
        action = str(data.get("action") or "")
        chat_id = await resolve_chat(_as_int(data.get("chat_id")))
        user_id = _as_int(data.get("user_id"))
        value = _as_int(data.get("value"))
        if not chat_id:
            return error("Не выбрана беседа.")
        target_row = await player_row(chat_id, user_id) if user_id else None
        if action not in {"chat_cooldowns_reset"} and target_row is None:
            return error("Сначала выбери участника.")
        message = "Готово."
        bot = request.app["bot"]

        try:
            if action == "wallet_delta":
                before = _as_int(target_row["points"])
                after_value = max(0, min(1_000_000_000, before + value))
                _, player = await core.db.set_player_points(chat_id, user_id, after_value, "admin_v123_wallet_delta")
                message = f"Обычное влияние: {fmt(before)} → {fmt(int(player.points))}."
            elif action == "wallet_set":
                before = _as_int(target_row["points"])
                after_value = max(0, min(1_000_000_000, value))
                _, player = await core.db.set_player_points(chat_id, user_id, after_value, "admin_v123_wallet_set")
                message = f"Обычное влияние установлено: {fmt(before)} → {fmt(int(player.points))}."
            elif action == "career_delta":
                before = _as_int(target_row["career_points"])
                old, new = await set_career(chat_id, user_id, before + value, "Изменено в админ-центре", f"admin-delta:{admin.id}:{time.time_ns()}")
                message = f"Карьерное влияние: {fmt(old)} → {fmt(new)}."
            elif action == "career_set":
                old, new = await set_career(chat_id, user_id, value, "Установлено в админ-центре", f"admin-set:{admin.id}:{time.time_ns()}")
                message = f"Карьерное влияние установлено: {fmt(old)} → {fmt(new)}."
            elif action == "role_set":
                key = str(data.get("role") or "")
                if key not in ROLE_PRESETS:
                    return error("Неизвестная роль.")
                amount = int(ROLE_PRESETS[key]["points"])
                old, new = await set_career(chat_id, user_id, amount, f"Назначена роль: {ROLE_PRESETS[key]['title']}", f"admin-role:{key}:{admin.id}:{time.time_ns()}")
                message = f"Роль назначена: {ROLE_PRESETS[key]['emoji']} {ROLE_PRESETS[key]['title']} · {fmt(old)} → {fmt(new)}."
            elif action == "cooldown_user_chat":
                changed = await core.db.admin_reset_user_cooldowns(user_id, chat_id)
                message = f"Кулдауны участника в этой беседе сброшены: {changed}."
            elif action == "cooldown_user_global":
                changed = await core.db.admin_reset_user_cooldowns(user_id, None)
                message = f"Глобальные кулдауны участника сброшены: {changed}."
            elif action == "chat_cooldowns_reset":
                changed = await core.db.admin_reset_chat_cooldowns(chat_id)
                message = f"Кулдауны беседы сброшены: {changed}."
            elif action == "stats_user_reset":
                await core.db.admin_reset_behavior(chat_id, user_id)
                message = "Статистика активности участника обнулена. Балансы сохранены."
            elif action == "mute":
                minutes = max(1, min(1440, value or 5))
                until = datetime.now(timezone.utc).timestamp() + minutes * 60
                await bot.restrict_chat_member(
                    chat_id,
                    user_id,
                    ChatPermissions(can_send_messages=False),
                    until_date=datetime.fromtimestamp(until, timezone.utc),
                )
                message = f"Участник ограничен на {minutes} мин."
            elif action == "unmute":
                await bot.restrict_chat_member(
                    chat_id,
                    user_id,
                    ChatPermissions(
                        can_send_messages=True,
                        can_send_audios=True,
                        can_send_documents=True,
                        can_send_photos=True,
                        can_send_videos=True,
                        can_send_video_notes=True,
                        can_send_voice_notes=True,
                        can_send_polls=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True,
                    ),
                )
                message = "Ограничения участника сняты."
            else:
                return error("Неизвестное действие админ-центра.")
        except Exception as exc:
            return error(str(exc), 400)

        await log_admin(int(admin.id), chat_id, user_id, action, message, data)
        return core.web.json_response({"ok": True, "message": message})

    async def index(_: Any):
        return core.web.FileResponse(
            ADMIN_DIR / "index.html",
            headers={"Cache-Control": "no-store", "X-Admin-Center": "reality-123"},
        )

    async def asset(request: Any):
        name = request.match_info["name"]
        if name not in {"admin.css", "admin.js"}:
            raise core.web.HTTPNotFound()
        return core.web.FileResponse(
            ADMIN_DIR / name,
            headers={"Cache-Control": "no-store", "X-Admin-Center": "reality-123"},
        )

    async def start_server_with_admin_v123(bot: Any):
        if not ADMIN_DIR.is_dir():
            raise RuntimeError(f"Не найдена папка админ-центра Reality 123: {ADMIN_DIR}")
        original_runner = core.web.AppRunner

        def runner_factory(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)

            def add_get(path: str, handler: Any) -> None:
                if ("GET", path) not in keys:
                    app.router.add_get(path, handler)
                    keys.add(("GET", path))

            def add_post(path: str, handler: Any) -> None:
                if ("POST", path) not in keys:
                    app.router.add_post(path, handler)
                    keys.add(("POST", path))

            add_get("/admin-v123", index)
            add_get("/admin-v123/", index)
            add_get("/admin-v123/{name:admin\\.css|admin\\.js}", asset)
            add_get("/admin-v123/api/state", state_api)
            add_get("/admin-v123/api/users", users_api)
            add_post("/admin-v123/api/action", action_api)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_server_with_admin_v123

    async def open_admin_v123(message: Message, bot: Any) -> None:
        if not message.from_user or int(message.from_user.id) != int(core.DEVELOPER_ID):
            return
        if not core.WEBAPP_PUBLIC_URL:
            await message.answer("⚠️ Для админ-центра укажи WEBAPP_PUBLIC_URL.")
            return
        parts = (message.text or "").split(maxsplit=1)
        query = parts[1].strip() if len(parts) == 2 else ""
        target = None
        chat_id = 0
        if core.is_group(message):
            chat_id = int(message.chat.id)
            replied = message.reply_to_message.from_user if message.reply_to_message else None
            if replied and not replied.is_bot:
                target = await core.db.upsert_player(chat_id, replied)
            elif query:
                target = await core.db.admin_find_player(query, chat_id)
            else:
                target = await core.db.upsert_player(chat_id, message.from_user)
        else:
            if query:
                target = await core.db.admin_find_player(query)
            if target is None:
                target = await core.db.admin_latest_group_player(message.from_user.id)
            if target is not None:
                chat_id = int(target.chat_id)
        if target is None or not chat_id:
            await message.answer("⚠️ Сначала открой <code>/admin</code> в нужной групповой беседе.")
            return
        url = (
            f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/admin-v123/"
            f"?chat_id={chat_id}&user_id={int(target.user_id)}&build=123-{int(time.time())}"
        )
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🛠 Открыть админ-центр Reality 123", web_app=WebAppInfo(url=url))]]
        )
        try:
            await bot.send_message(
                message.from_user.id,
                "🛠 <b>АДМИН-ЦЕНТР REALITY 123</b>\n\n"
                f"Беседа: <code>{chat_id}</code>\n"
                f"Участник: <b>{target.full_name}</b>\n\n"
                "Обычное и карьерное влияние управляются раздельно. Роль изменяется только карьерными очками.",
                reply_markup=markup,
            )
        except Exception:
            await message.answer("⚠️ Открой личку бота, нажми /start и повтори команду.")
            return
        if core.is_group(message):
            await core.ephemeral_reply(message, "🔒 Новый админ-центр отправлен в личные сообщения.", delay_seconds=3)

    core.open_admin_panel = open_admin_v123
