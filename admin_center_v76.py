from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from aiohttp import ClientSession
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, User, WebAppInfo

LOGGER = logging.getLogger(__name__)
ADMIN_V76_DIR = Path(__file__).resolve().parent / "adminapp_v76"
ADMIN_VERSION = "Reality 76 · Админ-центр"
GAME_ACTIONS = {
    "game_attempts_reset",
    "game_attempts_reset_chat",
    "game_sessions_close",
    "game_clear_stuck_chat",
    "game_run_void",
}


def install_admin_center_v76(core: Any) -> None:
    if getattr(core, "_admin_center_v76_installed", False):
        return
    core._admin_center_v76_installed = True
    core.ADMIN_CENTER_VERSION = ADMIN_VERSION
    original_start_server = core.start_webapp_server

    def error(reason: str, status: int = 400):
        return core.web.json_response({"ok": False, "reason": reason}, status=status)

    def auth(request: Any) -> tuple[User | None, Any | None]:
        user, reason = core._webapp_auth(request)
        if user is None:
            return None, error(reason or "Нет авторизации Telegram.", 401)
        if int(user.id) != int(core.DEVELOPER_ID):
            return None, error("Админ-центр доступен только владельцу бота.", 403)
        return user, None

    async def payload(request: Any) -> dict[str, Any]:
        try:
            value = await request.json()
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    def as_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    async def table_exists(conn: Any, name: str) -> bool:
        cursor = await conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (name,),
        )
        return await cursor.fetchone() is not None

    def role(points: int) -> dict[str, Any]:
        value = int(points)
        limits = {
            "decoration": 0,
            "dust": int(getattr(core, "DUST_MIN_POINTS", 1000)),
            "extras": int(getattr(core, "EXTRAS_MIN_POINTS", 3000)),
            "secondary": int(getattr(core, "SECONDARY_MIN_POINTS", 6000)),
            "hero": int(getattr(core, "HERO_MIN_POINTS", 10000)),
        }
        if value < limits["dust"]:
            key, emoji, title = "decoration", "🪑", "Декорация"
        elif value < limits["extras"]:
            key, emoji, title = "dust", "🌫", "Пыль"
        elif value < limits["secondary"]:
            key, emoji, title = "extras", "👥", "Массовка"
        elif value < limits["hero"]:
            key, emoji, title = "secondary", "🎭", "Второстепенная роль"
        else:
            key, emoji, title = "hero", "👑", "Главный герой"
        return {
            "key": key,
            "emoji": emoji,
            "title": title,
            "floor": limits[key],
            "thresholds": limits,
        }

    def day_bounds() -> tuple[int, int]:
        now = datetime.now(timezone.utc)
        start = int(datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp())
        return start, start + 86400

    async def proxy_json(request: Any, path: str) -> dict[str, Any]:
        headers = {
            "X-Telegram-Init-Data": request.headers.get("X-Telegram-Init-Data", ""),
            "Content-Type": "application/json",
        }
        url = f"http://127.0.0.1:{int(core.WEBAPP_PORT)}{path}"
        async with ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.json(content_type=None)
                if response.status >= 400 or not data.get("ok"):
                    raise RuntimeError(data.get("reason") or "Старый API админ-центра недоступен.")
                return data

    async def games_state(chat_id: int, user_id: int) -> dict[str, Any]:
        try:
            import game_center_v75 as base
        except Exception:
            return {"available": False, "reason": "Игровой модуль не загружен."}
        conn = core.db._require_connection()
        if not await table_exists(conn, "game_daily_v75") or not await table_exists(conn, "game_runs_v75"):
            return {"available": False, "reason": "Таблицы игрового центра не созданы."}

        cursor = await conn.execute(
            """SELECT game_key,attempts,best_score,best_base_reward,total_paid
               FROM game_daily_v75 WHERE chat_id=? AND user_id=? AND date_key=?""",
            (chat_id, user_id, base._date_key()),
        )
        daily = {str(row["game_key"]): row for row in await cursor.fetchall()}
        games: dict[str, Any] = {}
        for key, info in base.GAME_INFO.items():
            row = daily.get(key)
            attempts = int(row["attempts"]) if row else 0
            games[key] = {
                **dict(info),
                "key": key,
                "attempts": attempts,
                "attempts_left": max(0, int(base.GAME_ATTEMPTS_PER_DAY) - attempts),
                "best_score": int(row["best_score"]) if row else 0,
                "best_base_reward": int(row["best_base_reward"]) if row else 0,
                "total_paid": int(row["total_paid"]) if row else 0,
            }

        cursor = await conn.execute(
            """SELECT session_id,game_key,status,started_at,finished_at,score,
                      base_reward,actual_reward,meta_json
               FROM game_runs_v75 WHERE chat_id=? AND user_id=?
               ORDER BY started_at DESC LIMIT 30""",
            (chat_id, user_id),
        )
        runs = []
        for row in await cursor.fetchall():
            try:
                meta = json.loads(str(row["meta_json"] or "{}"))
                meta = meta if isinstance(meta, dict) else {}
            except Exception:
                meta = {}
            runs.append(
                {
                    "session_id": str(row["session_id"]),
                    "game_key": str(row["game_key"]),
                    "status": str(row["status"]),
                    "started_at": int(row["started_at"]),
                    "finished_at": int(row["finished_at"] or 0),
                    "score": int(row["score"]),
                    "base_reward": int(row["base_reward"]),
                    "actual_reward": int(row["actual_reward"]),
                    "meta": meta,
                }
            )

        start, end = day_bounds()
        cursor = await conn.execute(
            """SELECT COUNT(*) runs_today,
                      SUM(CASE WHEN status='finished' THEN 1 ELSE 0 END) finished_today,
                      SUM(CASE WHEN status='expired' THEN 1 ELSE 0 END) expired_today,
                      SUM(CASE WHEN status='voided' THEN 1 ELSE 0 END) voided_today,
                      SUM(CASE WHEN status='finished' THEN actual_reward ELSE 0 END) paid_today
               FROM game_runs_v75 WHERE chat_id=? AND started_at>=? AND started_at<?""",
            (chat_id, start, end),
        )
        totals = await cursor.fetchone()
        now = int(time.time())
        cursor = await conn.execute(
            """SELECT SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) active,
                      SUM(CASE WHEN status='resolving' THEN 1 ELSE 0 END) resolving,
                      SUM(CASE WHEN status IN ('active','resolving') AND started_at<? THEN 1 ELSE 0 END) stuck
               FROM game_runs_v75 WHERE chat_id=?""",
            (now - 300, chat_id),
        )
        live = await cursor.fetchone()
        value = lambda row, key: int(row[key] or 0) if row else 0
        return {
            "available": True,
            "attempts_per_day": int(base.GAME_ATTEMPTS_PER_DAY),
            "games": games,
            "runs": runs,
            "chat": {
                "runs_today": value(totals, "runs_today"),
                "finished_today": value(totals, "finished_today"),
                "expired_today": value(totals, "expired_today"),
                "voided_today": value(totals, "voided_today"),
                "paid_today": value(totals, "paid_today"),
                "active": value(live, "active"),
                "resolving": value(live, "resolving"),
                "stuck": value(live, "stuck"),
            },
            "player_url": base._game_link(core, chat_id),
        }

    async def state_api(request: Any):
        admin, problem = auth(request)
        if problem is not None:
            return problem
        chat_id = as_int(request.query.get("chat_id"))
        requested_user = as_int(request.query.get("user_id"))
        try:
            data = await proxy_json(
                request,
                f"/admin-app/api/state?chat_id={chat_id}&user_id={requested_user}",
            )
        except Exception as exc:
            LOGGER.exception("Не удалось получить базовое состояние админ-центра")
            return error(str(exc), 502)

        selected_chat = as_int(data.get("selected_chat", {}).get("chat_id"))
        target = data.get("target")
        target_error = None
        if requested_user and as_int((target or {}).get("user_id")) != requested_user:
            target = None
            data["behavior"] = {}
            data["knowledge"] = None
            target_error = "Участник не найден в выбранной беседе."
        if target:
            target["role"] = role(as_int(target.get("points")))
        for item in data.get("quick_users") or []:
            item["role"] = role(as_int(item.get("points")))
        if data.get("knowledge"):
            try:
                from raid_v64_direct_tree import WEEKLY_TREE_POINT_CAP
                data["knowledge"]["weekly_cap"] = int(WEEKLY_TREE_POINT_CAP)
            except Exception:
                data["knowledge"]["weekly_cap"] = 12

        health = data.get("health") or {}
        start, end = day_bounds()
        conn = core.db._require_connection()
        if await table_exists(conn, "score_log"):
            cursor = await conn.execute(
                """SELECT COALESCE(SUM(CASE WHEN delta>0 THEN delta ELSE 0 END),0) amount
                   FROM score_log WHERE created_at>=? AND created_at<?""",
                (start, end),
            )
            row = await cursor.fetchone()
            health["influence_today"] = int(row["amount"] or 0) if row else 0
        data.update(
            {
                "version": ADMIN_VERSION,
                "bot_version": str(getattr(core, "BOT_VERSION", "Reality 76")),
                "admin": {"user_id": int(admin.id), "name": admin.full_name},
                "requested_user_id": requested_user,
                "target": target,
                "target_error": target_error,
                "health": health,
                "role_thresholds": role(0)["thresholds"],
                "games": await games_state(selected_chat, as_int((target or {}).get("user_id")))
                if target
                else {"available": False, "reason": "Участник не выбран."},
            }
        )
        return core.web.json_response(data)

    async def users_api(request: Any):
        _, problem = auth(request)
        if problem is not None:
            return problem
        chat_id = as_int(request.query.get("chat_id"))
        query = str(request.query.get("q") or "")
        try:
            data = await proxy_json(
                request,
                f"/admin-app/api/users?chat_id={chat_id}&q={quote(query)}",
            )
        except Exception as exc:
            return error(str(exc), 502)
        for item in data.get("users") or []:
            item["role"] = role(as_int(item.get("points")))
        return core.web.json_response(data)

    async def log_action(admin_id: int, chat_id: int, target: int | None, action: str, detail: str) -> None:
        conn = core.db._require_connection()
        if not await table_exists(conn, "admin_action_log_v62"):
            return
        async with core.db.lock:
            await conn.execute(
                """INSERT INTO admin_action_log_v62
                   (admin_id,chat_id,target_user_id,action,detail,payload_json,reversible,created_at)
                   VALUES (?,?,?,?,?,'{}',0,?)""",
                (admin_id, chat_id, target, action, detail, int(time.time())),
            )
            await conn.commit()

    async def rebuild_daily(conn: Any, chat_id: int, user_id: int, game_key: str) -> None:
        import game_center_v75 as base
        start, end = day_bounds()
        cursor = await conn.execute(
            """SELECT COUNT(*) attempts,
                      COALESCE(MAX(CASE WHEN status='finished' THEN score ELSE 0 END),0) best_score,
                      COALESCE(SUM(CASE WHEN status='finished' THEN actual_reward ELSE 0 END),0) total_paid
               FROM game_runs_v75 WHERE chat_id=? AND user_id=? AND game_key=?
               AND started_at>=? AND started_at<?""",
            (chat_id, user_id, game_key, start, end),
        )
        row = await cursor.fetchone()
        attempts = min(int(base.GAME_ATTEMPTS_PER_DAY), int(row["attempts"] or 0))
        best_score = int(row["best_score"] or 0)
        await conn.execute(
            """INSERT INTO game_daily_v75
               (chat_id,user_id,game_key,date_key,attempts,best_score,best_base_reward,total_paid,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(chat_id,user_id,game_key,date_key) DO UPDATE SET
               attempts=excluded.attempts,best_score=excluded.best_score,
               best_base_reward=excluded.best_base_reward,total_paid=excluded.total_paid,
               updated_at=excluded.updated_at""",
            (
                chat_id, user_id, game_key, base._date_key(), attempts, best_score,
                int(base._base_reward(game_key, best_score)), int(row["total_paid"] or 0), int(time.time()),
            ),
        )

    async def game_action_api(request: Any):
        admin, problem = auth(request)
        if problem is not None:
            return problem
        data = await payload(request)
        action = str(data.get("action") or "")
        if action not in GAME_ACTIONS:
            return error("Неизвестное действие игрового центра.")
        chat_id, user_id = as_int(data.get("chat_id")), as_int(data.get("user_id"))
        game_key, session_id = str(data.get("game") or ""), str(data.get("session_id") or "")
        if not chat_id:
            return error("Не выбрана беседа.")
        conn = core.db._require_connection()
        if not await table_exists(conn, "game_runs_v75"):
            return error("Игровой центр ещё не создавал таблицы.", 404)
        message = "Готово."

        if action == "game_attempts_reset":
            if not user_id:
                return error("Не выбран участник.")
            import game_center_v75 as base
            sql = "DELETE FROM game_daily_v75 WHERE chat_id=? AND user_id=? AND date_key=?"
            args: list[Any] = [chat_id, user_id, base._date_key()]
            if game_key:
                sql += " AND game_key=?"
                args.append(game_key)
            async with core.db.lock:
                cursor = await conn.execute(sql, tuple(args)); await conn.commit()
            changed = max(0, int(cursor.rowcount or 0))
            message = f"Дневные попытки сброшены. Записей очищено: {changed}."
            await log_action(admin.id, chat_id, user_id, action, message)

        elif action == "game_attempts_reset_chat":
            import game_center_v75 as base
            async with core.db.lock:
                cursor = await conn.execute(
                    "DELETE FROM game_daily_v75 WHERE chat_id=? AND date_key=?",
                    (chat_id, base._date_key()),
                ); await conn.commit()
            changed = max(0, int(cursor.rowcount or 0))
            message = f"Попытки всей беседы сброшены. Записей: {changed}."
            await log_action(admin.id, chat_id, None, action, message)

        elif action == "game_sessions_close":
            if not user_id:
                return error("Не выбран участник.")
            sql = """UPDATE game_runs_v75 SET status='expired',finished_at=?
                     WHERE chat_id=? AND user_id=? AND status IN ('active','resolving')"""
            args = [int(time.time()), chat_id, user_id]
            if game_key:
                sql += " AND game_key=?"; args.append(game_key)
            async with core.db.lock:
                cursor = await conn.execute(sql, tuple(args)); await conn.commit()
            changed = max(0, int(cursor.rowcount or 0))
            message = f"Закрыто активных игровых сессий: {changed}."
            await log_action(admin.id, chat_id, user_id, action, message)

        elif action == "game_clear_stuck_chat":
            now = int(time.time())
            async with core.db.lock:
                cursor = await conn.execute(
                    """UPDATE game_runs_v75 SET status='expired',finished_at=?
                       WHERE chat_id=? AND status IN ('active','resolving') AND started_at<?""",
                    (now, chat_id, now - 300),
                ); await conn.commit()
            changed = max(0, int(cursor.rowcount or 0))
            message = f"Закрыто зависших игровых сессий: {changed}."
            await log_action(admin.id, chat_id, None, action, message)

        elif action == "game_run_void":
            if not user_id or not session_id:
                return error("Не выбрана игровая сессия.")
            cursor = await conn.execute(
                "SELECT * FROM game_runs_v75 WHERE session_id=? AND chat_id=? AND user_id=? LIMIT 1",
                (session_id, chat_id, user_id),
            )
            run = await cursor.fetchone()
            if run is None:
                return error("Игровая сессия не найдена.", 404)
            if str(run["status"]) != "finished":
                return error("Можно аннулировать только завершённый результат.")
            reward = max(0, int(run["actual_reward"] or 0))
            player = await core.db.get_player(chat_id, user_id)
            if player is None:
                return error("Участник не найден.", 404)
            await core.db.set_player_points(chat_id, user_id, int(player.points) - reward, "admin_game_void_v76")
            async with core.db.lock:
                await conn.execute(
                    "UPDATE game_runs_v75 SET status='voided',actual_reward=0 WHERE session_id=?",
                    (session_id,),
                )
                await rebuild_daily(conn, chat_id, user_id, str(run["game_key"])); await conn.commit()
            message = f"Результат аннулирован. Списано влияния: {reward}."
            await log_action(admin.id, chat_id, user_id, action, message)
        return core.web.json_response({"ok": True, "message": message})

    async def index(_: Any):
        return core.web.FileResponse(
            ADMIN_V76_DIR / "index.html",
            headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "X-Admin-Center": "reality-76"},
        )

    async def asset(request: Any):
        name = request.match_info["name"]
        if name not in {"admin.css", "admin.js"}:
            raise core.web.HTTPNotFound()
        return core.web.FileResponse(
            ADMIN_V76_DIR / name,
            headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "X-Admin-Center": "reality-76"},
        )

    async def start_server(bot: Any):
        if not ADMIN_V76_DIR.is_dir():
            raise RuntimeError(f"Не найдена папка нового админ-центра: {ADMIN_V76_DIR}")
        previous = core.web.Application
        def factory(*args: Any, **kwargs: Any):
            app = previous(*args, **kwargs)
            app.router.add_get("/admin-v76", index); app.router.add_get("/admin-v76/", index)
            app.router.add_get("/admin-v76/{name:admin\\.css|admin\\.js}", asset)
            app.router.add_get("/admin-v76/api/state", state_api)
            app.router.add_get("/admin-v76/api/users", users_api)
            app.router.add_post("/admin-v76/api/action", game_action_api)
            return app
        core.web.Application = factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = previous
    core.start_webapp_server = start_server

    async def open_admin(message: Message, bot: Any) -> None:
        if not message.from_user or int(message.from_user.id) != int(core.DEVELOPER_ID):
            return
        if not core.WEBAPP_PUBLIC_URL:
            await message.answer("⚠️ Для админ-центра укажи WEBAPP_PUBLIC_URL."); return
        parts = (message.text or "").split(maxsplit=1); query = parts[1].strip() if len(parts) == 2 else ""
        target, chat_id = None, 0
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
            await message.answer("⚠️ Сначала открой <code>/admin</code> в нужной групповой беседе."); return
        url = f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/admin-v76/?chat_id={chat_id}&user_id={int(target.user_id)}&v=76"
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠 Открыть админ-центр Reality 76", web_app=WebAppInfo(url=url))]])
        try:
            await bot.send_message(
                message.from_user.id,
                "🛠 <b>АДМИН-ЦЕНТР REALITY 76</b>\n\n"
                f"Беседа: <code>{chat_id}</code>\nУчастник: <b>{target.full_name}</b>\n\n"
                "Исправлен выбор участников, обновлены роли и добавлено управление играми.",
                reply_markup=markup,
            )
        except Exception:
            await message.answer("⚠️ Открой личку бота, нажми /start и повтори команду."); return
        if core.is_group(message):
            await core.ephemeral_reply(message, "🔒 Новый админ-центр отправлен в личные сообщения.", delay_seconds=3)
    core.open_admin_panel = open_admin
