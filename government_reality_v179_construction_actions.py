from __future__ import annotations

import secrets
from typing import Any

import government_reality_v177_funds as fund_bridge
import government_v127 as gov

from government_reality_v179_common import BUILDINGS, SOURCE_TITLES, ensure_schema
from government_reality_v179_construction_core import (
    _can_propose, _log, _start_if_ready_locked, debit_source_locked,
)


async def contribute_project(core: Any, chat_id: int, user_id: int, data: dict[str, Any]) -> str:
    await ensure_schema(core)
    await fund_bridge.migrate_funds(core)
    project_id = str(data.get("project_id") or "")
    amount = gov._as_int(data.get("amount"))
    request_id = str(data.get("request_id") or "").strip() or secrets.token_urlsafe(16)
    if amount < 100:
        raise ValueError("Минимальный вклад в строительство — 100 влияния.")
    conn = core.db._require_connection()
    async with core.db.lock:
        try:
            cursor = await conn.execute(
                "SELECT amount FROM government_construction_contributions_v179 WHERE request_id=?",
                (request_id,),
            )
            prior = await cursor.fetchone()
            if prior is not None:
                return f"Вклад {gov._fmt(int(prior['amount']))} уже учтён."
            cursor = await conn.execute(
                "SELECT * FROM government_construction_projects_v179 WHERE project_id=? AND chat_id=?",
                (project_id, int(chat_id)),
            )
            project = await cursor.fetchone()
            if project is None or str(project["status"]) != "awaiting_funding":
                raise ValueError("Вклады доступны только в утверждённый проект, ожидающий финансирования.")
            remaining = max(0, int(project["total_cost"]) - int(project["funded_amount"]))
            value = min(int(amount), remaining)
            if value <= 0:
                raise ValueError("Проект уже полностью профинансирован.")
            cursor = await conn.execute(
                """UPDATE players SET points=points-?,updated_at=?
                WHERE chat_id=? AND user_id=? AND points>=?""",
                (value, gov._now(), int(chat_id), int(user_id), value),
            )
            if int(cursor.rowcount or 0) <= 0:
                cursor = await conn.execute("SELECT points FROM players WHERE chat_id=? AND user_id=?", (int(chat_id), int(user_id)))
                row = await cursor.fetchone()
                raise ValueError(f"Недостаточно влияния. Твой баланс: {gov._fmt(int(row['points'] if row else 0))}.")
            score = max(1, value // 1000)
            await conn.execute(
                """INSERT INTO government_construction_contributions_v179(
                contribution_id,project_id,chat_id,user_id,amount,score,request_id,created_at)
                VALUES(?,?,?,?,?,?,?,?)""",
                (secrets.token_urlsafe(12), project_id, int(chat_id), int(user_id), value, score, request_id, gov._now()),
            )
            await conn.execute(
                """INSERT INTO government_construction_scores_v179(chat_id,user_id,score,amount,updated_at)
                VALUES(?,?,?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET
                score=government_construction_scores_v179.score+excluded.score,
                amount=government_construction_scores_v179.amount+excluded.amount,updated_at=excluded.updated_at""",
                (int(chat_id), int(user_id), score, value, gov._now()),
            )
            await conn.execute(
                "UPDATE government_construction_projects_v179 SET funded_amount=funded_amount+?,updated_at=? WHERE project_id=?",
                (value, gov._now(), project_id),
            )
            await _log(core, int(chat_id), "public_contribution", "Добровольный вклад в строительство", project_id=project_id, actor_id=int(user_id), amount=value)
            await _start_if_ready_locked(core, project_id)
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    return f"В строительство внесено {gov._fmt(value)} влияния. Начислено {score} строительных очков."


async def fund_project(core: Any, chat_id: int, actor_id: int, data: dict[str, Any]) -> str:
    await ensure_schema(core)
    await fund_bridge.migrate_funds(core)
    project_id = str(data.get("project_id") or "")
    source_key = str(data.get("source_key") or "")
    requested = gov._as_int(data.get("amount"))
    request_id = str(data.get("request_id") or "").strip() or secrets.token_urlsafe(16)
    conn = core.db._require_connection()
    cursor = await conn.execute("SELECT * FROM government_construction_projects_v179 WHERE project_id=? AND chat_id=?", (project_id, int(chat_id)))
    project = await cursor.fetchone()
    if project is None or str(project["status"]) != "awaiting_funding":
        raise ValueError("Проект сейчас не принимает финансирование.")
    spec = BUILDINGS[str(project["building_key"])]
    if source_key not in spec["sources"]:
        raise ValueError("Этот источник не разрешён для объекта.")
    await _can_propose(core, int(chat_id), int(actor_id), source_key)
    remaining = max(0, int(project["total_cost"]) - int(project["funded_amount"]))
    amount = min(requested if requested > 0 else remaining, remaining)
    if amount <= 0:
        raise ValueError("Проект уже полностью профинансирован.")
    async with core.db.lock:
        try:
            cursor = await conn.execute("SELECT amount FROM government_construction_funding_v179 WHERE request_id=?", (request_id,))
            prior = await cursor.fetchone()
            if prior is not None:
                return f"Финансирование {gov._fmt(int(prior['amount']))} уже учтено."
            cursor = await conn.execute("SELECT * FROM government_construction_projects_v179 WHERE project_id=? AND chat_id=?", (project_id, int(chat_id)))
            locked_project = await cursor.fetchone()
            if locked_project is None or str(locked_project["status"]) != "awaiting_funding":
                raise ValueError("Проект уже изменил состояние.")
            locked_remaining = max(0, int(locked_project["total_cost"]) - int(locked_project["funded_amount"]))
            amount = min(amount, locked_remaining)
            if amount <= 0:
                raise ValueError("Проект уже полностью профинансирован.")
            await debit_source_locked(core, int(chat_id), source_key, amount)
            await conn.execute(
                """INSERT INTO government_construction_funding_v179(
                funding_id,project_id,chat_id,source_type,source_key,actor_id,amount,request_id,created_at)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (secrets.token_urlsafe(12), project_id, int(chat_id), "government", source_key, int(actor_id), amount, request_id, gov._now()),
            )
            await conn.execute("UPDATE government_construction_projects_v179 SET funded_amount=funded_amount+?,updated_at=? WHERE project_id=?", (amount, gov._now(), project_id))
            await _log(core, int(chat_id), "government_funding", f"Финансирование из {SOURCE_TITLES[source_key]}", project_id=project_id, actor_id=int(actor_id), amount=amount)
            await _start_if_ready_locked(core, project_id)
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    return f"На проект направлено {gov._fmt(amount)} влияния."


async def pay_building_debt(core: Any, chat_id: int, actor_id: int, data: dict[str, Any]) -> str:
    await ensure_schema(core)
    building_id = str(data.get("building_id") or "")
    source_key = str(data.get("source_key") or "")
    await _can_propose(core, int(chat_id), int(actor_id), source_key)
    conn = core.db._require_connection()
    async with core.db.lock:
        try:
            cursor = await conn.execute("SELECT * FROM government_buildings_v179 WHERE building_id=? AND chat_id=?", (building_id, int(chat_id)))
            building = await cursor.fetchone()
            if building is None or int(building["maintenance_debt"] or 0) <= 0:
                raise ValueError("У объекта нет долга по содержанию.")
            spec = BUILDINGS[str(building["building_key"])]
            if source_key not in spec["sources"]:
                raise ValueError("Этот источник нельзя использовать для содержания объекта.")
            amount = int(building["maintenance_debt"])
            await debit_source_locked(core, int(chat_id), source_key, amount)
            await conn.execute("UPDATE government_buildings_v179 SET maintenance_debt=0,status='active',updated_at=? WHERE building_id=?", (gov._now(), building_id))
            await conn.execute("DELETE FROM government_building_debts_v179 WHERE building_id=?", (building_id,))
            await conn.execute("UPDATE government_building_effects_v179 SET active=1,updated_at=? WHERE building_id=?", (gov._now(), building_id))
            await _log(core, int(chat_id), "maintenance_debt_paid", "Погашен долг содержания", building_id=building_id, actor_id=int(actor_id), amount=amount)
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    return f"Долг объекта погашен: {gov._fmt(amount)} влияния."
