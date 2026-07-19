from __future__ import annotations

import re
import time
from typing import Any


HERO_DAY_REWARD = 500
# Статус действует до следующих выборов. Поле expires_at остаётся для
# совместимости со старой схемой и проверками боевой Mini App.
HERO_DAY_STATUS_EXPIRES_AT = 253_402_300_799
HERO_DAY_REWARD_MODE = "permanent_500"
ABOUT_VERSION = "Reality 77 · Главный герой дня"


def install_hero_day_v77(core: Any) -> None:
    """Переводит Главного героя дня на постоянную награду +500 без отката."""
    if getattr(core, "_hero_day_v77_installed", False):
        return
    core._hero_day_v77_installed = True
    core.HERO_DAY_REWARD = HERO_DAY_REWARD

    original_connect = core.Database.connect

    async def connect_with_hero_day_v77(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        now = int(time.time())

        async with self.lock:
            cursor = await conn.execute("PRAGMA table_info(hero_day_state)")
            columns = {str(row["name"]) for row in await cursor.fetchall()}
            if "reward_mode" not in columns:
                await conn.execute(
                    "ALTER TABLE hero_day_state "
                    "ADD COLUMN reward_mode TEXT NOT NULL DEFAULT 'legacy'"
                )

            # Старый активный герой мог быть временно поднят до порога роли.
            # Конвертируем только сам временный подъём в постоянные +500,
            # сохраняя весь заработанный или проигранный после выборов прогресс.
            cursor = await conn.execute(
                """
                SELECT h.chat_id, h.user_id, h.original_points,
                       h.assigned_points, h.reward_mode, p.points
                FROM hero_day_state h
                LEFT JOIN players p
                  ON p.chat_id = h.chat_id AND p.user_id = h.user_id
                WHERE COALESCE(h.reward_mode, 'legacy') <> ?
                """,
                (HERO_DAY_REWARD_MODE,),
            )
            rows = list(await cursor.fetchall())
            for row in rows:
                chat_id = int(row["chat_id"])
                user_id = int(row["user_id"])
                if row["points"] is None:
                    await conn.execute(
                        "DELETE FROM hero_day_state WHERE chat_id = ?",
                        (chat_id,),
                    )
                    continue

                current_points = int(row["points"])
                original_points = int(row["original_points"])
                legacy_assigned = int(row["assigned_points"])
                progress_after_election = current_points - legacy_assigned
                migrated_points = (
                    original_points + HERO_DAY_REWARD + progress_after_election
                )
                delta = migrated_points - current_points

                if delta:
                    await conn.execute(
                        """
                        UPDATE players
                        SET points = ?, updated_at = ?
                        WHERE chat_id = ? AND user_id = ?
                        """,
                        (migrated_points, now, chat_id, user_id),
                    )
                    await conn.execute(
                        """
                        INSERT INTO score_log (
                            chat_id, user_id, delta, reason, created_at
                        ) VALUES (?, ?, ?, 'hero_day_v77_migration', ?)
                        """,
                        (chat_id, user_id, delta, now),
                    )

                await conn.execute(
                    """
                    UPDATE hero_day_state
                    SET assigned_points = ?, expires_at = ?, reward_mode = ?
                    WHERE chat_id = ?
                    """,
                    (
                        migrated_points,
                        HERO_DAY_STATUS_EXPIRES_AT,
                        HERO_DAY_REWARD_MODE,
                        chat_id,
                    ),
                )

            await conn.commit()

    core.Database.connect = connect_with_hero_day_v77

    async def clear_previous_hero_day(
        self: Any,
        chat_id: int,
    ) -> Any | None:
        """Снимает только звание, не меняя баланс предыдущего героя."""
        conn = self._require_connection()
        user_id: int | None = None
        async with self.lock:
            cursor = await conn.execute(
                "SELECT user_id FROM hero_day_state WHERE chat_id = ?",
                (chat_id,),
            )
            state = await cursor.fetchone()
            if state is None:
                return None
            user_id = int(state["user_id"])
            await conn.execute(
                "DELETE FROM hero_day_state WHERE chat_id = ?",
                (chat_id,),
            )
            await conn.commit()
        return await self.get_player(chat_id, user_id)

    async def assign_hero_day(
        self: Any,
        chat_id: int,
        user_id: int,
        original_points: int | None = None,
        assigned_points: int | None = None,
    ) -> Any:
        """Выдаёт постоянные +500 и сохраняет только временный статус."""
        del original_points, assigned_points
        conn = self._require_connection()
        now = int(time.time())

        async with self.lock:
            cursor = await conn.execute(
                "SELECT points FROM players WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id),
            )
            row = await cursor.fetchone()
            if row is None:
                raise RuntimeError("Hero of the day player not found")

            before = int(row["points"])
            after = before + HERO_DAY_REWARD
            await conn.execute(
                """
                UPDATE players
                SET points = ?, updated_at = ?
                WHERE chat_id = ? AND user_id = ?
                """,
                (after, now, chat_id, user_id),
            )
            await conn.execute(
                """
                INSERT INTO score_log (
                    chat_id, user_id, delta, reason, created_at
                ) VALUES (?, ?, ?, 'hero_day_election_reward', ?)
                """,
                (chat_id, user_id, HERO_DAY_REWARD, now),
            )
            await conn.execute(
                """
                INSERT INTO hero_day_state (
                    chat_id, user_id, original_points, assigned_points,
                    selected_at, expires_at, reward_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    original_points = excluded.original_points,
                    assigned_points = excluded.assigned_points,
                    selected_at = excluded.selected_at,
                    expires_at = excluded.expires_at,
                    reward_mode = excluded.reward_mode
                """,
                (
                    chat_id,
                    user_id,
                    before,
                    after,
                    now,
                    HERO_DAY_STATUS_EXPIRES_AT,
                    HERO_DAY_REWARD_MODE,
                ),
            )
            await conn.commit()

        player = await self.get_player(chat_id, user_id)
        if player is None:
            raise RuntimeError("Hero of the day player disappeared")
        return player

    core.Database.restore_previous_hero_day = clear_previous_hero_day
    core.Database.assign_hero_day = assign_hero_day

    async def elect_hero_of_day(chat_id: int) -> str:
        previous = await core.db.restore_previous_hero_day(chat_id)
        board = await core.db.leaderboard(chat_id, limit=10_000)
        if not board:
            return (
                "🌟 <b>ВЫБОРЫ СОРВАНЫ</b>\n\n"
                "В этой беседе пока нет участников."
            )

        winner = core.random.choice(board)
        before = winner.points
        after = await core.db.assign_hero_day(
            chat_id,
            winner.user_id,
            before,
            before + HERO_DAY_REWARD,
        )

        previous_text = ""
        if previous is not None and previous.user_id != after.user_id:
            previous_text = (
                f"\n\n↩️ {core.player_link(previous)} больше не является "
                "Временным Главным героем. Его текущий баланс "
                f"<b>{previous.points}</b> полностью сохранён."
            )
        elif previous is not None:
            previous_text = (
                "\n\n🔁 Корона осталась у прежнего владельца, "
                "поэтому он получил новую постоянную награду за избрание."
            )

        return (
            "🌟 <b>ГЛАВНЫЙ ГЕРОЙ ДНЯ ВЫБРАН!</b> 🌟\n\n"
            f"🌟👑 Сегодня это {core.player_link(after)}.\n"
            "Ему присвоено звание <b>Временный Главный герой</b>.\n"
            f"🎁 Награда за избрание: <b>+{HERO_DAY_REWARD} обычных очков</b>.\n"
            f"📈 Баланс: <b>{before} → {after.points}</b>.\n\n"
            "Эти очки остаются навсегда: их можно выигрывать, проигрывать "
            "и использовать в играх. При следующих выборах снимается только "
            "временное звание."
            f"{previous_text}"
        )

    core.elect_hero_of_day = elect_hero_of_day

    original_stats = core.build_stats_text

    async def build_stats_text(chat_id: int, player: Any) -> str:
        text = await original_stats(chat_id, player)
        if player.user_id == await core.temporary_hero_day_user_id(chat_id):
            text = re.sub(
                r"(?m)^[^\n]* Роль: <b>.*?</b>$",
                "🌟👑 Роль: <b>Временный Главный герой</b>",
                text,
                count=1,
            )
        return text

    core.build_stats_text = build_stats_text

    original_profile = core.build_profile

    async def build_profile(
        chat_id: int,
        player: Any,
        *,
        addressed: bool = False,
    ) -> str:
        text = await original_profile(chat_id, player, addressed=addressed)
        if player.user_id != await core.temporary_hero_day_user_id(chat_id):
            return text

        text = re.sub(
            r"(?m)^[^\n]*<b>Твоя роль — .*?</b>$",
            "🌟👑 <b>Твоя роль — Временный Главный герой</b>",
            text,
            count=1,
        )
        text = re.sub(
            r"(?m)^[^\n]*<b>Роль — .*?</b>$",
            "🌟👑 <b>Роль — Временный Главный герой</b>",
            text,
            count=1,
        )
        return text

    core.build_profile = build_profile

    async def build_top_text(chat_id: int, heading: str = "Иерархия") -> str:
        board = await core.db.leaderboard(chat_id, limit=10)
        if not board:
            return "Здесь пока нет людей. Только декорации."

        temporary_id = await core.temporary_hero_day_user_id(chat_id)
        sabotage_ids = set(await core.db.active_sabotage_usurper_ids(chat_id))
        lines = [f"🏆 <b>{core.html.escape(heading)}</b>", ""]

        if temporary_id is not None:
            temporary_player = await core.db.get_player(chat_id, temporary_id)
            if temporary_player is not None:
                lines.extend(
                    [
                        "🌟👑 <b>Временный Главный герой</b>",
                        f"{core.player_link(temporary_player)} — "
                        f"<b>{temporary_player.points}</b> очков",
                        "",
                    ]
                )

        for index, player in enumerate(board, start=1):
            role = core.role_by_points(player.points, index == 1)
            role_title = role.title
            marker = "👑" if role.key == "hero" else f"{index}."

            if player.user_id == temporary_id:
                role_title = "Временный Главный герой"
                marker = "🌟"
            elif role.key == "hero" and player.user_id in sabotage_ids:
                role_title = "Саботажный Главный герой"
                marker = "💣"

            lines.append(
                f"{marker} {core.player_link(player)} — <b>{player.points}</b> "
                f"({role_title})"
            )

        lines.extend(
            [
                "",
                "Первое место не означает, что человек лучше остальных.",
                "Оно означает, что его ЧСВ оказалось убедительнее.",
            ]
        )
        return "\n".join(lines)

    core.build_top_text = build_top_text

    original_inline_menu_specs = core.inline_menu_specs

    def inline_menu_specs(user: Any) -> list[dict[str, Any]]:
        specs = original_inline_menu_specs(user)
        for spec in specs:
            if spec.get("action") == "hero_day":
                spec["description"] = (
                    "Временное звание и +500 постоянных очков · кулдаун 24 часа"
                )
                break
        return specs

    core.inline_menu_specs = inline_menu_specs

    previous_about = core.about_bot_text
    core.BOT_VERSION = ABOUT_VERSION

    def about_bot_text() -> str:
        text = previous_about()
        text = text.replace(
            "временно присваивает статус Временного Главного героя; "
            "при следующих выборах возвращает прежний баланс.",
            "присваивает временное звание и навсегда начисляет +500 очков; "
            "при следующих выборах снимается только звание.",
        )
        latest = (
            "Reality 77 — Главный герой дня получает временное звание и "
            "+500 постоянных очков; откат баланса удалён, статус показан в "
            "топе и даёт способности Временного Главного героя в рейде.\n"
        )
        marker = "📜 <b>ПОСЛЕДНИЕ ВЕРСИИ</b>\n"
        if latest not in text:
            if marker in text:
                text = text.replace(marker, marker + latest, 1)
            else:
                text += "\n\n🆕 <b>REALITY 77</b>\n" + latest.rstrip()
        return text

    core.about_bot_text = about_bot_text
