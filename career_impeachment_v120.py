from __future__ import annotations

import time
from typing import Any

from career_model_v120 import CAREER_CENTER, CAREER_HERO, career_value


def install_career_impeachment_v120(core: Any) -> None:
    if getattr(core, "_career_impeachment_v120_installed", False):
        return
    core._career_impeachment_v120_installed = True

    original_is_honest_hero = core.is_honest_hero

    async def is_honest_hero_v120(chat_id: int, player: Any) -> bool:
        fresh = await core.db.get_player(int(chat_id), int(player.user_id)) or player
        if career_value(fresh.points) >= CAREER_CENTER:
            return False
        return await original_is_honest_hero(chat_id, fresh)

    core.is_honest_hero = is_honest_hero_v120

    original_set_player_points = core.Database.set_player_points

    async def set_player_points_with_career_demote(
        self: Any,
        chat_id: int,
        user_id: int,
        new_points: int,
        reason: str,
    ):
        conn = self._require_connection()
        cursor = await conn.execute(
            "SELECT career_points FROM players WHERE chat_id=? AND user_id=?",
            (int(chat_id), int(user_id)),
        )
        row = await cursor.fetchone()
        career_before = int(row["career_points"] or 0) if row else 0
        wallet_before, after = await original_set_player_points(
            self,
            int(chat_id),
            int(user_id),
            int(new_points),
            str(reason),
        )
        lowered = str(reason or "").casefold()
        if (
            "impeachment" in lowered
            and "demote" in lowered
            and CAREER_HERO <= career_before < CAREER_CENTER
        ):
            career_after = CAREER_HERO - 1
            created_at = int(time.time())
            async with self.lock:
                await conn.execute(
                    "UPDATE players SET career_points=?,career_initialized=1,updated_at=? "
                    "WHERE chat_id=? AND user_id=?",
                    (career_after, created_at, int(chat_id), int(user_id)),
                )
                await conn.execute(
                    "INSERT INTO career_log_v120("
                    "chat_id,user_id,delta,reason,source_type,source_id,created_at"
                    ") VALUES(?,?,?,?,?,?,?)",
                    (
                        int(chat_id),
                        int(user_id),
                        career_after - career_before,
                        "Понижение после успешного импичмента",
                        "impeachment",
                        f"impeachment:{created_at}",
                        created_at,
                    ),
                )
                await conn.commit()
            after = await self.get_player(int(chat_id), int(user_id)) or after
        return wallet_before, after

    core.Database.set_player_points = set_player_points_with_career_demote

    def impeachment_active_text_v120(target: Any, vote_count: int) -> str:
        return (
            "🏛 <b>ИМПИЧМЕНТ ОТКРЫТ!</b> 🏛\n\n"
            f"Под судом беседы: {core.player_link(target)}.\n"
            f"Карьерное влияние: <b>{career_value(target.points):,}</b>.\n\n"
            "Нажмите одну из кнопок 🔥, 👍 или ❤️ снизу. "
            "Нужны пять разных участников.\n"
            f"Прогресс: <b>{int(vote_count)}/{int(core.IMPEACHMENT_REACTION_TARGET)} голосов</b>.\n\n"
            "После пятого голоса Главный герой будет понижен до "
            "<b>Второстепенной роли</b>: карьерное влияние станет <b>899 999</b>. "
            "Центр Вселенной обычному импичменту не подлежит."
        ).replace(",", " ")

    core.impeachment_active_text = impeachment_active_text_v120
