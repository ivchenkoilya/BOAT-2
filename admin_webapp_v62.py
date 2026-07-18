from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aiogram.types import (
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
    WebAppInfo,
)

LOGGER = logging.getLogger(__name__)
ADMIN_DIR = Path(__file__).resolve().parent / "adminapp"
ROLE_POINTS = {
    "decoration": ("🪑 Декорация", 0),
    "dust": ("🌫 Пыль", 500),
    "extras": ("👥 Массовка", 1000),
    "secondary": ("🎭 Второстепенная роль", 2000),
    "hero": ("👑 Главный герой", 3000),
}
ATTACKS = {"shield", "silence", "single", "mass"}
CHAT_TITLE_CACHE: dict[int, tuple[float, str]] = {}


def install_admin_webapp_v62(core: Any) -> None:
    """Устанавливает отдельное защищённое Mini App для управления ботом."""
    if getattr(core, "_admin_webapp_v62_installed", False):
        return
    core._admin_webapp_v62_installed = True

    original_connect = core.Database.connect
    original_open_admin_panel = core.open_admin_panel

    async def connect_with_admin_schema(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS admin_action_log_v62 (
                    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL,
                    chat_id INTEGER,
                    target_user_id INTEGER,
                    action TEXT NOT NULL,
                    detail TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    reversible INTEGER NOT NULL DEFAULT 0,
                    undone_at INTEGER,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_admin_action_log_v62_created
                ON admin_action_log_v62 (created_at DESC);
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_admin_schema

    def _json_error(reason: str, status: int = 400):
        return core.web.json_response({"ok": False, "reason": reason}, status=status)

    def _auth(request: Any) -> tuple[User | None, Any | None]:
        user, reason = core._webapp_auth(request)
        if user is None:
            return None, _json_error(reason or "Нет авторизации.", 401)
        if int(user.id) != int(core.DEVELOPER_ID):
            return None, _json_error("Админ-панель доступна только владельцу бота.", 403)
        return user, None

    async def _payload(request: Any) -> dict[str, Any]:
        try:
            value = await request.json()
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    def _int(
        value: Any,
        default: int = 0,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = default
        if minimum is not None:
            number = max(minimum, number)
        if maximum is not None:
            number = min(maximum, number)
        return number

    def _role(points: int) -> dict[str, Any]:
        if points < 500:
            key, emoji, title = "decoration", "🪑", "Декорация"
        elif points < 1000:
            key, emoji, title = "dust", "🌫", "Пыль"
        elif points < 2000:
            key, emoji, title = "extras", "👥", "Массовка"
        elif points < 3000:
            key, emoji, title = "secondary", "🎭", "Второстепенная роль"
        else:
            key, emoji, title = "hero", "👑", "Главный герой"
        return {"key": key, "emoji": emoji, "title": title}

    async def _chat_title(bot: Any, chat_id: int) -> str:
        cached = CHAT_TITLE_CACHE.get(chat_id)
        if cached and time.time() - cached[0] < 600:
            return cached[1]
        title = str(chat_id)
        try:
            chat = await bot.get_chat(chat_id)
            title = str(chat.title or chat.full_name or chat_id)
        except Exception:
            pass
        CHAT_TITLE_CACHE[chat_id] = (time.time(), title)
        return title

    async def _chat_rows() -> list[Any]:
        conn = core.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT chat_id, COUNT(*) AS users, MAX(updated_at) AS updated_at
            FROM players
            WHERE chat_id < 0
            GROUP BY chat_id
            ORDER BY updated_at DESC
            LIMIT 30
            """
        )
        return list(await cursor.fetchall())

    async def _resolve_chat(requested: int) -> int:
        rows = await _chat_rows()
        available = {int(row["chat_id"]) for row in rows}
        if requested in available:
            return requested
        latest = await core.db.admin_latest_group_player(core.DEVELOPER_ID)
        if latest is not None and int(latest.chat_id) in available:
            return int(latest.chat_id)
        return int(rows[0]["chat_id"]) if rows else 0

    async def _resolve_target(chat_id: int, requested: int) -> Any | None:
        if chat_id == 0:
            return None
        if requested:
            found = await core.db.get_player(chat_id, requested)
            if found is not None:
                return found
        own = await core.db.get_player(chat_id, core.DEVELOPER_ID)
        if own is not None:
            return own
        board = await core.db.leaderboard(chat_id, limit=1)
        return board[0] if board else None

    async def _knowledge(chat_id: int, user_id: int) -> dict[str, Any]:
        import talent_system

        try:
            state = await talent_system.talent_state(core.db, chat_id, user_id)
        except Exception:
            state = {
                "points": {"total": 0, "spent": 0, "available": 0},
                "levels": {},
                "buffs": {},
            }
        conn = core.db._require_connection()
        cursor = await conn.execute(
            "SELECT shards FROM knowledge_wallets WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        wallet = await cursor.fetchone()
        iso = datetime.now(timezone.utc).date().isocalendar()
        week_key = f"{iso.year}-W{iso.week:02d}"
        cursor = await conn.execute(
            """
            SELECT tree_points FROM knowledge_weekly
            WHERE chat_id = ? AND user_id = ? AND week_key = ?
            """,
            (chat_id, user_id, week_key),
        )
        weekly = await cursor.fetchone()
        levels = state.get("levels") or {}
        active = []
        for skill_id, level in levels.items():
            if int(level) <= 0:
                continue
            spec = talent_system.SKILLS.get(str(skill_id), {})
            active.append(
                {
                    "skill_id": str(skill_id),
                    "name": str(spec.get("name") or skill_id),
                    "branch": str(spec.get("branch") or "other"),
                    "level": int(level),
                    "max": int(spec.get("max") or level),
                }
            )
        return {
            "shards": int(wallet["shards"]) if wallet else 0,
            "weekly_tree_points": int(weekly["tree_points"]) if weekly else 0,
            "weekly_cap": 3,
            "profile": state.get("points")
            or {"total": 0, "spent": 0, "available": 0},
            "levels": active,
            "buffs": state.get("buffs") or {},
        }

    async def _boss_state(chat_id: int) -> dict[str, Any] | None:
        if chat_id == 0:
            return None
        conn = core.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT * FROM boss_battles
            WHERE chat_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (chat_id,),
        )
        battle = await cursor.fetchone()
        if battle is None:
            return None
        boss_id = str(battle["boss_id"])
        cursor = await conn.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN player_hp > 0 THEN 1 ELSE 0 END) AS alive
            FROM boss_fighters WHERE boss_id = ?
            """,
            (boss_id,),
        )
        fighter_count = await cursor.fetchone()
        runtime = None
        try:
            cursor = await conn.execute(
                "SELECT * FROM boss_runtime_v60 WHERE boss_id = ?",
                (boss_id,),
            )
            runtime = await cursor.fetchone()
        except Exception:
            runtime = None
        logs = await core.db.recent_boss_logs(boss_id, 8)
        planned_key = str(runtime["planned_action"] or "") if runtime else ""
        action_info = {}
        try:
            import raid_v60

            action_info = dict(raid_v60.ACTION_INFO.get(planned_key, {}))
        except Exception:
            pass
        return {
            "boss_id": boss_id,
            "status": str(battle["status"]),
            "hp": int(battle["hp"]),
            "max_hp": int(battle["max_hp"]),
            "phase": int(battle["phase"]),
            "ends_at": int(battle["ends_at"]),
            "next_action_at": int(battle["next_action_at"]),
            "fighters": int(fighter_count["total"] or 0) if fighter_count else 0,
            "alive": int(fighter_count["alive"] or 0) if fighter_count else 0,
            "pressure": int(runtime["pressure"] or 0) if runtime else 0,
            "pressure_max": 120,
            "planned_action": planned_key,
            "planned_action_name": str(action_info.get("name") or "Не выбрана"),
            "planned_action_icon": str(action_info.get("icon") or "⚠"),
            "logs": logs,
            "player_url": (
                f"{core.WEBAPP_PUBLIC_URL}/boss-app/?boss={boss_id}"
                if core.WEBAPP_PUBLIC_URL
                else core.boss_miniapp_link(boss_id)
            ),
        }

    async def _history(limit: int = 40) -> list[dict[str, Any]]:
        conn = core.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT * FROM admin_action_log_v62
            ORDER BY action_id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            {
                "id": int(row["action_id"]),
                "admin_id": int(row["admin_id"]),
                "chat_id": int(row["chat_id"] or 0),
                "target_user_id": int(row["target_user_id"] or 0),
                "action": str(row["action"]),
                "detail": str(row["detail"]),
                "reversible": bool(row["reversible"]),
                "undone": row["undone_at"] is not None,
                "created_at": int(row["created_at"]),
            }
            for row in await cursor.fetchall()
        ]

    async def _log(
        admin_id: int,
        chat_id: int | None,
        target_id: int | None,
        action: str,
        detail: str,
        payload: dict[str, Any] | None = None,
        reversible: bool = False,
    ) -> None:
        conn = core.db._require_connection()
        async with core.db.lock:
            await conn.execute(
                """
                INSERT INTO admin_action_log_v62 (
                    admin_id, chat_id, target_user_id, action, detail,
                    payload_json, reversible, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    admin_id,
                    chat_id,
                    target_id,
                    action,
                    detail,
                    json.dumps(
                        payload or {},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    1 if reversible else 0,
                    int(time.time()),
                ),
            )
            await conn.commit()

    async def _database_health() -> dict[str, Any]:
        conn = core.db._require_connection()
        cursor = await conn.execute("PRAGMA quick_check")
        row = await cursor.fetchone()
        result = str(row[0] if row else "unknown")
        counts = {}
        for table in (
            "players",
            "boss_battles",
            "talent_profiles",
            "admin_action_log_v62",
        ):
            try:
                cursor = await conn.execute(f"SELECT COUNT(*) AS amount FROM {table}")
                item = await cursor.fetchone()
                counts[table] = int(item["amount"] if item else 0)
            except Exception:
                counts[table] = -1
        return {"status": result, "counts": counts}

    async def _state(request: Any):
        user, error = _auth(request)
        if error is not None:
            return error
        requested_chat = _int(request.query.get("chat_id"), 0)
        requested_user = _int(request.query.get("user_id"), 0)
        chat_id = await _resolve_chat(requested_chat)
        target = await _resolve_target(chat_id, requested_user)
        bot = request.app["bot"]

        chats = []
        for row in await _chat_rows():
            cid = int(row["chat_id"])
            chats.append(
                {
                    "chat_id": cid,
                    "title": await _chat_title(bot, cid),
                    "users": int(row["users"]),
                }
            )

        target_data = None
        behavior = {}
        knowledge = None
        if target is not None:
            behavior = await core.db.get_behavior(chat_id, target.user_id)
            knowledge = await _knowledge(chat_id, target.user_id)
            target_data = {
                "chat_id": int(target.chat_id),
                "user_id": int(target.user_id),
                "username": target.username,
                "full_name": target.full_name,
                "points": int(target.points),
                "message_count": int(target.message_count),
                "role": _role(int(target.points)),
            }

        conn = core.db._require_connection()
        cursor = (
            await conn.execute(
                """
                SELECT user_id, username, full_name, points, message_count
                FROM players WHERE chat_id = ?
                ORDER BY points DESC, updated_at DESC
                LIMIT 12
                """,
                (chat_id,),
            )
            if chat_id
            else None
        )
        quick_users = []
        if cursor is not None:
            for row in await cursor.fetchall():
                quick_users.append(
                    {
                        "user_id": int(row["user_id"]),
                        "username": row["username"],
                        "full_name": str(row["full_name"]),
                        "points": int(row["points"]),
                        "message_count": int(row["message_count"]),
                        "role": _role(int(row["points"])),
                    }
                )

        return core.web.json_response(
            {
                "ok": True,
                "version": "Reality 62 · Админ-центр",
                "admin": {"user_id": int(user.id), "name": user.full_name},
                "selected_chat": {
                    "chat_id": chat_id,
                    "title": (
                        await _chat_title(bot, chat_id) if chat_id else "Нет беседы"
                    ),
                },
                "chats": chats,
                "target": target_data,
                "behavior": behavior,
                "knowledge": knowledge,
                "quick_users": quick_users,
                "boss": await _boss_state(chat_id),
                "history": await _history(),
                "health": await _database_health(),
            }
        )

    async def _users(request: Any):
        _, error = _auth(request)
        if error is not None:
            return error
        chat_id = _int(request.query.get("chat_id"), 0)
        query = str(request.query.get("q") or "").strip().casefold()
        if not chat_id:
            return _json_error("Не выбрана беседа.")
        conn = core.db._require_connection()
        like = f"%{query.lstrip('@')}%"
        cursor = await conn.execute(
            """
            SELECT user_id, username, full_name, points, message_count
            FROM players
            WHERE chat_id = ? AND (
                ? = '' OR lower(full_name) LIKE ?
                OR lower(COALESCE(username,'')) LIKE ?
                OR CAST(user_id AS TEXT) LIKE ?
            )
            ORDER BY points DESC, updated_at DESC
            LIMIT 50
            """,
            (chat_id, query, like, like, like),
        )
        items = []
        for row in await cursor.fetchall():
            items.append(
                {
                    "user_id": int(row["user_id"]),
                    "username": row["username"],
                    "full_name": str(row["full_name"]),
                    "points": int(row["points"]),
                    "message_count": int(row["message_count"]),
                    "role": _role(int(row["points"])),
                }
            )
        return core.web.json_response({"ok": True, "users": items})

    async def _current_battle(chat_id: int) -> Any | None:
        conn = core.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT * FROM boss_battles WHERE chat_id = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (chat_id,),
        )
        return await cursor.fetchone()

    async def _set_shards(chat_id: int, user_id: int, value: int) -> tuple[int, int]:
        conn = core.db._require_connection()
        now = int(time.time())
        async with core.db.lock:
            cursor = await conn.execute(
                "SELECT shards FROM knowledge_wallets WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id),
            )
            row = await cursor.fetchone()
            old = int(row["shards"]) if row else 0
            new = max(0, min(1_000_000, int(value)))
            await conn.execute(
                """
                INSERT INTO knowledge_wallets (chat_id, user_id, shards, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET
                    shards = excluded.shards, updated_at = excluded.updated_at
                """,
                (chat_id, user_id, new, now),
            )
            await conn.commit()
        return old, new

    async def _set_tree_total(
        chat_id: int,
        user_id: int,
        value: int,
    ) -> tuple[int, int]:
        import talent_system

        await talent_system.sync_profile(core.db, chat_id, user_id)
        conn = core.db._require_connection()
        async with core.db.lock:
            cursor = await conn.execute(
                """
                SELECT total_points, spent_points FROM talent_profiles
                WHERE chat_id = ? AND user_id = ?
                """,
                (chat_id, user_id),
            )
            row = await cursor.fetchone()
            old = int(row["total_points"]) if row else 0
            spent = int(row["spent_points"]) if row else 0
            new = max(spent, min(1_000_000, int(value)))
            await conn.execute(
                """
                UPDATE talent_profiles SET total_points = ?, updated_at = ?
                WHERE chat_id = ? AND user_id = ?
                """,
                (new, int(time.time()), chat_id, user_id),
            )
            await conn.commit()
        return old, new

    async def _convert_shards(chat_id: int, user_id: int) -> tuple[int, int]:
        import talent_system

        await talent_system.sync_profile(core.db, chat_id, user_id)
        conn = core.db._require_connection()
        iso = datetime.now(timezone.utc).date().isocalendar()
        week_key = f"{iso.year}-W{iso.week:02d}"
        now = int(time.time())
        async with core.db.lock:
            cursor = await conn.execute(
                "SELECT shards FROM knowledge_wallets WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id),
            )
            wallet = await cursor.fetchone()
            shards = int(wallet["shards"]) if wallet else 0
            cursor = await conn.execute(
                """
                SELECT tree_points FROM knowledge_weekly
                WHERE chat_id = ? AND user_id = ? AND week_key = ?
                """,
                (chat_id, user_id, week_key),
            )
            weekly = await cursor.fetchone()
            weekly_points = int(weekly["tree_points"]) if weekly else 0
            converted = min(shards // 5, max(0, 3 - weekly_points))
            remaining = shards - converted * 5
            if converted:
                await conn.execute(
                    """
                    UPDATE knowledge_wallets SET shards = ?, updated_at = ?
                    WHERE chat_id = ? AND user_id = ?
                    """,
                    (remaining, now, chat_id, user_id),
                )
                await conn.execute(
                    """
                    INSERT INTO knowledge_weekly (
                        chat_id, user_id, week_key, tree_points, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(chat_id, user_id, week_key) DO UPDATE SET
                        tree_points = knowledge_weekly.tree_points + excluded.tree_points,
                        updated_at = excluded.updated_at
                    """,
                    (chat_id, user_id, week_key, converted, now),
                )
                await conn.execute(
                    """
                    UPDATE talent_profiles
                    SET total_points = total_points + ?, updated_at = ?
                    WHERE chat_id = ? AND user_id = ?
                    """,
                    (converted, now, chat_id, user_id),
                )
            await conn.commit()
        return converted, remaining

    async def _undo(admin_id: int) -> str:
        conn = core.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT * FROM admin_action_log_v62
            WHERE reversible = 1 AND undone_at IS NULL
            ORDER BY action_id DESC LIMIT 1
            """
        )
        row = await cursor.fetchone()
        if row is None:
            return "Нет действий, которые можно отменить."
        payload = json.loads(str(row["payload_json"] or "{}"))
        kind = str(payload.get("kind") or "")
        chat_id = int(row["chat_id"] or 0)
        user_id = int(row["target_user_id"] or 0)
        old = _int(payload.get("old"), 0)
        if kind == "points":
            await core.db.set_player_points(
                chat_id,
                user_id,
                old,
                "admin_app_v62_undo",
            )
        elif kind == "shards":
            await _set_shards(chat_id, user_id, old)
        elif kind == "tree_total":
            await _set_tree_total(chat_id, user_id, old)
        else:
            return "Последнее действие больше нельзя отменить."
        async with core.db.lock:
            await conn.execute(
                "UPDATE admin_action_log_v62 SET undone_at = ? WHERE action_id = ?",
                (int(time.time()), int(row["action_id"])),
            )
            await conn.commit()
        await _log(
            admin_id,
            chat_id,
            user_id,
            "undo",
            f"Отменено действие #{int(row['action_id'])}: {row['detail']}",
        )
        return "Последнее изменение отменено."

    async def _action(request: Any):
        admin, error = _auth(request)
        if error is not None:
            return error
        data = await _payload(request)
        action = str(data.get("action") or "").strip()
        chat_id = _int(data.get("chat_id"), 0)
        user_id = _int(data.get("user_id"), 0)
        value = _int(
            data.get("value"),
            0,
            -1_000_000_000,
            1_000_000_000,
        )
        bot = request.app["bot"]
        message = "Готово."

        if action == "undo":
            message = await _undo(admin.id)
            return core.web.json_response({"ok": True, "message": message})

        player = (
            await core.db.get_player(chat_id, user_id)
            if chat_id and user_id
            else None
        )
        if action.startswith(
            (
                "points_",
                "role_",
                "mute",
                "unmute",
                "cooldown_user",
                "stats_user",
                "shards_",
                "tree_",
                "knowledge_",
            )
        ) and player is None:
            return _json_error("Участник не найден в выбранной беседе.", 404)

        if action == "points_delta":
            old, updated = await core.db.add_points_with_balance(
                chat_id,
                user_id,
                value,
                "admin_app_v62_points",
            )
            new = int(updated.points)
            message = f"Влияние: {old} → {new}."
            await _log(
                admin.id,
                chat_id,
                user_id,
                action,
                message,
                {"kind": "points", "old": old, "new": new},
                True,
            )
        elif action == "points_set":
            old, updated = await core.db.set_player_points(
                chat_id,
                user_id,
                value,
                "admin_app_v62_set_points",
            )
            new = int(updated.points)
            message = f"Влияние установлено: {old} → {new}."
            await _log(
                admin.id,
                chat_id,
                user_id,
                action,
                message,
                {"kind": "points", "old": old, "new": new},
                True,
            )
        elif action == "role_set":
            role_key = str(data.get("role") or "")
            role_info = ROLE_POINTS.get(role_key)
            if role_info is None:
                return _json_error("Неизвестная роль.")
            old, updated = await core.db.set_player_points(
                chat_id,
                user_id,
                role_info[1],
                f"admin_app_v62_role_{role_key}",
            )
            new = int(updated.points)
            message = f"Роль изменена на {role_info[0]}: {old} → {new}."
            await _log(
                admin.id,
                chat_id,
                user_id,
                action,
                message,
                {"kind": "points", "old": old, "new": new},
                True,
            )
        elif action == "mute":
            minutes = _int(data.get("minutes"), 5, 1, 1440)
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=core.muted_chat_permissions(),
                use_independent_chat_permissions=True,
                until_date=datetime.now(timezone.utc) + timedelta(minutes=minutes),
            )
            message = f"{player.full_name} получил мут на {minutes} минут."
            await _log(admin.id, chat_id, user_id, action, message)
        elif action == "unmute":
            permissions = ChatPermissions(
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
            )
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=permissions,
                use_independent_chat_permissions=True,
            )
            message = f"Мут для {player.full_name} снят."
            await _log(admin.id, chat_id, user_id, action, message)
        elif action == "cooldown_user_chat":
            removed = await core.db.admin_reset_user_cooldowns(user_id, chat_id)
            message = f"Сброшено личных кулдаунов в беседе: {removed}."
            await _log(admin.id, chat_id, user_id, action, message)
        elif action == "cooldown_user_global":
            removed = await core.db.admin_reset_user_cooldowns(user_id)
            message = f"Сброшено личных кулдаунов во всех беседах: {removed}."
            await _log(admin.id, chat_id, user_id, action, message)
        elif action == "stats_user_reset":
            await core.db.admin_reset_behavior(chat_id, user_id)
            message = "Статистика выбранного участника сброшена."
            await _log(admin.id, chat_id, user_id, action, message)
        elif action in {"shards_delta", "shards_set"}:
            knowledge = await _knowledge(chat_id, user_id)
            old_value = int(knowledge["shards"])
            target_value = old_value + value if action == "shards_delta" else value
            old, new = await _set_shards(chat_id, user_id, target_value)
            message = f"Осколки знаний: {old} → {new}."
            await _log(
                admin.id,
                chat_id,
                user_id,
                action,
                message,
                {"kind": "shards", "old": old, "new": new},
                True,
            )
        elif action in {"tree_delta", "tree_set"}:
            knowledge = await _knowledge(chat_id, user_id)
            old_value = int(knowledge["profile"].get("total", 0))
            target_value = old_value + value if action == "tree_delta" else value
            old, new = await _set_tree_total(chat_id, user_id, target_value)
            message = f"Очки древа: {old} → {new}."
            await _log(
                admin.id,
                chat_id,
                user_id,
                action,
                message,
                {"kind": "tree_total", "old": old, "new": new},
                True,
            )
        elif action in {"tree_reset", "tree_refund"}:
            import talent_system

            await talent_system.sync_profile(core.db, chat_id, user_id)
            conn = core.db._require_connection()
            async with core.db.lock:
                await conn.execute(
                    "DELETE FROM talent_levels WHERE chat_id = ? AND user_id = ?",
                    (chat_id, user_id),
                )
                await conn.execute(
                    """
                    UPDATE talent_profiles SET spent_points = 0, updated_at = ?
                    WHERE chat_id = ? AND user_id = ?
                    """,
                    (int(time.time()), chat_id, user_id),
                )
                await conn.commit()
            message = "Прокачка древа сброшена, потраченные очки возвращены."
            await _log(admin.id, chat_id, user_id, action, message)
        elif action == "knowledge_convert":
            converted, remaining = await _convert_shards(chat_id, user_id)
            message = (
                f"Преобразовано очков древа: {converted}. "
                f"Осколков осталось: {remaining}."
            )
            await _log(admin.id, chat_id, user_id, action, message)
        elif action == "knowledge_week_reset":
            iso = datetime.now(timezone.utc).date().isocalendar()
            week_key = f"{iso.year}-W{iso.week:02d}"
            conn = core.db._require_connection()
            async with core.db.lock:
                await conn.execute(
                    """
                    DELETE FROM knowledge_weekly
                    WHERE chat_id = ? AND user_id = ? AND week_key = ?
                    """,
                    (chat_id, user_id, week_key),
                )
                await conn.commit()
            message = "Недельный лимит рейдовых очков древа сброшен."
            await _log(admin.id, chat_id, user_id, action, message)
        elif action == "knowledge_recalculate":
            import talent_system

            state = await talent_system.talent_state(core.db, chat_id, user_id)
            message = (
                "Профиль пересчитан. Доступно очков: "
                f"{int(state['points']['available'])}."
            )
            await _log(admin.id, chat_id, user_id, action, message)
        elif action == "chat_cooldowns_reset":
            removed = await core.db.admin_reset_chat_cooldowns(chat_id)
            message = f"Сброшены кулдауны беседы: {removed}."
            await _log(admin.id, chat_id, None, action, message)
        elif action == "chat_stats_reset":
            conn = core.db._require_connection()
            cursor = await conn.execute(
                "SELECT user_id FROM players WHERE chat_id = ?",
                (chat_id,),
            )
            ids = [int(row["user_id"]) for row in await cursor.fetchall()]
            for uid in ids:
                await core.db.admin_reset_behavior(chat_id, uid)
            message = f"Статистика беседы сброшена для {len(ids)} участников."
            await _log(admin.id, chat_id, None, action, message)
        elif action == "chat_profiles_recalculate":
            import talent_system

            conn = core.db._require_connection()
            cursor = await conn.execute(
                "SELECT user_id FROM players WHERE chat_id = ?",
                (chat_id,),
            )
            ids = [int(row["user_id"]) for row in await cursor.fetchall()]
            for uid in ids:
                try:
                    await talent_system.sync_profile(core.db, chat_id, uid)
                except Exception:
                    LOGGER.exception("Не удалось пересчитать профиль %s", uid)
            message = f"Пересчитано профилей: {len(ids)}."
            await _log(admin.id, chat_id, None, action, message)
        elif action == "database_check":
            health = await _database_health()
            message = f"Проверка базы: {health['status']}."
            await _log(admin.id, chat_id, None, action, message)
        elif action == "boss_start":
            started, text = await core.start_boss_battle(chat_id, admin, bot)
            message = "Босс запущен." if started else str(text)
            await _log(admin.id, chat_id, None, action, message)
        elif action.startswith("boss_"):
            battle = await _current_battle(chat_id)
            if battle is None:
                return _json_error("В этой беседе ещё не было рейда.", 404)
            boss_id = str(battle["boss_id"])
            conn = core.db._require_connection()
            if action in {"boss_hp_delta", "boss_hp_set"}:
                current = int(battle["hp"])
                max_hp = int(battle["max_hp"])
                new_hp = current + value if action == "boss_hp_delta" else value
                new_hp = max(0, min(max_hp, new_hp))
                phase = core.boss_phase_for_hp(new_hp, max_hp)
                async with core.db.lock:
                    await conn.execute(
                        """
                        UPDATE boss_battles SET hp = ?, phase = ?
                        WHERE boss_id = ?
                        """,
                        (new_hp, phase, boss_id),
                    )
                    await conn.commit()
                message = f"HP босса: {current} → {new_hp}."
            elif action in {"boss_pressure_reset", "boss_pressure_fill"}:
                pressure = 0 if action.endswith("reset") else 120
                async with core.db.lock:
                    await conn.execute(
                        """
                        INSERT OR IGNORE INTO boss_runtime_v60 (
                            boss_id, pressure, pressure_updated_at
                        ) VALUES (?, 0, ?)
                        """,
                        (boss_id, int(time.time())),
                    )
                    await conn.execute(
                        """
                        UPDATE boss_runtime_v60
                        SET pressure = ?, pressure_updated_at = ?
                        WHERE boss_id = ?
                        """,
                        (pressure, int(time.time()), boss_id),
                    )
                    await conn.commit()
                message = f"Давление отряда установлено: {pressure}/120."
            elif action == "boss_cooldowns_reset":
                async with core.db.lock:
                    await conn.execute(
                        """
                        UPDATE boss_fighters
                        SET last_attack_at = 0, ability_used_at = 0,
                            heal_used_at = 0, defend_used_at = 0,
                            silenced_until = 0, knocked_out_until = 0
                        WHERE boss_id = ?
                        """,
                        (boss_id,),
                    )
                    await conn.commit()
                message = "Кулдауны и блокировки участников рейда сброшены."
            elif action == "boss_phase_set":
                phase = _int(data.get("phase"), 1, 1, 4)
                max_hp = int(battle["max_hp"])
                ratios = {1: 1.0, 2: 0.75, 3: 0.50, 4: 0.25}
                new_hp = max(1, int(max_hp * ratios[phase]))
                async with core.db.lock:
                    await conn.execute(
                        """
                        UPDATE boss_battles SET hp = ?, phase = ?
                        WHERE boss_id = ?
                        """,
                        (new_hp, phase, boss_id),
                    )
                    await conn.commit()
                message = f"Установлена фаза {phase}, HP: {new_hp}."
            elif action == "boss_attack_set":
                attack = str(data.get("attack") or "")
                if attack not in ATTACKS:
                    return _json_error("Неизвестная атака босса.")
                async with core.db.lock:
                    await conn.execute(
                        """
                        INSERT OR IGNORE INTO boss_runtime_v60 (
                            boss_id, pressure, pressure_updated_at
                        ) VALUES (?, 0, ?)
                        """,
                        (boss_id, int(time.time())),
                    )
                    await conn.execute(
                        """
                        UPDATE boss_runtime_v60
                        SET planned_action = ?, planned_for = ?
                        WHERE boss_id = ?
                        """,
                        (attack, int(battle["next_action_at"]), boss_id),
                    )
                    await conn.commit()
                message = f"Следующая атака установлена: {attack}."
            elif action == "boss_attack_now":
                now = int(time.time())
                async with core.db.lock:
                    await conn.execute(
                        "UPDATE boss_battles SET next_action_at = ? WHERE boss_id = ?",
                        (now, boss_id),
                    )
                    await conn.execute(
                        """
                        UPDATE boss_runtime_v60 SET planned_for = ?
                        WHERE boss_id = ?
                        """,
                        (now, boss_id),
                    )
                    await conn.commit()
                result = await core.db.boss_perform_action(boss_id)
                message = str(
                    result.get("log")
                    or result.get("reason")
                    or "Атака выполнена."
                )
            elif action == "boss_refresh_post":
                await core.edit_boss_post(bot, battle, change_media=True)
                message = "Сообщение босса обновлено."
            elif action == "boss_recover":
                if int(battle["hp"]) <= 0 or str(battle["status"]) == "resolving":
                    await core.resolve_boss_victory(boss_id, bot)
                    message = "Завершение рейда восстановлено."
                else:
                    message = "Рейд не находится в зависшем завершении."
            elif action == "boss_victory":
                async with core.db.lock:
                    await conn.execute(
                        "UPDATE boss_battles SET hp = 0, phase = 4 WHERE boss_id = ?",
                        (boss_id,),
                    )
                    await conn.commit()
                await core.resolve_boss_victory(boss_id, bot)
                message = "Рейд завершён победой с выдачей наград."
            elif action == "boss_cancel":
                text = "🛑 <b>РЕЙД ОТМЕНЁН АДМИНИСТРАТОРОМ</b>"
                await core.db.finish_boss(boss_id, "cancelled", text)
                refreshed = await core.db.get_boss(boss_id)
                if refreshed is not None:
                    try:
                        await core.edit_boss_post(
                            bot,
                            refreshed,
                            change_media=False,
                            final_caption=text,
                        )
                    except Exception:
                        LOGGER.exception("Не удалось обновить отменённый рейд")
                message = "Рейд отменён без наград."
            else:
                return _json_error("Неизвестное действие рейда.")
            await _log(admin.id, chat_id, None, action, message)
        else:
            return _json_error("Неизвестное действие админ-панели.")

        return core.web.json_response({"ok": True, "message": message})

    async def admin_index(request: Any):
        return core.web.FileResponse(
            ADMIN_DIR / "index.html",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
            },
        )

    async def admin_file(request: Any):
        name = request.match_info["name"]
        if name not in {"admin.css", "admin.js"}:
            raise core.web.HTTPNotFound()
        return core.web.FileResponse(
            ADMIN_DIR / name,
            headers={"Cache-Control": "no-store, max-age=0"},
        )

    async def start_webapp_server_with_admin(bot: Any):
        if not core.WEBAPP_DIR.is_dir():
            raise RuntimeError(f"Не найдена папка Mini App: {core.WEBAPP_DIR}")
        if not ADMIN_DIR.is_dir():
            raise RuntimeError(f"Не найдена папка админ Mini App: {ADMIN_DIR}")
        app = core.web.Application(client_max_size=1024 * 1024)
        app["bot"] = bot
        app.router.add_get("/", core.webapp_index)
        app.router.add_get("/boss-app", core.webapp_index)
        app.router.add_get("/boss-app/", core.webapp_index)
        app.router.add_get(
            "/boss-app/{name:style\\.css|app\\.js}",
            core.webapp_file,
        )
        app.router.add_static(
            "/boss-app/assets/",
            core.WEBAPP_DIR / "assets",
            show_index=False,
        )
        app.router.add_post("/boss-app/api/boss/session", core.webapp_session)
        app.router.add_get("/boss-app/api/boss/state", core.webapp_state)
        app.router.add_post("/boss-app/api/boss/action", core.webapp_action)
        app.router.add_get("/admin-app", admin_index)
        app.router.add_get("/admin-app/", admin_index)
        app.router.add_get(
            "/admin-app/{name:admin\\.css|admin\\.js}",
            admin_file,
        )
        app.router.add_get("/admin-app/api/state", _state)
        app.router.add_get("/admin-app/api/users", _users)
        app.router.add_post("/admin-app/api/action", _action)
        app.router.add_get("/health", core.healthcheck)
        runner = core.web.AppRunner(app, access_log=None)
        await runner.setup()
        site = core.web.TCPSite(runner, core.WEBAPP_HOST, core.WEBAPP_PORT)
        await site.start()
        logging.info(
            "Mini App и админ-центр запущены на %s:%s",
            core.WEBAPP_HOST,
            core.WEBAPP_PORT,
        )
        return runner

    core.start_webapp_server = start_webapp_server_with_admin

    async def open_admin_miniapp(message: Message, bot: Any) -> None:
        if not message.from_user or int(message.from_user.id) != int(core.DEVELOPER_ID):
            return
        if not core.WEBAPP_PUBLIC_URL:
            await original_open_admin_panel(message, bot)
            await message.answer(
                "⚠️ Для отдельного Admin Mini App укажи WEBAPP_PUBLIC_URL. "
                "Пока открыта старая панель."
            )
            return

        command_parts = (message.text or "").split(maxsplit=1)
        query = command_parts[1].strip() if len(command_parts) == 2 else ""
        target = None
        chat_id = 0
        if core.is_group(message):
            chat_id = int(message.chat.id)
            replied = (
                message.reply_to_message.from_user
                if message.reply_to_message
                else None
            )
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
            await message.answer(
                "⚠️ Сначала открой <code>/admin</code> в нужной групповой беседе."
            )
            return

        url = (
            f"{core.WEBAPP_PUBLIC_URL}/admin-app/"
            f"?chat_id={chat_id}&user_id={int(target.user_id)}&v=62"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛠 Открыть админ-центр",
                        web_app=WebAppInfo(url=url),
                    )
                ]
            ]
        )
        try:
            await bot.send_message(
                chat_id=message.from_user.id,
                text=(
                    "🛠 <b>АДМИН-ЦЕНТР REALITY 62</b>\n\n"
                    f"Беседа: <code>{chat_id}</code>\n"
                    f"Участник: <b>{target.full_name}</b>\n\n"
                    "Панель работает только для твоего Telegram ID."
                ),
                reply_markup=keyboard,
            )
        except Exception:
            await message.answer(
                "⚠️ Не удалось отправить админ-центр в личные сообщения. "
                "Сначала открой личку бота и нажми /start."
            )
            return
        if core.is_group(message):
            await core.ephemeral_reply(
                message,
                "🔒 Админ-центр отправлен тебе в личные сообщения.",
                delay_seconds=3,
            )

    core.open_admin_panel = open_admin_miniapp
