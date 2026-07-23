from __future__ import annotations

import asyncio
from typing import Any

import government_treasury_contributions_v150 as contributions
import government_treasury_management_v164 as treasury
import government_v127 as gov

import government_programs_property_v176_programs as original_programs
import government_programs_property_v176_state as original_state
from government_programs_property_v176_common import PROGRAMS, _program_cost, ensure_schema


# Reality 150 funds visible in the current Treasury screen.
LEGACY_FUND_BY_PROGRAM: dict[str, str] = {
    "anti_crisis": "reserve",
    "festival": "development",
    "social_help": "social",
    "oversight_operation": "security",
    "market_intervention": "general",
    "election_campaign": "elections",
}

_PROGRAM_RUN_LOCK = asyncio.Lock()


def _available_balance(structure_balance: int, legacy_balance: int, treasury_balance: int) -> int:
    """Count dedicated money plus the part of the old earmark backed by the treasury."""
    structure = max(0, int(structure_balance))
    legacy = max(0, int(legacy_balance))
    treasury_cash = max(0, int(treasury_balance))
    return structure + min(legacy, treasury_cash)


def _required_transfer(
    cost: int,
    structure_balance: int,
    legacy_balance: int,
    treasury_balance: int,
) -> int:
    value = max(0, int(cost))
    structure = max(0, int(structure_balance))
    available = _available_balance(structure, legacy_balance, treasury_balance)
    if available < value:
        raise ValueError("В фонде недостаточно средств.")
    return max(0, value - structure)


def _source_title(program_key: str, structure_balance: int, legacy_balance: int) -> str:
    structure_title = str(treasury.STRUCTURES[str(PROGRAMS[program_key]["fund_key"])]["title"])
    legacy_title = str(contributions.FUND_SPECS[LEGACY_FUND_BY_PROGRAM[program_key]]["title"])
    if int(structure_balance) > 0 and int(legacy_balance) > 0 and structure_title != legacy_title:
        return f"{structure_title} + {legacy_title}"
    return legacy_title if int(legacy_balance) > 0 else structure_title


async def _balances(core: Any, chat_id: int) -> tuple[dict[str, int], dict[str, int], int]:
    await ensure_schema(core)
    await treasury._ensure_schema(core)
    await contributions._ensure_schema(core)
    state = await gov._ensure_state(core, int(chat_id))
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT structure_key,balance FROM government_structure_funds_v164 WHERE chat_id=?",
        (int(chat_id),),
    )
    structures = {str(row["structure_key"]): int(row["balance"] or 0) for row in await cursor.fetchall()}
    cursor = await conn.execute(
        "SELECT fund_key,amount FROM government_fund_balances_v150 WHERE chat_id=?",
        (int(chat_id),),
    )
    legacy = {str(row["fund_key"]): int(row["amount"] or 0) for row in await cursor.fetchall()}
    return structures, legacy, int(state["treasury"] if state else 0)


async def programs_state(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    payload = await original_state.programs_state(core, int(chat_id), int(user_id))
    structures, legacy, treasury_balance = await _balances(core, int(chat_id))
    cards = {str(item.get("key")): item for item in payload.get("programs", [])}
    for program_key, spec in PROGRAMS.items():
        card = cards.get(program_key)
        if card is None:
            continue
        structure_balance = structures.get(str(spec["fund_key"]), 0)
        legacy_balance = min(
            legacy.get(LEGACY_FUND_BY_PROGRAM[program_key], 0),
            max(0, treasury_balance),
        )
        balance = _available_balance(structure_balance, legacy_balance, treasury_balance)
        card["fund_balance"] = balance
        card["fund_title"] = _source_title(program_key, structure_balance, legacy_balance)
        card["calculated_cost"] = _program_cost(
            program_key,
            balance,
            int(spec["min_cost"]),
        )
        card["fund_sources"] = {
            "structure": structure_balance,
            "legacy": legacy_balance,
            "legacy_key": LEGACY_FUND_BY_PROGRAM[program_key],
        }
    return payload


async def _bridge_needed_money(
    core: Any,
    chat_id: int,
    program_key: str,
    requested_amount: int,
) -> tuple[int, int]:
    """Move only the missing amount and return (moved, exact program cost)."""
    structures, legacy, treasury_balance = await _balances(core, int(chat_id))
    spec = PROGRAMS[program_key]
    structure_key = str(spec["fund_key"])
    legacy_key = LEGACY_FUND_BY_PROGRAM[program_key]
    structure_balance = structures.get(structure_key, 0)
    legacy_balance = legacy.get(legacy_key, 0)
    available = _available_balance(structure_balance, legacy_balance, treasury_balance)
    cost = _program_cost(program_key, available, int(requested_amount))
    if cost <= 0 or available < cost:
        raise ValueError(
            f"В фонде недостаточно средств. Требуется {gov._fmt(cost)}, доступно {gov._fmt(available)}."
        )
    transfer = max(0, cost - max(0, structure_balance))
    if transfer <= 0:
        return 0, cost

    conn = core.db._require_connection()
    now = gov._now()
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT balance FROM government_structure_funds_v164 WHERE chat_id=? AND structure_key=?",
            (int(chat_id), structure_key),
        )
        structure_row = await cursor.fetchone()
        cursor = await conn.execute(
            "SELECT amount FROM government_fund_balances_v150 WHERE chat_id=? AND fund_key=?",
            (int(chat_id), legacy_key),
        )
        legacy_row = await cursor.fetchone()
        cursor = await conn.execute(
            "SELECT treasury FROM government_state_v127 WHERE chat_id=?",
            (int(chat_id),),
        )
        state_row = await cursor.fetchone()
        current_structure = int(structure_row["balance"] if structure_row else 0)
        current_legacy = int(legacy_row["amount"] if legacy_row else 0)
        current_treasury = int(state_row["treasury"] if state_row else 0)
        current_available = _available_balance(current_structure, current_legacy, current_treasury)
        current_cost = _program_cost(program_key, current_available, int(requested_amount))
        transfer = _required_transfer(
            current_cost, current_structure, current_legacy, current_treasury
        )
        if current_available < current_cost or current_legacy < transfer or current_treasury < transfer:
            raise ValueError("Баланс фонда изменился: средств уже недостаточно.")
        if transfer <= 0:
            return 0, current_cost
        await conn.execute(
            "UPDATE government_fund_balances_v150 SET amount=amount-?,updated_at=? WHERE chat_id=? AND fund_key=?",
            (transfer, now, int(chat_id), legacy_key),
        )
        await conn.execute(
            "UPDATE government_state_v127 SET treasury=treasury-?,updated_at=? WHERE chat_id=?",
            (transfer, now, int(chat_id)),
        )
        await conn.execute(
            """
            INSERT INTO government_structure_funds_v164(chat_id,structure_key,balance,updated_at)
            VALUES(?,?,?,?)
            ON CONFLICT(chat_id,structure_key) DO UPDATE SET
              balance=government_structure_funds_v164.balance+excluded.balance,
              updated_at=excluded.updated_at
            """,
            (int(chat_id), structure_key, transfer, now),
        )
        await conn.commit()
    return transfer, current_cost


async def _restore_bridge_money(
    core: Any,
    chat_id: int,
    program_key: str,
    amount: int,
) -> None:
    value = max(0, int(amount))
    if value <= 0:
        return
    spec = PROGRAMS[program_key]
    structure_key = str(spec["fund_key"])
    legacy_key = LEGACY_FUND_BY_PROGRAM[program_key]
    conn = core.db._require_connection()
    now = gov._now()
    async with core.db.lock:
        await conn.rollback()
        cursor = await conn.execute(
            "SELECT balance FROM government_structure_funds_v164 WHERE chat_id=? AND structure_key=?",
            (int(chat_id), structure_key),
        )
        row = await cursor.fetchone()
        if row is None or int(row["balance"] or 0) < value:
            return
        await conn.execute(
            "UPDATE government_structure_funds_v164 SET balance=balance-?,updated_at=? WHERE chat_id=? AND structure_key=?",
            (value, now, int(chat_id), structure_key),
        )
        await conn.execute(
            """
            INSERT INTO government_fund_balances_v150(chat_id,fund_key,amount,updated_at)
            VALUES(?,?,?,?)
            ON CONFLICT(chat_id,fund_key) DO UPDATE SET
              amount=government_fund_balances_v150.amount+excluded.amount,
              updated_at=excluded.updated_at
            """,
            (int(chat_id), legacy_key, value, now),
        )
        await conn.execute(
            "UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?",
            (value, now, int(chat_id)),
        )
        await conn.commit()


async def run_program(core: Any, bot: Any, chat_id: int, actor_id: int, data: dict[str, Any]) -> str:
    program_key = str(data.get("program_key") or "")
    spec = PROGRAMS.get(program_key)
    if spec is None:
        raise ValueError("Неизвестная государственная программа.")
    offices = await gov._user_offices(core, int(chat_id), int(actor_id))
    is_admin = int(actor_id) == int(core.DEVELOPER_ID)
    if not (is_admin or set(offices).intersection(spec["roles"])):
        raise PermissionError("У вашей должности нет права запускать эту программу.")
    if await gov._has_active_sanctions(core, int(chat_id), int(actor_id)) and not is_admin:
        raise PermissionError("Чиновник с активными санкциями не может расходовать фонд.")

    requested = gov._as_int(data.get("amount"), int(spec["min_cost"]))
    async with _PROGRAM_RUN_LOCK:
        moved, target_cost = await _bridge_needed_money(
            core, int(chat_id), program_key, requested
        )
        original_cost = original_programs._program_cost

        def fixed_cost(key: str, balance: int, requested_value: int = 0) -> int:
            if str(key) == program_key:
                return int(target_cost)
            return int(original_cost(key, balance, requested_value))

        original_programs._program_cost = fixed_cost
        try:
            return await original_programs.run_program(
                core,
                bot,
                int(chat_id),
                int(actor_id),
                data,
            )
        except Exception:
            await _restore_bridge_money(core, int(chat_id), program_key, moved)
            raise
        finally:
            original_programs._program_cost = original_cost


apply_anti_crisis = original_programs.apply_anti_crisis
process_expired_effects = original_programs.process_expired_effects
expanded_oversight_report = original_programs.expanded_oversight_report
