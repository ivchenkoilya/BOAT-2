from __future__ import annotations

import json
import logging
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiohttp import ClientSession, web

import game_center_v75 as games_base
import talent_system


LOGGER = logging.getLogger(__name__)
VERSION = "Reality 89 · Админ-центр Pro"
DEFAULT_ATTEMPTS = 3
MAX_ATTEMPTS = 2_000_000_000
ASSET_DIR = Path(__file__).resolve().parent / "adminapp_v89"
GAME_HELPER_PATH = Path(__file__).resolve().parent / "games" / "game-attempts-v89.js"


def _day_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _week_key() -> str:
    iso = datetime.now(timezone.utc).date().isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def install_admin_game_attempts_v89(core: Any) -> None:
    if getattr(core, "_admin_game_attempts_v89_installed", False):
        return
    core._admin_game_attempts_v89_installed = True
    core.ADMIN_CENTER_VERSION = VERSION

    original_connect = core.Database.connect

    async def connect_with_attempt_limits(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS game_attempt_limits_v89 (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    game_key TEXT NOT NULL,
                    date_key TEXT NOT NULL,
                    attempt_limit INTEGER NOT NULL DEFAULT 3,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (chat_id, user_id, game_key, date_key)
                );
                CREATE INDEX IF NOT EXISTS idx_game_attempt_limits_v89_owner
                ON game_attempt_limits_v89 (chat_id, user_id, date_key);
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_attempt_limits

    def auth(request: web.Request) -> tuple[Any | None, web.Response | None]:
        user, reason = core._webapp_auth(request)
        if user is None:
            return None, core.web.json_response(
                {"ok": False, "reason": reason or "Нет авторизации Telegram."},
                status=401,
            )
        if int(user.id) != int(core.DEVELOPER_ID):
            return None, core.web.json_response(
                {"ok": False, "reason": "Админ-центр доступен только владельцу бота."},
                status=403,
            )
        return user, None

    async def payload(request: web.Request) -> dict[str, Any]:
        try:
            value = await request.json()
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    async def table_exists(conn: Any, name: str) -> bool:
        cursor = await conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (name,),
        )
        return await cursor.fetchone() is not None

    async def attempt_limit(
        conn: Any,
        chat_id: int,
        user_id: int,
        game_key: str,
        day: str | None = None,
    ) -> tuple[int, bool]:
        cursor = await conn.execute(
            """
            SELECT attempt_limit FROM game_attempt_limits_v89
            WHERE chat_id=? AND user_id=? AND game_key=? AND date_key=?
            """,
            (chat_id, user_id, game_key, day or _day_key()),
        )
        row = await cursor.fetchone()
        if row is None:
            return DEFAULT_ATTEMPTS, False
        return max(0, int(row["attempt_limit"])), True

    async def player_auth(request: web.Request) -> tuple[Any, int, dict[str, Any]]:
        user, start_param = core._webapp_auth(request)
        if user is None:
            raise PermissionError(start_param or "Нет авторизации Telegram.")
        data = await payload(request)
        raw = str(start_param or "")
        if raw.startswith(games_base.GAME_PREFIX):
            raw = raw[len(games_base.GAME_PREFIX):]
        else:
            raw = str(data.get("chat_id") or request.query.get("chat_id") or "")
        try:
            chat_id = int(raw)
        except (TypeError, ValueError):
            raise ValueError("Не найдена беседа для начисления влияния.")
        if await core.db.get_player(chat_id, user.id) is None:
            raise PermissionError("Сначала открой игру из меню бота в нужной беседе.")
        return user, chat_id, data

    def player_error(error: Exception) -> web.Response:
        status = 403 if isinstance(error, PermissionError) else 400
        return core.web.json_response({"ok": False, "reason": str(error)}, status=status)

    async def daily_rows(chat_id: int, user_id: int) -> dict[str, dict[str, int]]:
        conn = core.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT game_key,attempts,best_score,best_base_reward,total_paid
            FROM game_daily_v75
            WHERE chat_id=? AND user_id=? AND date_key=?
            """,
            (chat_id, user_id, _day_key()),
        )
        return {
            str(row["game_key"]): {
                "attempts": int(row["attempts"]),
                "best_score": int(row["best_score"]),
                "best_base_reward": int(row["best_base_reward"]),
                "total_paid": int(row["total_paid"]),
            }
            for row in await cursor.fetchall()
        }

    async def player_state_api(request: web.Request) -> web.Response:
        try:
            user, chat_id, _ = await player_auth(request)
            player = await core.db.get_player(chat_id, user.id)
            rows = await daily_rows(chat_id, user.id)
            buffs = await talent_system.buffs_for(core.db, chat_id, user.id)
            conn = core.db._require_connection()
            result: dict[str, Any] = {}
            limits: list[int] = []
            for key, info in games_base.GAME_INFO.items():
                row = rows.get(key, {})
                used = max(0, int(row.get("attempts", 0)))
                limit, custom = await attempt_limit(conn, chat_id, user.id, key)
                limits.append(limit)
                result[key] = {
                    **info,
                    "attempts": used,
                    "attempt_limit": limit,
                    "attempts_left": max(0, limit - used),
                    "custom_attempts": custom,
                    "best_score": int(row.get("best_score", 0)),
                    "best_base_reward": int(row.get("best_base_reward", 0)),
                    "total_paid": int(row.get("total_paid", 0)),
                }
            common_limit = limits[0] if limits and all(x == limits[0] for x in limits) else DEFAULT_ATTEMPTS
            return core.web.json_response(
                {
                    "ok": True,
                    "version": VERSION,
                    "chat_id": chat_id,
                    "player": {
                        "user_id": int(user.id),
                        "name": user.full_name,
                        "points": int(player.points) if player else 0,
                    },
                    "games": result,
                    "attempts_per_day": common_limit,
                    "buffs": buffs,
                    "daily_rule": (
                        "Базовый лимит — 3 попытки на каждую игру. "
                        "Владелец бота может выдать персональный пакет любого размера. "
                        "Влияние по-прежнему начисляется только за улучшение лучшей награды дня."
                    ),
                }
            )
        except (PermissionError, ValueError) as error:
            return player_error(error)

    async def player_start_api(request: web.Request) -> web.Response:
        try:
            user, chat_id, data = await player_auth(request)
            game_key = str(data.get("game") or "")
            info = games_base.GAME_INFO.get(game_key)
            if info is None:
                raise ValueError("Неизвестная игра.")
            now = int(time.time())
            day = _day_key()
            session_id = secrets.token_urlsafe(18)
            seed = secrets.randbelow(2_000_000_000) + 1
            conn = core.db._require_connection()
            async with core.db.lock:
                await conn.execute(
                    """
                    INSERT OR IGNORE INTO game_daily_v75(
                        chat_id,user_id,game_key,date_key,attempts,updated_at
                    ) VALUES(?,?,?,?,0,?)
                    """,
                    (chat_id, user.id, game_key, day, now),
                )
                cursor = await conn.execute(
                    """
                    SELECT attempts FROM game_daily_v75
                    WHERE chat_id=? AND user_id=? AND game_key=? AND date_key=?
                    """,
                    (chat_id, user.id, game_key, day),
                )
                row = await cursor.fetchone()
                used = max(0, int(row["attempts"])) if row else 0
                limit, _ = await attempt_limit(conn, chat_id, user.id, game_key, day)
                if used >= limit:
                    await conn.commit()
                    raise ValueError(f"Все {limit} попыток этой игры на сегодня использованы.")
                await conn.execute(
                    """
                    UPDATE game_daily_v75 SET attempts=attempts+1,updated_at=?
                    WHERE chat_id=? AND user_id=? AND game_key=? AND date_key=?
                    """,
                    (now, chat_id, user.id, game_key, day),
                )
                await conn.execute(
                    """
                    UPDATE game_runs_v75 SET status='expired'
                    WHERE status='active' AND started_at<?
                    """,
                    (now - 600,),
                )
                await conn.execute(
                    """
                    INSERT INTO game_runs_v75(
                        session_id,chat_id,user_id,game_key,seed,status,started_at
                    ) VALUES(?,?,?,?,?,'active',?)
                    """,
                    (session_id, chat_id, user.id, game_key, seed, now),
                )
                await conn.commit()
            return core.web.json_response(
                {
                    "ok": True,
                    "session_id": session_id,
                    "seed": seed,
                    "game": game_key,
                    "duration": int(info["duration"]),
                    "attempt_limit": limit,
                    "attempts_left": max(0, limit - used - 1),
                }
            )
        except (PermissionError, ValueError) as error:
            return player_error(error)

    async def proxy_admin_state(request: web.Request, chat_id: int, user_id: int) -> dict[str, Any]:
        headers = {
            "X-Telegram-Init-Data": request.headers.get("X-Telegram-Init-Data", ""),
            "Content-Type": "application/json",
        }
        url = (
            f"http://127.0.0.1:{int(core.WEBAPP_PORT)}"
            f"/admin-v76/api/state?chat_id={chat_id}&user_id={user_id}"
        )
        async with ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.json(content_type=None)
                if response.status >= 400 or not data.get("ok"):
                    raise RuntimeError(data.get("reason") or "Админ-центр Reality 76 недоступен.")
                return data

    async def admin_state_api(request: web.Request) -> web.Response:
        _, problem = auth(request)
        if problem is not None:
            return problem
        chat_id = _as_int(request.query.get("chat_id"))
        user_id = _as_int(request.query.get("user_id"))
        try:
            data = await proxy_admin_state(request, chat_id, user_id)
        except Exception as exc:
            LOGGER.exception("Не удалось получить состояние старого админ-центра")
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=502)

        data["version"] = VERSION
        target = data.get("target") or {}
        selected_chat = _as_int((data.get("selected_chat") or {}).get("chat_id"))
        selected_user = _as_int(target.get("user_id"))
        conn = core.db._require_connection()

        if selected_chat and selected_user and (data.get("games") or {}).get("available"):
            limits: list[int] = []
            game_rows = (data.get("games") or {}).get("games") or {}
            for key, game in game_rows.items():
                limit, custom = await attempt_limit(conn, selected_chat, selected_user, str(key))
                used = max(0, _as_int(game.get("attempts")))
                game["attempt_limit"] = limit
                game["attempts_left"] = max(0, limit - used)
                game["custom_attempts"] = custom
                limits.append(limit)
            if limits and all(value == limits[0] for value in limits):
                data["games"]["attempts_per_day"] = limits[0]
            data["games"]["max_attempts"] = MAX_ATTEMPTS

        sources: dict[str, int] = {
            "career": 0,
            "entitled": 0,
            "game_wins": 0,
            "tasks": 0,
            "boss_wins": 0,
            "game_career_week": 0,
            "task_points_week": 0,
            "activity_points_week": 0,
            "achievement_points": 0,
        }
        if selected_chat and selected_user and await table_exists(conn, "knowledge_economy_v85"):
            cursor = await conn.execute(
                """
                SELECT career,entitled,game_wins,tasks,boss_wins
                FROM knowledge_economy_v85 WHERE chat_id=? AND user_id=?
                """,
                (selected_chat, selected_user),
            )
            row = await cursor.fetchone()
            if row:
                for key in ("career", "entitled", "game_wins", "tasks", "boss_wins"):
                    sources[key] = int(row[key] or 0)
        if selected_chat and selected_user and await table_exists(conn, "knowledge_week_v85"):
            cursor = await conn.execute(
                """
                SELECT game_career,task_points,activity_points
                FROM knowledge_week_v85
                WHERE chat_id=? AND user_id=? AND week_key=?
                """,
                (selected_chat, selected_user, _week_key()),
            )
            row = await cursor.fetchone()
            if row:
                sources["game_career_week"] = int(row["game_career"] or 0)
                sources["task_points_week"] = int(row["task_points"] or 0)
                sources["activity_points_week"] = int(row["activity_points"] or 0)
        if selected_chat and selected_user and await table_exists(conn, "knowledge_achievements_v85"):
            cursor = await conn.execute(
                """
                SELECT COALESCE(SUM(points),0) amount
                FROM knowledge_achievements_v85 WHERE chat_id=? AND user_id=?
                """,
                (selected_chat, selected_user),
            )
            row = await cursor.fetchone()
            sources["achievement_points"] = int(row["amount"] or 0) if row else 0
        if data.get("knowledge") is not None:
            data["knowledge"]["sources_v89"] = sources
        data["economy_v89"] = sources
        return core.web.json_response(data)

    async def log_action(
        admin_id: int,
        chat_id: int,
        user_id: int,
        detail: str,
        payload_data: dict[str, Any],
    ) -> None:
        conn = core.db._require_connection()
        if not await table_exists(conn, "admin_action_log_v62"):
            return
        async with core.db.lock:
            await conn.execute(
                """
                INSERT INTO admin_action_log_v62(
                    admin_id,chat_id,target_user_id,action,detail,
                    payload_json,reversible,created_at
                ) VALUES(?,?,?,?,?,?,0,?)
                """,
                (
                    admin_id,
                    chat_id,
                    user_id,
                    "game_attempts_set",
                    detail,
                    json.dumps(payload_data, ensure_ascii=False, separators=(",", ":")),
                    int(time.time()),
                ),
            )
            await conn.commit()

    async def admin_action_api(request: web.Request) -> web.Response:
        admin, problem = auth(request)
        if problem is not None:
            return problem
        data = await payload(request)
        action = str(data.get("action") or "")
        if action != "game_attempts_set":
            return core.web.json_response(
                {"ok": False, "reason": "Неизвестное действие Reality 89."},
                status=400,
            )
        chat_id = _as_int(data.get("chat_id"))
        user_id = _as_int(data.get("user_id"))
        requested_game = str(data.get("game") or "all")
        value = _as_int(data.get("value"), DEFAULT_ATTEMPTS)
        if not chat_id or not user_id:
            return core.web.json_response(
                {"ok": False, "reason": "Сначала выбери беседу и участника."},
                status=400,
            )
        if value < 0 or value > MAX_ATTEMPTS:
            return core.web.json_response(
                {
                    "ok": False,
                    "reason": f"Количество должно быть от 0 до {MAX_ATTEMPTS}.",
                },
                status=400,
            )
        if requested_game == "all":
            game_keys = list(games_base.GAME_INFO)
        elif requested_game in games_base.GAME_INFO:
            game_keys = [requested_game]
        else:
            return core.web.json_response(
                {"ok": False, "reason": "Неизвестная игра."},
                status=400,
            )

        now = int(time.time())
        day = _day_key()
        conn = core.db._require_connection()
        async with core.db.lock:
            for game_key in game_keys:
                await conn.execute(
                    """
                    INSERT OR IGNORE INTO game_daily_v75(
                        chat_id,user_id,game_key,date_key,attempts,
                        best_score,best_base_reward,total_paid,updated_at
                    ) VALUES(?,?,?,?,0,0,0,0,?)
                    """,
                    (chat_id, user_id, game_key, day, now),
                )
                await conn.execute(
                    """
                    UPDATE game_daily_v75 SET attempts=0,updated_at=?
                    WHERE chat_id=? AND user_id=? AND game_key=? AND date_key=?
                    """,
                    (now, chat_id, user_id, game_key, day),
                )
                await conn.execute(
                    """
                    INSERT INTO game_attempt_limits_v89(
                        chat_id,user_id,game_key,date_key,attempt_limit,updated_at
                    ) VALUES(?,?,?,?,?,?)
                    ON CONFLICT(chat_id,user_id,game_key,date_key) DO UPDATE SET
                        attempt_limit=excluded.attempt_limit,
                        updated_at=excluded.updated_at
                    """,
                    (chat_id, user_id, game_key, day, value, now),
                )
            await conn.commit()

        scope = "обе игры" if requested_game == "all" else str(
            games_base.GAME_INFO[requested_game]["title"]
        )
        detail = (
            f"Игроку выдан новый пакет: {value}/{value} попыток, {scope}. "
            "Использованные попытки сброшены; рекорды и выплаты сохранены."
        )
        await log_action(
            int(admin.id),
            chat_id,
            user_id,
            detail,
            {"game": requested_game, "value": value, "date_key": day},
        )
        return core.web.json_response({"ok": True, "message": detail})

    def asset_response(path: Path, marker: str) -> web.FileResponse:
        return core.web.FileResponse(
            path,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Reality-Upgrade": marker,
            },
        )

    async def admin_script(_: web.Request) -> web.StreamResponse:
        return asset_response(ASSET_DIR / "admin-v89.js", "admin-v89")

    async def game_script(_: web.Request) -> web.StreamResponse:
        return asset_response(GAME_HELPER_PATH, "game-attempts-v89")

    original_start_server = core.start_webapp_server

    async def start_server_v89(bot: Any):
        previous_application = core.web.Application

        def application_factory(*args: Any, **kwargs: Any):
            app = previous_application(*args, **kwargs)
            app.router.add_get("/admin-v89/admin-v89.js", admin_script)
            app.router.add_get("/games/game-attempts-v89.js", game_script)
            app.router.add_get("/admin-v89/api/state", admin_state_api)
            app.router.add_post("/admin-v89/api/action", admin_action_api)
            app.router.add_post("/games-v89/api/state", player_state_api)
            app.router.add_post("/games-v89/api/start", player_start_api)
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = previous_application

    core.start_webapp_server = start_server_v89
