from __future__ import annotations

from typing import Any

import government_crisis_v131 as crisis


VERSION = "Reality 148 · Строгие кризисные полномочия"
COUNTERINTEL_ROLES = ("security", "prosecutor", "oversight", "president")


async def _strict_investigate_theft(
    core: Any,
    bot: Any,
    chat_id: int,
    user_id: int,
    theft_id: str,
) -> str:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_thefts_v131 WHERE theft_id=? AND chat_id=?",
        (str(theft_id), int(chat_id)),
    )
    theft = await cursor.fetchone()
    if (
        theft is None
        or str(theft["status"]) != "pending"
        or int(theft["resolve_at"]) <= crisis._now()
    ):
        raise ValueError("Эта операция уже закрыта.")

    offices = await crisis._offices(core, chat_id, user_id)
    office = next((key for key in crisis.INVESTIGATOR_OFFICES if key in offices), "")
    if not office:
        raise PermissionError(
            "Расследование доступно Надзору, прокуратуре, Минфину, "
            "Счётной палате, Совбезу, Центральному банку и президенту."
        )

    cursor = await conn.execute(
        "SELECT 1 FROM government_theft_investigations_v131 WHERE theft_id=? AND investigator_id=?",
        (str(theft_id), int(user_id)),
    )
    if await cursor.fetchone() is not None:
        raise ValueError("Ты уже проводил проверку этой операции.")

    prior = int(theft["investigations"] or 0)
    sabotage = int(theft["sabotage_bonus"] or 0)
    chance = max(
        5,
        min(
            95,
            int(crisis.INVESTIGATION_CHANCES.get(office, 20)) + prior * 5 - sabotage,
        ),
    )
    roll = crisis.secrets.randbelow(100) + 1
    success = roll <= chance
    now = crisis._now()
    await conn.execute(
        """
        INSERT INTO government_theft_investigations_v131(
            theft_id,investigator_id,office_key,chance,roll,success,created_at
        ) VALUES(?,?,?,?,?,?,?)
        """,
        (str(theft_id), int(user_id), office, chance, roll, 1 if success else 0, now),
    )
    await conn.execute(
        "UPDATE government_thefts_v131 SET investigations=investigations+1 WHERE theft_id=?",
        (str(theft_id),),
    )
    await conn.commit()

    if success:
        await crisis._catch_theft(core, bot, theft, user_id)
        return "Следы найдены. Виновник раскрыт, деньги возвращены."
    return "Проверка завершена, но доказательств пока недостаточно."


async def _strict_counterintel(
    core: Any,
    bot: Any,
    chat_id: int,
    user_id: int,
) -> str:
    offices = await crisis._offices(core, chat_id, user_id)
    office = next((key for key in COUNTERINTEL_ROLES if key in offices), "")
    if not office:
        raise PermissionError(
            "Контрразведка доступна президенту, Совбезу, прокуратуре и Надзору."
        )

    conflict = await crisis._active_conflict(core, chat_id)
    if (
        conflict is None
        or str(conflict["conflict_type"]) != "coup"
        or str(conflict["stage"]) not in {"recruiting", "preparation"}
    ):
        return "Признаков активного заговора не обнаружено."

    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_conflict_members_v131 WHERE conflict_id=? AND user_id=?",
        (str(conflict["conflict_id"]), int(user_id)),
    )
    own = await cursor.fetchone()
    if own is not None and str(own["status"]) == "accepted":
        raise PermissionError(
            "Участник заговора не может проводить контрразведку против самого себя."
        )

    cursor = await conn.execute(
        """
        SELECT last_action_at FROM government_conflict_members_v131
        WHERE conflict_id=? AND user_id=? AND side='counterintel'
        """,
        (str(conflict["conflict_id"]), int(user_id)),
    )
    row = await cursor.fetchone()
    if (
        row
        and int(row["last_action_at"] or 0) + crisis.COUP_ACTION_COOLDOWN
        > crisis._now()
    ):
        raise ValueError(
            "Следующая проверка доступна через "
            f"{crisis._remaining(int(row['last_action_at']) + crisis.COUP_ACTION_COOLDOWN)}."
        )

    base = {
        "security": 22,
        "prosecutor": 20,
        "oversight": 18,
        "president": 12,
    }.get(office, 15)
    defense = base + crisis.secrets.randbelow(9)
    chance = max(
        5,
        min(
            75,
            15
            + defense
            + int(conflict["defense_score"] or 0) // 3
            - int(conflict["plot_score"] or 0) // 5,
        ),
    )
    roll = crisis.secrets.randbelow(100) + 1
    now = crisis._now()
    await conn.execute(
        """
        INSERT INTO government_conflict_members_v131(
            conflict_id,user_id,side,status,role_key,points,last_action_at,invited_by,created_at
        ) VALUES(?,?,'counterintel','accepted',?,?,?,0,?)
        ON CONFLICT(conflict_id,user_id) DO UPDATE SET
            side='counterintel',status='accepted',role_key=excluded.role_key,
            points=government_conflict_members_v131.points+excluded.points,
            last_action_at=excluded.last_action_at
        """,
        (str(conflict["conflict_id"]), int(user_id), office, defense, now, now),
    )
    await conn.execute(
        "UPDATE government_conflicts_v131 SET defense_score=defense_score+? WHERE conflict_id=?",
        (defense, str(conflict["conflict_id"])),
    )
    await conn.commit()

    if roll <= chance:
        cursor = await conn.execute(
            "SELECT * FROM government_conflicts_v131 WHERE conflict_id=?",
            (str(conflict["conflict_id"]),),
        )
        fresh = await cursor.fetchone()
        if fresh is not None:
            await crisis._resolve_coup(
                core,
                bot,
                fresh,
                forced_success=False,
                discovered=True,
            )
        return "Заговор раскрыт. Участники задержаны."
    return "Проверка завершена. Прямых доказательств пока нет."


def install_government_crisis_permissions_v148(core: Any) -> None:
    if getattr(core, "_government_crisis_permissions_v148_installed", False):
        return
    core._government_crisis_permissions_v148_installed = True
    core.GOVERNMENT_VERSION = VERSION
    crisis._investigate_theft = _strict_investigate_theft
    crisis._counterintel = _strict_counterintel
