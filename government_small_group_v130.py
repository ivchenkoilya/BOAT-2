from __future__ import annotations

import html
import secrets
from typing import Any

import government_v127 as government
import hierarchy_v130 as hierarchy


VERSION = "Reality 130 · Компактное государство"


def install_government_small_group_v130(core: Any) -> None:
    if getattr(core, "_government_small_group_v130_installed", False):
        return
    core._government_small_group_v130_installed = True

    original_start_election = government._start_election

    async def start_election_scaled(
        core_value: Any,
        bot: Any,
        chat_id: int,
        office_key: str,
        actor_id: int,
    ) -> str:
        if office_key != "deputy":
            return await original_start_election(
                core_value,
                bot,
                chat_id,
                office_key,
                actor_id,
            )
        if await government._active_election(core_value, chat_id, office_key):
            raise ValueError("Выборы депутатов уже идут.")
        if actor_id != int(core_value.DEVELOPER_ID):
            existing = await government._office_rows(core_value, chat_id)
            if any(str(row["office_key"]) == "deputy" for row in existing):
                raise PermissionError(
                    "Досрочные выборы депутатов запускает только владелец бота."
                )

        active = await hierarchy.active_user_count(core_value, chat_id)
        seats = hierarchy.recommended_deputy_seats(active)
        now = government._now()
        election_id = secrets.token_urlsafe(12)
        spec = government.OFFICES["deputy"]
        conn = core_value.db._require_connection()
        await conn.execute(
            """
            INSERT INTO government_elections_v127(
              election_id,chat_id,office_key,seats,phase,nomination_ends_at,
              voting_ends_at,term_seconds,created_by,created_at,resolved_at
            ) VALUES(?,?,?,?,'nomination',?,0,?,?,?,0)
            """,
            (
                election_id,
                int(chat_id),
                "deputy",
                int(seats),
                now + government.NOMINATION_SECONDS,
                government.TERM_SECONDS,
                int(actor_id),
                now,
            ),
        )
        await conn.commit()
        await government._publish(
            bot,
            chat_id,
            f"🗳 <b>ОТКРЫТЫ ВЫБОРЫ: {html.escape(str(spec['title']).upper())}</b>\n\n"
            f"Активных участников за последние 14 дней: <b>{active}</b>.\n"
            f"Депутатских мест: <b>{seats}</b>.\n"
            f"Выдвижение завершится: "
            f"<b>{government._date_text(now + government.NOMINATION_SECONDS)}</b>\n\n"
            "Количество мест рассчитано автоматически под активность беседы.",
        )
        return election_id

    government._start_election = start_election_scaled

    original_state = government._state

    async def state_with_scale(
        core_value: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        active = await hierarchy.active_user_count(core_value, chat_id)
        recommended = hierarchy.recommended_deputy_seats(active)
        conn = core_value.db._require_connection()
        await conn.execute(
            """
            UPDATE government_elections_v127
            SET seats=?
            WHERE chat_id=? AND office_key='deputy' AND phase='nomination'
            """,
            (int(recommended), int(chat_id)),
        )
        await conn.commit()

        state = await original_state(core_value, bot, chat_id, user_id)
        current = sum(
            1
            for office in state.get("offices", [])
            if str(office.get("office_key")) == "deputy"
        )
        visible_seats = max(int(recommended), int(current))
        specs = {
            str(key): dict(value)
            for key, value in state.get("office_specs", {}).items()
        }
        if "deputy" in specs:
            specs["deputy"]["seats"] = visible_seats
        state["office_specs"] = specs
        state["government_scale"] = {
            "active_users": int(active),
            "total_users": len(state.get("eligible_users", [])),
            "deputy_seats": int(visible_seats),
            "recommended_deputy_seats": int(recommended),
            "quorum": max(1, (int(visible_seats) + 1) // 2),
            "activity_window_days": 14,
        }
        return state

    government._state = state_with_scale
