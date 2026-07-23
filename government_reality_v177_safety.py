from __future__ import annotations

import json
from typing import Any

import government_reality_v177 as integration
import government_reality_v177_api as api
import government_reality_v177_programs as programs
import government_v127 as gov

from government_reality_v177_common import json_value, fmt
from government_reality_v177_funds import debit_fund_locked


async def emergency_transfer_safe(
    core: Any,
    bot: Any,
    chat_id: int,
    actor_id: int,
) -> str:
    offices = await gov._user_offices(core, int(chat_id), int(actor_id))
    if not set(offices).intersection({"president", "security"}) and int(actor_id) != int(core.DEVELOPER_ID):
        raise PermissionError("Экстренное действие доступно президенту и Совбезу.")

    conn = core.db._require_connection()
    now = gov._now()
    async with core.db.lock:
        # The effect and its one-use flag are read again while holding the same lock as
        # the money transfer. Two devices therefore cannot consume the action together.
        cursor = await conn.execute(
            """SELECT * FROM government_program_effects_v177
            WHERE chat_id=? AND effect_key='emergency_mode' AND active=1 AND ends_at>?
            ORDER BY ends_at DESC LIMIT 1""",
            (int(chat_id), now),
        )
        effect = await cursor.fetchone()
        if effect is None:
            raise ValueError("Режим чрезвычайной ситуации сейчас не действует.")
        payload = json_value(effect["payload_json"], {})
        if payload.get("transfer_used"):
            raise ValueError("Экстренное пополнение по этому режиму уже использовано.")

        cursor = await conn.execute(
            "SELECT balance FROM government_structure_funds_v164 WHERE chat_id=? AND structure_key='reserve'",
            (int(chat_id),),
        )
        row = await cursor.fetchone()
        amount = max(0, int(row["balance"] if row else 0) // 10)
        if amount <= 0:
            raise ValueError("Резервный фонд пуст.")

        await debit_fund_locked(core, int(chat_id), "reserve", amount)
        await conn.execute(
            "UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?",
            (amount, now, int(chat_id)),
        )
        payload["transfer_used"] = True
        payload["transfer_actor_id"] = int(actor_id)
        payload["transfer_amount"] = amount
        payload["transfer_at"] = now
        await conn.execute(
            "UPDATE government_program_effects_v177 SET payload_json=? WHERE effect_id=?",
            (json.dumps(payload, ensure_ascii=False), str(effect["effect_id"])),
        )
        await conn.commit()

    await gov._publish(
        bot,
        int(chat_id),
        "🚑 <b>ЭКСТРЕННАЯ СТАБИЛИЗАЦИЯ</b>\n\n"
        f"Из Резервного фонда в свободную казну переведено <b>{fmt(amount)}</b> влияния.",
    )
    return f"Свободная казна экстренно пополнена на {fmt(amount)}."


async def _ensure_property_owner_trigger(core: Any) -> None:
    conn = core.db._require_connection()
    await conn.execute(
        """CREATE TRIGGER IF NOT EXISTS government_property_primary_owner_guard_v177
        AFTER UPDATE OF owner_id ON government_property_v176
        WHEN OLD.owner_id <> NEW.owner_id
        BEGIN
          UPDATE government_property_meta_v177
          SET is_primary=0,updated_at=CAST(strftime('%s','now') AS INTEGER)
          WHERE property_id=NEW.property_id;
        END"""
    )
    await conn.commit()


def install_government_reality_v177_safety(core: Any) -> None:
    if getattr(core, "_government_reality_v177_safety_installed", False):
        return
    core._government_reality_v177_safety_installed = True

    programs.emergency_transfer = emergency_transfer_safe
    integration.emergency_transfer = emergency_transfer_safe
    api.emergency_transfer = emergency_transfer_safe

    original_connect = core.Database.connect

    async def connect_with_reality177_safety(self: Any) -> None:
        await original_connect(self)
        await _ensure_property_owner_trigger(core)

    core.Database.connect = connect_with_reality177_safety
