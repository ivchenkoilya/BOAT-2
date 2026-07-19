from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from aiohttp import ClientSession, web


VERSION = "Reality 92 · Админ-центр Pro"
DEFAULT_ATTEMPTS = 3
MAX_ATTEMPTS = 2_000_000_000
SCRIPT_PATH = Path(__file__).resolve().parent / "adminapp_v89" / "admin-v89.js"


def _day_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def install_admin_attempts_hotfix_v92(core: Any) -> None:
    """Ставит middleware до всех Mini App и использует только стабильные маршруты."""
    if getattr(core, "_admin_attempts_hotfix_v92_installed", False):
        return
    core._admin_attempts_hotfix_v92_installed = True
    core.ADMIN_CENTER_VERSION = VERSION

    original_connect = core.Database.connect

    async def connect_with_attempt_packages(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS game_attempt_limits_v92 (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    game_key TEXT NOT NULL,
                    date_key TEXT NOT NULL,
                    attempt_limit INTEGER NOT NULL DEFAULT 3,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (chat_id,user_id,game_key,date_key)
                );
                CREATE INDEX IF NOT EXISTS idx_game_attempt_limits_v92_owner
                ON game_attempt_limits_v92(chat_id,user_id,date_key);
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_attempt_packages

    async def _table_exists(conn: Any, name: str) -> bool:
        cursor = await conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (name,),
        )
        return await cursor.fetchone() is not None

    async def _limits(chat_id: int, user_id: int) -> dict[str, int]:
        if not chat_id or not user_id:
            return {}
        conn = core.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT game_key,attempt_limit FROM game_attempt_limits_v92
            WHERE chat_id=? AND user_id=? AND date_key=?
            """,
            (chat_id, user_id, _day_key()),
        )
        return {
            str(row["game_key"]): max(0, int(row["attempt_limit"]))
            for row in await cursor.fetchall()
        }

    async def _augment_games(data: dict[str, Any], admin: bool) -> dict[str, Any]:
        if admin:
            chat_id = _as_int((data.get("selected_chat") or {}).get("chat_id"))
            user_id = _as_int((data.get("target") or {}).get("user_id"))
        else:
            chat_id = _as_int(data.get("chat_id"))
            user_id = _as_int((data.get("player") or {}).get("user_id"))
        limits = await _limits(chat_id, user_id)
        container = data.get("games") or {}
        games = container.get("games") if admin else container
        if not isinstance(games, dict):
            return data
        totals: list[int] = []
        for key, game in games.items():
            if not isinstance(game, dict):
                continue
            limit = limits.get(str(key), DEFAULT_ATTEMPTS)
            remaining = max(0, _as_int(game.get("attempts_left")))
            game["attempt_limit"] = limit
            game["attempts_left"] = remaining
            game["attempts"] = max(0, limit - remaining)
            game["custom_attempts"] = str(key) in limits
            totals.append(limit)
        if admin:
            if totals and all(value == totals[0] for value in totals):
                container["attempts_per_day"] = totals[0]
            container["max_attempts"] = MAX_ATTEMPTS
            data["version"] = VERSION
        else:
            if totals and all(value == totals[0] for value in totals):
                data["attempts_per_day"] = totals[0]
            data["version"] = VERSION
            data["daily_rule"] = (
                "Базово доступно 3 попытки на каждую игру. Владелец может выдать "
                "персональный пакет любого размера; рекорды и награды при этом сохраняются."
            )
        return data

    async def _augment_knowledge(data: dict[str, Any]) -> None:
        chat_id = _as_int((data.get("selected_chat") or {}).get("chat_id"))
        user_id = _as_int((data.get("target") or {}).get("user_id"))
        if not chat_id or not user_id or data.get("knowledge") is None:
            return
        conn = core.db._require_connection()
        sources = {
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
        if await _table_exists(conn, "knowledge_economy_v85"):
            cursor = await conn.execute(
                "SELECT career,entitled,game_wins,tasks,boss_wins FROM knowledge_economy_v85 WHERE chat_id=? AND user_id=?",
                (chat_id, user_id),
            )
            row = await cursor.fetchone()
            if row:
                for key in ("career", "entitled", "game_wins", "tasks", "boss_wins"):
                    sources[key] = int(row[key] or 0)
        iso = datetime.now(timezone.utc).date().isocalendar()
        week_key = f"{iso.year}-W{iso.week:02d}"
        if await _table_exists(conn, "knowledge_week_v85"):
            cursor = await conn.execute(
                "SELECT game_career,task_points,activity_points FROM knowledge_week_v85 WHERE chat_id=? AND user_id=? AND week_key=?",
                (chat_id, user_id, week_key),
            )
            row = await cursor.fetchone()
            if row:
                sources["game_career_week"] = int(row["game_career"] or 0)
                sources["task_points_week"] = int(row["task_points"] or 0)
                sources["activity_points_week"] = int(row["activity_points"] or 0)
        if await _table_exists(conn, "knowledge_achievements_v85"):
            cursor = await conn.execute(
                "SELECT COALESCE(SUM(points),0) amount FROM knowledge_achievements_v85 WHERE chat_id=? AND user_id=?",
                (chat_id, user_id),
            )
            row = await cursor.fetchone()
            sources["achievement_points"] = int(row["amount"] or 0) if row else 0
        data["knowledge"]["sources_v89"] = sources
        data["economy_v89"] = sources

    async def _json_from_response(response: web.StreamResponse) -> dict[str, Any] | None:
        if not isinstance(response, web.Response) or response.body is None:
            return None
        try:
            value = json.loads(response.body.decode("utf-8"))
            return value if isinstance(value, dict) else None
        except Exception:
            return None

    async def _set_attempts(request: web.Request) -> web.Response:
        user, reason = core._webapp_auth(request)
        if user is None:
            return core.web.json_response(
                {"ok": False, "reason": reason or "Нет авторизации Telegram."}, status=401
            )
        if int(user.id) != int(core.DEVELOPER_ID):
            return core.web.json_response(
                {"ok": False, "reason": "Админ-центр доступен только владельцу бота."}, status=403
            )
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        chat_id = _as_int(payload.get("chat_id"))
        user_id = _as_int(payload.get("user_id"))
        value = _as_int(payload.get("value"), DEFAULT_ATTEMPTS)
        requested_game = str(payload.get("game") or "all")
        if not chat_id or not user_id:
            return core.web.json_response(
                {"ok": False, "reason": "Сначала выбери беседу и участника."}, status=400
            )
        if value < 0 or value > MAX_ATTEMPTS:
            return core.web.json_response(
                {"ok": False, "reason": f"Количество должно быть от 0 до {MAX_ATTEMPTS}."}, status=400
            )
        import game_center_v75 as games_base

        if requested_game == "all":
            game_keys = list(games_base.GAME_INFO)
        elif requested_game in games_base.GAME_INFO:
            game_keys = [requested_game]
        else:
            return core.web.json_response(
                {"ok": False, "reason": "Неизвестная игра."}, status=400
            )
        now = int(time.time())
        day = _day_key()
        # Старый игровой API блокирует запуск при attempts >= 3. Отрицательный
        # счётчик здесь является безопасным кредитом попыток: 3 - 1000 = -997.
        stored_attempts = int(games_base.GAME_ATTEMPTS_PER_DAY) - value
        conn = core.db._require_connection()
        async with core.db.lock:
            for game_key in game_keys:
                await conn.execute(
                    """
                    INSERT INTO game_daily_v75(
                        chat_id,user_id,game_key,date_key,attempts,
                        best_score,best_base_reward,total_paid,updated_at
                    ) VALUES(?,?,?,?,?,0,0,0,?)
                    ON CONFLICT(chat_id,user_id,game_key,date_key) DO UPDATE SET
                        attempts=excluded.attempts,updated_at=excluded.updated_at
                    """,
                    (chat_id, user_id, game_key, day, stored_attempts, now),
                )
                await conn.execute(
                    """
                    INSERT INTO game_attempt_limits_v92(
                        chat_id,user_id,game_key,date_key,attempt_limit,updated_at
                    ) VALUES(?,?,?,?,?,?)
                    ON CONFLICT(chat_id,user_id,game_key,date_key) DO UPDATE SET
                        attempt_limit=excluded.attempt_limit,updated_at=excluded.updated_at
                    """,
                    (chat_id, user_id, game_key, day, value, now),
                )
            if await _table_exists(conn, "admin_action_log_v62"):
                scope = "обе игры" if requested_game == "all" else str(games_base.GAME_INFO[requested_game]["title"])
                detail = f"Выдан персональный пакет {value}/{value}: {scope}. Рекорды и выплаты сохранены."
                await conn.execute(
                    """
                    INSERT INTO admin_action_log_v62(
                        admin_id,chat_id,target_user_id,action,detail,payload_json,reversible,created_at
                    ) VALUES(?,?,?,?,?,?,0,?)
                    """,
                    (
                        int(user.id), chat_id, user_id, "game_attempts_set", detail,
                        json.dumps({"game": requested_game, "value": value}, ensure_ascii=False), now,
                    ),
                )
            await conn.commit()
        return core.web.json_response(
            {
                "ok": True,
                "message": f"Игроку выдано {value}/{value} попыток. Рекорды и влияние сохранены.",
            }
        )

    async def _clear_custom_after_reset(request: web.Request, payload: dict[str, Any]) -> None:
        action = str(payload.get("action") or "")
        if action not in {"game_attempts_reset", "game_attempts_reset_chat"}:
            return
        chat_id = _as_int(payload.get("chat_id"))
        user_id = _as_int(payload.get("user_id"))
        game_key = str(payload.get("game") or "")
        if not chat_id:
            return
        conn = core.db._require_connection()
        sql = "DELETE FROM game_attempt_limits_v92 WHERE chat_id=? AND date_key=?"
        args: list[Any] = [chat_id, _day_key()]
        if action == "game_attempts_reset" and user_id:
            sql += " AND user_id=?"
            args.append(user_id)
        if game_key:
            sql += " AND game_key=?"
            args.append(game_key)
        async with core.db.lock:
            await conn.execute(sql, tuple(args))
            await conn.commit()

    async def _proxy(request: web.Request, target_path: str) -> web.Response:
        body = await request.read()
        query = f"?{request.query_string}" if request.query_string else ""
        url = f"http://127.0.0.1:{int(core.WEBAPP_PORT)}{target_path}{query}"
        headers = {
            "X-Telegram-Init-Data": request.headers.get("X-Telegram-Init-Data", ""),
            "Content-Type": request.headers.get("Content-Type", "application/json"),
        }
        async with ClientSession() as session:
            async with session.request(request.method, url, data=body, headers=headers) as response:
                raw = await response.read()
                return web.Response(
                    body=raw,
                    status=response.status,
                    content_type=response.content_type or "application/json",
                    charset=response.charset,
                )

    @web.middleware
    async def hotfix_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
        path = request.path
        if request.method == "GET" and path in {"/admin-v89", "/admin-v89/"}:
            query = dict(request.query)
            query["build"] = str(int(time.time()))
            raise web.HTTPFound(location="/admin-v76/?" + urlencode(query))
        if request.method == "GET" and path in {
            "/admin-v89/admin-v89.js",
            "/admin-v76/admin-v89.js",
        }:
            return web.FileResponse(
                SCRIPT_PATH,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Admin-Center": "reality-92",
                },
            )
        if path == "/admin-v89/api/state":
            return await _proxy(request, "/admin-v76/api/state")
        if path == "/admin-v89/api/action":
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if str(payload.get("action") or "") == "game_attempts_set":
                return await _set_attempts(request)
            return await _proxy(request, "/admin-v76/api/action")
        if path == "/games-v89/api/state":
            return await _proxy(request, "/games/api/state")
        if path == "/games-v89/api/start":
            return await _proxy(request, "/games/api/start")

        action_payload: dict[str, Any] = {}
        if request.method == "POST" and path == "/admin-v76/api/action":
            try:
                action_payload = await request.json()
            except Exception:
                action_payload = {}
            if str(action_payload.get("action") or "") == "game_attempts_set":
                return await _set_attempts(request)

        response = await handler(request)
        if request.method == "GET" and path == "/admin-v76/api/state":
            data = await _json_from_response(response)
            if data and data.get("ok"):
                await _augment_games(data, admin=True)
                await _augment_knowledge(data)
                return core.web.json_response(data, status=response.status)
        if request.method == "POST" and path == "/games/api/state":
            data = await _json_from_response(response)
            if data and data.get("ok"):
                await _augment_games(data, admin=False)
                return core.web.json_response(data, status=response.status)
        if action_payload and isinstance(response, web.Response) and response.status < 400:
            await _clear_custom_after_reset(request, action_payload)
        return response

    # Ставится до остальных Mini App: все последующие модули захватывают уже
    # эту фабрику Application, поэтому middleware не теряется в цепочке обёрток.
    original_application = core.web.Application

    def application_with_hotfix(*args: Any, **kwargs: Any):
        existing = list(kwargs.pop("middlewares", []) or [])
        kwargs["middlewares"] = [hotfix_middleware, *existing]
        return original_application(*args, **kwargs)

    core.web.Application = application_with_hotfix
