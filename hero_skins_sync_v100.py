from __future__ import annotations

import time
from typing import Any


MIN_SKIN_ID = 1
MAX_SKIN_ID = 7


def install_hero_skins_sync_v100(core: Any) -> None:
    """Сохраняет выбранный образ на сервере и отдаёт его всему отряду."""
    if getattr(core, "_hero_skins_sync_v101_installed", False):
        return

    core._hero_skins_sync_v101_installed = True

    original_connect = core.Database.connect

    async def connect_with_hero_skins(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS hero_skin_choices_v101 (
                    user_id INTEGER PRIMARY KEY,
                    skin_id INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    CHECK (skin_id BETWEEN 1 AND 7)
                );

                CREATE INDEX IF NOT EXISTS idx_hero_skin_choices_v101_updated
                ON hero_skin_choices_v101 (updated_at);

                INSERT OR IGNORE INTO hero_skin_choices_v101 (
                    user_id, skin_id, updated_at
                )
                SELECT user_id, skin_id, updated_at
                FROM hero_skin_choices_v100
                WHERE skin_id BETWEEN 1 AND 6;
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_hero_skins

    async def skin_map(database: Any, user_ids: list[int]) -> dict[int, int]:
        unique_ids = sorted({int(user_id) for user_id in user_ids if int(user_id) > 0})
        if not unique_ids:
            return {}

        placeholders = ",".join("?" for _ in unique_ids)
        conn = database._require_connection()
        cursor = await conn.execute(
            f"""
            SELECT user_id, skin_id
            FROM hero_skin_choices_v101
            WHERE user_id IN ({placeholders})
            """,
            tuple(unique_ids),
        )
        rows = await cursor.fetchall()
        return {
            int(row["user_id"]): int(row["skin_id"])
            for row in rows
            if MIN_SKIN_ID <= int(row["skin_id"]) <= MAX_SKIN_ID
        }

    async def save_skin(database: Any, user_id: int, skin_id: int) -> None:
        conn = database._require_connection()
        now = int(time.time())
        async with database.lock:
            await conn.execute(
                """
                INSERT INTO hero_skin_choices_v101 (user_id, skin_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    skin_id = excluded.skin_id,
                    updated_at = excluded.updated_at
                """,
                (int(user_id), int(skin_id), now),
            )
            await conn.commit()

    original_build_state = core.build_boss_web_state

    async def build_state_with_skins(boss_id: str, user_id: int) -> dict[str, Any]:
        result = await original_build_state(boss_id, user_id)
        if not result.get("ok"):
            return result

        fighters = list(result.get("fighters") or [])
        ids = [int(item.get("user_id", 0)) for item in fighters]
        if user_id not in ids:
            ids.append(int(user_id))
        choices = await skin_map(core.db, ids)

        for fighter in fighters:
            fighter_id = int(fighter.get("user_id", 0))
            fighter["skin_id"] = int(choices.get(fighter_id, 0))

        self_data = result.get("self")
        if isinstance(self_data, dict):
            self_data["skin_id"] = int(choices.get(int(user_id), 0))

        result["hero_skins"] = {
            "available": list(range(MIN_SKIN_ID, MAX_SKIN_ID + 1)),
            "selected": int(choices.get(int(user_id), 0)),
        }
        return result

    core.build_boss_web_state = build_state_with_skins

    original_webapp_action = core.webapp_action

    async def webapp_action_with_skins(request: Any):
        payload = await core._webapp_json(request)
        action = str(payload.get("action") or "").strip()
        if action != "select_skin":
            return await original_webapp_action(request)

        user, start_param = core._webapp_auth(request)
        if user is None:
            return core._webapp_error(start_param or "Нет авторизации.", 401)

        boss_id = str(start_param or payload.get("boss_id") or "").strip()
        if not boss_id:
            return core._webapp_error("Не найден идентификатор боя.")

        try:
            skin_id = int(payload.get("skin_id"))
        except (TypeError, ValueError):
            return core._webapp_error("Некорректный номер образа.")

        if not MIN_SKIN_ID <= skin_id <= MAX_SKIN_ID:
            return core._webapp_error("Этот образ пока недоступен.")

        battle = await core.db.get_boss(boss_id)
        if battle is None:
            return core._webapp_error("Бой не найден.", 404)

        conn = core.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT 1
            FROM boss_fighters
            WHERE boss_id = ? AND user_id = ?
            LIMIT 1
            """,
            (boss_id, int(user.id)),
        )
        if await cursor.fetchone() is None:
            return core._webapp_error("Сначала войди в отряд.", 403)

        await save_skin(core.db, int(user.id), skin_id)
        state = await core.build_boss_web_state(boss_id, int(user.id))
        state["selected_skin"] = skin_id
        return core.web.json_response(state)

    core.webapp_action = webapp_action_with_skins
