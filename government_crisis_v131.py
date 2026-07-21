from __future__ import annotations

import asyncio
import html
import json
import math
import secrets
import time
from pathlib import Path
from typing import Any

import government_institutions_v128 as institutions
import government_v127 as gov
import hierarchy_v130 as hierarchy
import sanctions_v126 as sanctions


VERSION = "Reality 131 · Казнокрадство и перевороты"
APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "crisis-v131.js"
ASSET_CSS = APP_DIR / "crisis-v131.css"
THEFT_COOLDOWN = 5 * 60 * 60
THEFT_INVESTIGATION_WINDOW = 2 * 60 * 60
MILITIA_GATHERING = 6 * 60 * 60
MILITIA_BATTLE = 30 * 60
COUP_RECRUITING = 6 * 60 * 60
COUP_PREPARATION = 6 * 60 * 60
COUP_ACTION_COOLDOWN = 30 * 60
MILITIA_ACTION_COOLDOWN = 2 * 60
COUNCIL_TERM = 12 * 60 * 60
_RUNTIME_STARTED = False

THEFT_RULES: dict[int, tuple[int, int]] = {
    5: (80, 20),
    10: (60, 40),
    20: (35, 65),
    35: (15, 85),
}
INVESTIGATION_CHANCES = {
    "auditor": 55,
    "prosecutor": 50,
    "oversight": 45,
    "finance": 35,
    "security": 30,
    "central_bank": 25,
    "president": 20,
}
INVESTIGATOR_OFFICES = tuple(INVESTIGATION_CHANCES)
COUP_ELIGIBLE_OFFICES = {
    "chair", "deputy", "finance", "oversight", "supreme_court", "prosecutor",
    "central_bank", "auditor", "cec", "ombudsman", "security", "press",
}
APPOINTED_OFFICES = {
    "finance", "oversight", "supreme_court", "prosecutor", "central_bank",
    "auditor", "cec", "ombudsman", "security", "press",
}


def _now() -> int:
    return int(time.time())


def _fmt(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _json(value: Any, default: Any) -> Any:
    if isinstance(value, type(default)):
        return value
    try:
        parsed = json.loads(str(value or ""))
        return parsed if isinstance(parsed, type(default)) else default
    except Exception:
        return default


def _remaining(timestamp: int) -> str:
    return gov._remaining(int(timestamp or 0))


async def _ensure_schema(core: Any) -> None:
    if getattr(core, "_government_crisis_v131_schema_ready", False):
        return
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS government_thefts_v131(
                theft_id TEXT PRIMARY KEY,chat_id INTEGER NOT NULL,thief_id INTEGER NOT NULL,
                percent INTEGER NOT NULL,amount INTEGER NOT NULL,status TEXT NOT NULL,
                success_chance INTEGER NOT NULL,detection_risk INTEGER NOT NULL,
                sabotage_bonus INTEGER NOT NULL DEFAULT 0,investigations INTEGER NOT NULL DEFAULT 0,
                started_at INTEGER NOT NULL,resolve_at INTEGER NOT NULL,caught_by INTEGER NOT NULL DEFAULT 0,
                caught_at INTEGER NOT NULL DEFAULT 0,resolved_at INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_thefts_chat_v131
            ON government_thefts_v131(chat_id,status,started_at DESC);
            CREATE TABLE IF NOT EXISTS government_theft_cooldowns_v131(
                chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,next_at INTEGER NOT NULL,
                PRIMARY KEY(chat_id,user_id)
            );
            CREATE TABLE IF NOT EXISTS government_theft_investigations_v131(
                theft_id TEXT NOT NULL,investigator_id INTEGER NOT NULL,office_key TEXT NOT NULL,
                chance INTEGER NOT NULL,roll INTEGER NOT NULL,success INTEGER NOT NULL,
                created_at INTEGER NOT NULL,PRIMARY KEY(theft_id,investigator_id)
            );
            CREATE TABLE IF NOT EXISTS government_election_bans_v131(
                chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,until_at INTEGER NOT NULL,
                reason TEXT NOT NULL,created_at INTEGER NOT NULL,PRIMARY KEY(chat_id,user_id)
            );
            CREATE TABLE IF NOT EXISTS government_conflict_bans_v131(
                chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,until_at INTEGER NOT NULL,
                reason TEXT NOT NULL,created_at INTEGER NOT NULL,PRIMARY KEY(chat_id,user_id)
            );
            CREATE TABLE IF NOT EXISTS government_conflicts_v131(
                conflict_id TEXT PRIMARY KEY,chat_id INTEGER NOT NULL,conflict_type TEXT NOT NULL,
                target_office TEXT NOT NULL,target_seat INTEGER NOT NULL DEFAULT 1,
                target_user_id INTEGER NOT NULL,created_by INTEGER NOT NULL,stage TEXT NOT NULL,
                reason TEXT NOT NULL,threshold INTEGER NOT NULL DEFAULT 0,
                militia_score INTEGER NOT NULL DEFAULT 0,loyalist_score INTEGER NOT NULL DEFAULT 0,
                plot_score INTEGER NOT NULL DEFAULT 0,defense_score INTEGER NOT NULL DEFAULT 0,
                started_at INTEGER NOT NULL,stage_ends_at INTEGER NOT NULL,
                outcome TEXT NOT NULL DEFAULT '',payload_json TEXT NOT NULL DEFAULT '{}',
                resolved_at INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_conflicts_chat_v131
            ON government_conflicts_v131(chat_id,stage,started_at DESC);
            CREATE TABLE IF NOT EXISTS government_conflict_members_v131(
                conflict_id TEXT NOT NULL,user_id INTEGER NOT NULL,side TEXT NOT NULL,
                status TEXT NOT NULL,role_key TEXT NOT NULL DEFAULT '',points INTEGER NOT NULL DEFAULT 0,
                last_action_at INTEGER NOT NULL DEFAULT 0,invited_by INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,PRIMARY KEY(conflict_id,user_id)
            );
            CREATE TABLE IF NOT EXISTS government_council_v131(
                chat_id INTEGER PRIMARY KEY,conflict_id TEXT NOT NULL,members_json TEXT NOT NULL,
                until_at INTEGER NOT NULL,election_called INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );
            """
        )
        await conn.commit()
    core._government_crisis_v131_schema_ready = True


async def _player(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    player = await gov._player_dict(core, int(chat_id), int(user_id))
    if player is None:
        raise ValueError("Участник не найден в этой беседе.")
    return player


async def _name(core: Any, chat_id: int, user_id: int) -> str:
    player = await gov._player_dict(core, int(chat_id), int(user_id))
    return str(player["name"] if player else f"ID {int(user_id)}")


async def _is_sabotage_hero(core: Any, chat_id: int, user_id: int) -> bool:
    try:
        return await core.db.get_active_sabotage_for_usurper(int(chat_id), int(user_id)) is not None
    except Exception:
        return False


async def _offices(core: Any, chat_id: int, user_id: int) -> list[str]:
    return await gov._user_offices(core, int(chat_id), int(user_id))


async def _office_holder(core: Any, chat_id: int, office_key: str, seat_no: int = 1) -> Any | None:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_offices_v127 WHERE chat_id=? AND office_key=? AND seat_no=? AND ends_at>?",
        (int(chat_id), str(office_key), int(seat_no), _now()),
    )
    return await cursor.fetchone()


async def _treasury(core: Any, chat_id: int) -> int:
    state = await gov._ensure_state(core, int(chat_id))
    return int(state["treasury"] or 0)


async def _active_conflict(core: Any, chat_id: int) -> Any | None:
    await _ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_conflicts_v131 WHERE chat_id=? AND stage NOT IN ('resolved','failed','cancelled') ORDER BY started_at DESC LIMIT 1",
        (int(chat_id),),
    )
    return await cursor.fetchone()


async def _ban_until(core: Any, table: str, chat_id: int, user_id: int) -> int:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        f"SELECT until_at FROM {table} WHERE chat_id=? AND user_id=? AND until_at>?",
        (int(chat_id), int(user_id), _now()),
    )
    row = await cursor.fetchone()
    return int(row["until_at"] or 0) if row else 0


async def _set_ban(core: Any, table: str, chat_id: int, user_id: int, seconds: int, reason: str) -> None:
    conn = core.db._require_connection()
    now = _now()
    await conn.execute(
        f"""INSERT INTO {table}(chat_id,user_id,until_at,reason,created_at)
            VALUES(?,?,?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET
            until_at=MAX({table}.until_at,excluded.until_at),reason=excluded.reason,created_at=excluded.created_at""",
        (int(chat_id), int(user_id), now + int(seconds), str(reason), now),
    )
    await conn.commit()


async def _remove_offices(core: Any, chat_id: int, user_id: int, only_office: str = "", seat_no: int = 0) -> list[str]:
    conn = core.db._require_connection()
    now = _now()
    if only_office:
        cursor = await conn.execute(
            "SELECT office_key FROM government_offices_v127 WHERE chat_id=? AND user_id=? AND office_key=? AND (?=0 OR seat_no=?) AND ends_at>?",
            (int(chat_id), int(user_id), str(only_office), int(seat_no), int(seat_no), now),
        )
        removed = [str(row["office_key"]) for row in await cursor.fetchall()]
        await conn.execute(
            "DELETE FROM government_offices_v127 WHERE chat_id=? AND user_id=? AND office_key=? AND (?=0 OR seat_no=?) AND ends_at>?",
            (int(chat_id), int(user_id), str(only_office), int(seat_no), int(seat_no), now),
        )
    else:
        cursor = await conn.execute(
            "SELECT office_key FROM government_offices_v127 WHERE chat_id=? AND user_id=? AND ends_at>?",
            (int(chat_id), int(user_id), now),
        )
        removed = [str(row["office_key"]) for row in await cursor.fetchall()]
        await conn.execute(
            "DELETE FROM government_offices_v127 WHERE chat_id=? AND user_id=? AND ends_at>?",
            (int(chat_id), int(user_id), now),
        )
    await conn.commit()
    return removed


async def _issue_finance_sanction(core: Any, bot: Any, chat_id: int, user_id: int, duration: int, reason: str) -> None:
    try:
        types, expires_at = await sanctions.issue_sanctions(
            core, int(chat_id), int(user_id), ["finance"], int(duration), str(reason), int(core.DEVELOPER_ID)
        )
        await sanctions.send_issue_notice(core, bot, int(chat_id), int(user_id), types, int(duration), str(reason), expires_at)
    except Exception:
        core.logging.exception("Не удалось применить финансовую санкцию Reality 131")


async def _punish_points(core: Any, chat_id: int, user_id: int, amount: int, reason: str) -> int:
    conn = core.db._require_connection()
    player = await _player(core, chat_id, user_id)
    fine = min(max(0, int(player["points"])), max(0, int(amount)))
    if fine <= 0:
        return 0
    now = _now()
    async with core.db.lock:
        cursor = await conn.execute(
            "UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=? AND points>=?",
            (fine, now, int(chat_id), int(user_id), fine),
        )
        if int(cursor.rowcount or 0) <= 0:
            await conn.rollback()
            return 0
        await conn.execute(
            "UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?",
            (fine, now, int(chat_id)),
        )
        await conn.execute(
            "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
            (int(chat_id), int(user_id), -fine, str(reason), now),
        )
        await gov._treasury_log(core, chat_id, fine, "Конфискация в пользу казны", "confiscation_v131", str(user_id), int(core.DEVELOPER_ID))
        await conn.commit()
    return fine


async def _catch_theft(core: Any, bot: Any, theft: Any, investigator_id: int, immediate: bool = False) -> None:
    theft_id = str(theft["theft_id"])
    chat_id = int(theft["chat_id"])
    thief_id = int(theft["thief_id"])
    amount = int(theft["amount"])
    conn = core.db._require_connection()
    now = _now()
    async with core.db.lock:
        cursor = await conn.execute(
            "UPDATE government_thefts_v131 SET status='caught',caught_by=?,caught_at=?,resolved_at=? WHERE theft_id=? AND status IN ('pending','attempt_failed')",
            (int(investigator_id), now, now, theft_id),
        )
        if int(cursor.rowcount or 0) <= 0:
            await conn.rollback()
            return
        if str(theft["status"]) == "pending":
            await conn.execute(
                "UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?",
                (amount, now, chat_id),
            )
            await gov._treasury_log(core, chat_id, amount, "Возврат похищенных средств", "theft_recovery_v131", theft_id, int(investigator_id))
        await conn.commit()
    fine = await _punish_points(core, chat_id, thief_id, max(100, amount // 2), "treasury_theft_fine_v131")
    removed = await _remove_offices(core, chat_id, thief_id)
    await _set_ban(core, "government_election_bans_v131", chat_id, thief_id, 24 * 60 * 60, "Казнокрадство")
    await _issue_finance_sanction(core, bot, chat_id, thief_id, 24 * 60 * 60, "Попытка хищения государственной казны")
    thief_name = await _name(core, chat_id, thief_id)
    await gov._publish(
        bot,
        chat_id,
        "🚨 <b>КАЗНОКРАД ПОЙМАН</b>\n\n"
        f"Виновник: <b>{html.escape(thief_name)}</b>\n"
        f"Сумма: <b>{_fmt(amount)}</b> влияния\n"
        f"Возвращено в казну: <b>{_fmt(amount if str(theft['status']) == 'pending' else 0)}</b>\n"
        f"Штраф: <b>{_fmt(fine)}</b>\n"
        f"Снятые должности: <b>{html.escape(', '.join(removed) if removed else 'нет')}</b>\n\n"
        "Участник отстранён от выборов на 24 часа.\n\n"
        "🏛 <b>Решение принято Надзором за гандонами.</b>",
    )


async def _start_theft(core: Any, bot: Any, chat_id: int, user_id: int, percent: int) -> str:
    await _ensure_schema(core)
    if int(percent) not in THEFT_RULES:
        raise ValueError("Можно попытаться украсть 5%, 10%, 20% или 35% казны.")
    if await sanctions.blocking_sanction(core, chat_id, user_id, "finance"):
        raise PermissionError("Финансовые санкции запрещают операции с казной.")
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT next_at FROM government_theft_cooldowns_v131 WHERE chat_id=? AND user_id=?",
        (int(chat_id), int(user_id)),
    )
    cooldown = await cursor.fetchone()
    if cooldown and int(cooldown["next_at"]) > _now():
        raise ValueError(f"Следующая попытка доступна через {_remaining(int(cooldown['next_at']))}.")
    cursor = await conn.execute(
        "SELECT 1 FROM government_thefts_v131 WHERE chat_id=? AND thief_id=? AND status='pending' LIMIT 1",
        (int(chat_id), int(user_id)),
    )
    if await cursor.fetchone() is not None:
        raise ValueError("Предыдущая операция ещё находится под расследованием.")
    treasury = await _treasury(core, chat_id)
    if treasury < 10:
        raise ValueError("В казне почти ничего нет.")
    amount = max(1, treasury * int(percent) // 100)
    base_success, detection = THEFT_RULES[int(percent)]
    sabotage = await _is_sabotage_hero(core, chat_id, user_id)
    offices = await _offices(core, chat_id, user_id)
    sabotage_bonus = 15 if sabotage else 0
    official_penalty = 5 if offices else 0
    chance = max(5, min(95, base_success + sabotage_bonus - official_penalty))
    detection_risk = max(5, min(95, detection - sabotage_bonus + (10 if offices else 0)))
    roll = secrets.randbelow(100) + 1
    theft_id = secrets.token_urlsafe(12)
    now = _now()
    status = "pending" if roll <= chance else "attempt_failed"
    async with core.db.lock:
        await conn.execute(
            """INSERT INTO government_thefts_v131(
                 theft_id,chat_id,thief_id,percent,amount,status,success_chance,detection_risk,
                 sabotage_bonus,investigations,started_at,resolve_at,caught_by,caught_at,resolved_at
               ) VALUES(?,?,?,?,?,?,?,?,?,0,?,?,0,0,0)""",
            (theft_id, int(chat_id), int(user_id), int(percent), amount, status, chance,
             detection_risk, sabotage_bonus, now, now + THEFT_INVESTIGATION_WINDOW),
        )
        await conn.execute(
            """INSERT INTO government_theft_cooldowns_v131(chat_id,user_id,next_at)
               VALUES(?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET next_at=excluded.next_at""",
            (int(chat_id), int(user_id), now + THEFT_COOLDOWN),
        )
        if status == "pending":
            cursor = await conn.execute(
                "UPDATE government_state_v127 SET treasury=treasury-?,updated_at=? WHERE chat_id=? AND treasury>=?",
                (amount, now, int(chat_id), amount),
            )
            if int(cursor.rowcount or 0) <= 0:
                await conn.rollback()
                raise ValueError("Казна изменилась. Обнови страницу и повтори попытку.")
            await gov._treasury_log(core, chat_id, -amount, "Неустановленная операция", "suspected_theft_v131", theft_id, 0)
        await conn.commit()
    if status == "pending":
        await gov._publish(
            bot,
            chat_id,
            "🕶 <b>ПОДОЗРИТЕЛЬНАЯ ОПЕРАЦИЯ В КАЗНЕ</b>\n\n"
            f"Из казны выведено: <b>{_fmt(amount)}</b> влияния.\n"
            f"На расследование: <b>2 часа</b>.\n\n"
            "Надзор, прокуратура, Минфин и Счётная палата получили доступ к проверке.",
        )
        return "Средства выведены. Следствие получило 2 часа на поиск следов."
    cursor = await conn.execute("SELECT * FROM government_thefts_v131 WHERE theft_id=?", (theft_id,))
    row = await cursor.fetchone()
    if row is not None:
        await _catch_theft(core, bot, row, int(core.DEVELOPER_ID), immediate=True)
    return "Попытка провалилась: операция была раскрыта сразу."


async def _investigate_theft(core: Any, bot: Any, chat_id: int, user_id: int, theft_id: str) -> str:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_thefts_v131 WHERE theft_id=? AND chat_id=?",
        (str(theft_id), int(chat_id)),
    )
    theft = await cursor.fetchone()
    if theft is None or str(theft["status"]) != "pending" or int(theft["resolve_at"]) <= _now():
        raise ValueError("Эта операция уже закрыта.")
    offices = await _offices(core, chat_id, user_id)
    office = next((key for key in INVESTIGATOR_OFFICES if key in offices), "")
    if int(user_id) == int(core.DEVELOPER_ID):
        office = "auditor"
    if not office:
        raise PermissionError("Расследование доступно Надзору, прокуратуре, Минфину, Счётной палате, Совбезу и ЦБ.")
    cursor = await conn.execute(
        "SELECT 1 FROM government_theft_investigations_v131 WHERE theft_id=? AND investigator_id=?",
        (str(theft_id), int(user_id)),
    )
    if await cursor.fetchone() is not None:
        raise ValueError("Ты уже проводил проверку этой операции.")
    prior = int(theft["investigations"] or 0)
    sabotage = int(theft["sabotage_bonus"] or 0)
    chance = max(5, min(95, INVESTIGATION_CHANCES.get(office, 20) + prior * 5 - sabotage))
    roll = secrets.randbelow(100) + 1
    success = roll <= chance
    now = _now()
    await conn.execute(
        "INSERT INTO government_theft_investigations_v131(theft_id,investigator_id,office_key,chance,roll,success,created_at) VALUES(?,?,?,?,?,?,?)",
        (str(theft_id), int(user_id), office, chance, roll, 1 if success else 0, now),
    )
    await conn.execute(
        "UPDATE government_thefts_v131 SET investigations=investigations+1 WHERE theft_id=?",
        (str(theft_id),),
    )
    await conn.commit()
    if success:
        await _catch_theft(core, bot, theft, user_id)
        return "Следы найдены. Виновник раскрыт, деньги возвращены."
    return "Проверка завершена, но доказательств пока недостаточно."


async def _resolve_theft(core: Any, bot: Any, theft: Any) -> None:
    theft_id = str(theft["theft_id"])
    chat_id = int(theft["chat_id"])
    thief_id = int(theft["thief_id"])
    amount = int(theft["amount"])
    conn = core.db._require_connection()
    now = _now()
    async with core.db.lock:
        cursor = await conn.execute(
            "UPDATE government_thefts_v131 SET status='escaped',resolved_at=? WHERE theft_id=? AND status='pending'",
            (now, theft_id),
        )
        if int(cursor.rowcount or 0) <= 0:
            await conn.rollback()
            return
        await conn.execute(
            "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
            (amount, now, chat_id, thief_id),
        )
        await conn.execute(
            "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
            (chat_id, thief_id, amount, "treasury_theft_v131", now),
        )
        await conn.commit()
    await gov._publish(
        bot,
        chat_id,
        "🕶 <b>РАССЛЕДОВАНИЕ ОПЕРАЦИИ ЗАВЕРШЕНО</b>\n\n"
        f"Следствию не удалось установить виновника.\n"
        f"Потеря казны: <b>{_fmt(amount)}</b> влияния.",
    )


async def _militia_threshold(core: Any, chat_id: int) -> tuple[int, int]:
    active = max(1, int(await hierarchy.active_user_count(core, int(chat_id))))
    return active, max(2, int(math.ceil(active / 2)))


async def _create_militia(core: Any, bot: Any, chat_id: int, user_id: int, office_key: str, seat_no: int, reason: str) -> str:
    if await _active_conflict(core, chat_id) or await _council(core, chat_id):
        raise ValueError("В беседе уже идёт политический конфликт или действует Революционный совет.")
    ban = await _ban_until(core, "government_conflict_bans_v131", chat_id, user_id)
    if ban:
        raise PermissionError(f"Новый конфликт доступен через {_remaining(ban)}.")
    holder = await _office_holder(core, chat_id, office_key, seat_no)
    if holder is None:
        raise ValueError("Выбранная должность сейчас свободна.")
    target_id = int(holder["user_id"])
    if target_id == int(user_id):
        raise ValueError("Нельзя создавать ополчение против самого себя.")
    clean = str(reason or "").strip()
    if len(clean) < 10 or len(clean) > 600:
        raise ValueError("Причина должна содержать от 10 до 600 символов.")
    active, threshold = await _militia_threshold(core, chat_id)
    conflict_id = secrets.token_urlsafe(12)
    now = _now()
    conn = core.db._require_connection()
    await conn.execute(
        """INSERT INTO government_conflicts_v131(
             conflict_id,chat_id,conflict_type,target_office,target_seat,target_user_id,
             created_by,stage,reason,threshold,started_at,stage_ends_at
           ) VALUES(?,?,?,?,?,?,?,'gathering',?,?,?,?)""",
        (conflict_id, int(chat_id), "militia", str(office_key), int(seat_no), target_id,
         int(user_id), clean, threshold, now, now + MILITIA_GATHERING),
    )
    await conn.execute(
        "INSERT INTO government_conflict_members_v131(conflict_id,user_id,side,status,role_key,points,last_action_at,invited_by,created_at) VALUES(?,?,'militia','accepted','leader',0,0,0,?)",
        (conflict_id, int(user_id), now),
    )
    await conn.commit()
    target_name = await _name(core, chat_id, target_id)
    title = gov.OFFICES.get(str(office_key), {"title": office_key})["title"]
    await gov._publish(
        bot,
        chat_id,
        "🔥 <b>СОЗДАНО НАРОДНОЕ ОПОЛЧЕНИЕ</b>\n\n"
        f"Цель: <b>{html.escape(str(title))}</b> — <b>{html.escape(target_name)}</b>\n"
        f"Причина: {html.escape(clean)}\n\n"
        f"Для начала противостояния нужны <b>{threshold}</b> сторонника из <b>{active}</b> активных участников.\n"
        "Сбор поддержки длится <b>6 часов</b>.",
    )
    return conflict_id


async def _join_militia(core: Any, bot: Any, chat_id: int, user_id: int, conflict_id: str, side: str) -> str:
    if side not in {"militia", "loyalist", "neutral"}:
        raise ValueError("Неизвестная сторона конфликта.")
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_conflicts_v131 WHERE conflict_id=? AND chat_id=? AND conflict_type='militia'",
        (str(conflict_id), int(chat_id)),
    )
    conflict = await cursor.fetchone()
    if conflict is None or str(conflict["stage"]) not in {"gathering", "battle"}:
        raise ValueError("Ополчение уже завершено.")
    if str(conflict["stage"]) == "battle":
        cursor = await conn.execute(
            "SELECT side FROM government_conflict_members_v131 WHERE conflict_id=? AND user_id=?",
            (str(conflict_id), int(user_id)),
        )
        current = await cursor.fetchone()
        if current is None or str(current["side"]) != side:
            raise ValueError("После начала противостояния менять сторону нельзя.")
    await conn.execute(
        """INSERT INTO government_conflict_members_v131(
             conflict_id,user_id,side,status,role_key,points,last_action_at,invited_by,created_at
           ) VALUES(?,?,?,'accepted','',0,0,0,?) ON CONFLICT(conflict_id,user_id) DO UPDATE SET
             side=excluded.side,status='accepted'""",
        (str(conflict_id), int(user_id), side, _now()),
    )
    await conn.commit()
    cursor = await conn.execute(
        "SELECT side,COUNT(*) amount FROM government_conflict_members_v131 WHERE conflict_id=? AND status='accepted' GROUP BY side",
        (str(conflict_id),),
    )
    counts = {str(row["side"]): int(row["amount"]) for row in await cursor.fetchall()}
    if str(conflict["stage"]) == "gathering" and counts.get("militia", 0) >= int(conflict["threshold"]):
        militia_score = counts.get("militia", 0) * 20
        loyalist_score = counts.get("loyalist", 0) * 20
        await conn.execute(
            "UPDATE government_conflicts_v131 SET stage='battle',militia_score=?,loyalist_score=?,stage_ends_at=? WHERE conflict_id=? AND stage='gathering'",
            (militia_score, loyalist_score, _now() + MILITIA_BATTLE, str(conflict_id)),
        )
        await conn.commit()
        await gov._publish(
            bot,
            chat_id,
            "⚔️ <b>НАЧАЛО ВНУТРЕННЕГО ПРОТИВОСТОЯНИЯ</b>\n\n"
            f"Ополчение собрало необходимую поддержку: <b>{counts.get('militia', 0)}</b>.\n"
            "Стороны получили <b>30 минут</b> на борьбу за власть.",
        )
        return "Порог собран. Началось 30-минутное противостояние."
    labels = {"militia": "ополчению", "loyalist": "защитникам власти", "neutral": "нейтралитету"}
    return f"Ты присоединился к {labels[side]}."


async def _militia_action(core: Any, chat_id: int, user_id: int, conflict_id: str, action: str) -> str:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_conflicts_v131 WHERE conflict_id=? AND chat_id=? AND conflict_type='militia' AND stage='battle'",
        (str(conflict_id), int(chat_id)),
    )
    conflict = await cursor.fetchone()
    if conflict is None or int(conflict["stage_ends_at"]) <= _now():
        raise ValueError("Активное противостояние не найдено.")
    cursor = await conn.execute(
        "SELECT * FROM government_conflict_members_v131 WHERE conflict_id=? AND user_id=? AND status='accepted'",
        (str(conflict_id), int(user_id)),
    )
    member = await cursor.fetchone()
    if member is None or str(member["side"]) not in {"militia", "loyalist"}:
        raise PermissionError("Для действий нужно выбрать одну из сторон.")
    if int(member["last_action_at"] or 0) + MILITIA_ACTION_COOLDOWN > _now():
        raise ValueError(f"Следующее действие доступно через {_remaining(int(member['last_action_at']) + MILITIA_ACTION_COOLDOWN)}.")
    side = str(member["side"])
    valid = {
        "militia": {"agitate": (8, 16), "seize": (12, 24), "fund": (20, 20), "expose": (8, 18)},
        "loyalist": {"fortify": (10, 20), "suppress": (12, 24), "fund": (20, 20), "investigate": (8, 18)},
    }
    if action not in valid[side]:
        raise ValueError("Это действие недоступно выбранной стороне.")
    if action == "fund":
        player = await _player(core, chat_id, user_id)
        if int(player["points"]) < 500:
            raise ValueError("Для финансирования стороны нужно 500 влияния.")
        await conn.execute(
            "UPDATE players SET points=points-500,updated_at=? WHERE chat_id=? AND user_id=? AND points>=500",
            (_now(), int(chat_id), int(user_id)),
        )
        await conn.execute(
            "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
            (int(chat_id), int(user_id), -500, "militia_funding_v131", _now()),
        )
    low, high = valid[side][action]
    points = low if low == high else low + secrets.randbelow(high - low + 1)
    field = "militia_score" if side == "militia" else "loyalist_score"
    await conn.execute(
        f"UPDATE government_conflicts_v131 SET {field}={field}+? WHERE conflict_id=?",
        (points, str(conflict_id)),
    )
    await conn.execute(
        "UPDATE government_conflict_members_v131 SET points=points+?,last_action_at=? WHERE conflict_id=? AND user_id=?",
        (points, _now(), str(conflict_id), int(user_id)),
    )
    await conn.commit()
    return f"Действие принесло стороне +{points} очков."


async def _resolve_militia(core: Any, bot: Any, conflict: Any, forced_failure: bool = False) -> None:
    conflict_id = str(conflict["conflict_id"])
    chat_id = int(conflict["chat_id"])
    creator = int(conflict["created_by"])
    conn = core.db._require_connection()
    if str(conflict["stage"]) == "gathering" or forced_failure:
        outcome = "failed_support"
        militia_wins = False
    else:
        militia_wins = int(conflict["militia_score"]) > int(conflict["loyalist_score"])
        outcome = "militia_win" if militia_wins else "loyalist_win"
    cursor = await conn.execute(
        "UPDATE government_conflicts_v131 SET stage='resolved',outcome=?,resolved_at=? WHERE conflict_id=? AND stage NOT IN ('resolved','failed','cancelled')",
        (outcome, _now(), conflict_id),
    )
    await conn.commit()
    if int(cursor.rowcount or 0) <= 0:
        return
    target_id = int(conflict["target_user_id"])
    target_name = await _name(core, chat_id, target_id)
    office_key = str(conflict["target_office"])
    title = str(gov.OFFICES.get(office_key, {"title": office_key})["title"])
    if militia_wins:
        await _remove_offices(core, chat_id, target_id, office_key, int(conflict["target_seat"] or 1))
        await gov._publish(
            bot,
            chat_id,
            "🔥 <b>ОПОЛЧЕНИЕ ПОБЕДИЛО</b>\n\n"
            f"{html.escape(title)} <b>{html.escape(target_name)}</b> отстранён от должности.\n"
            f"Счёт: <b>{int(conflict['militia_score'])}</b> — <b>{int(conflict['loyalist_score'])}</b>.",
        )
        if office_key == "president" and not await gov._active_election(core, chat_id, "president"):
            try:
                await gov._start_election(core, bot, chat_id, "president", int(core.DEVELOPER_ID))
            except Exception:
                core.logging.exception("Не удалось открыть досрочные выборы после ополчения")
        return
    creator_player = await _player(core, chat_id, creator)
    penalty = min(5_000, max(500, max(0, int(creator_player["points"])) // 10))
    fine = await _punish_points(core, chat_id, creator, penalty, "failed_militia_penalty_v131")
    await _set_ban(core, "government_conflict_bans_v131", chat_id, creator, 48 * 60 * 60, "Провал ополчения")
    await _issue_finance_sanction(core, bot, chat_id, creator, 6 * 60 * 60, "Организация провалившегося ополчения")
    await conn.execute(
        "UPDATE government_offices_v127 SET trust=MIN(100,trust+10) WHERE chat_id=? AND office_key=? AND seat_no=? AND user_id=?",
        (chat_id, office_key, int(conflict["target_seat"] or 1), target_id),
    )
    await conn.commit()
    await gov._publish(
        bot,
        chat_id,
        "🛡 <b>ОПОЛЧЕНИЕ ПОДАВЛЕНО</b>\n\n"
        f"{html.escape(title)} <b>{html.escape(target_name)}</b> сохранил должность.\n"
        f"Организатор оштрафован на <b>{_fmt(fine)}</b> и не может создавать конфликты 48 часов.",
    )


async def _coup_eligible(core: Any, chat_id: int, user_id: int) -> tuple[bool, list[str], bool]:
    offices = await _offices(core, chat_id, user_id)
    sabotage = await _is_sabotage_hero(core, chat_id, user_id)
    return bool(set(offices) & COUP_ELIGIBLE_OFFICES or sabotage), offices, sabotage


async def _create_coup(core: Any, chat_id: int, user_id: int, invited_id: int, reason: str) -> str:
    if await _active_conflict(core, chat_id) or await _council(core, chat_id):
        raise ValueError("В беседе уже идёт политический конфликт или действует Революционный совет.")
    ban = await _ban_until(core, "government_conflict_bans_v131", chat_id, user_id)
    if ban:
        raise PermissionError(f"Новый заговор доступен через {_remaining(ban)}.")
    eligible, offices, sabotage = await _coup_eligible(core, chat_id, user_id)
    if not eligible:
        raise PermissionError("Дворцовый переворот могут готовить чиновники или саботажный герой.")
    president = await _office_holder(core, chat_id, "president", 1)
    if president is None:
        raise ValueError("Президент ещё не избран.")
    if int(president["user_id"]) == int(user_id):
        raise ValueError("Президент не может организовать переворот против себя.")
    invite_ok, invite_offices, invite_sabotage = await _coup_eligible(core, chat_id, invited_id)
    if not invite_ok or int(invited_id) == int(user_id) or int(invited_id) == int(president["user_id"]):
        raise ValueError("Пригласи другого подходящего чиновника или саботажного героя.")
    clean = str(reason or "").strip()
    if len(clean) < 10 or len(clean) > 600:
        raise ValueError("План должен содержать от 10 до 600 символов.")
    conflict_id = secrets.token_urlsafe(12)
    now = _now()
    payload = {"discovered": False, "launch_roll": 0, "success_chance": 0}
    conn = core.db._require_connection()
    await conn.execute(
        """INSERT INTO government_conflicts_v131(
             conflict_id,chat_id,conflict_type,target_office,target_seat,target_user_id,
             created_by,stage,reason,threshold,plot_score,started_at,stage_ends_at,payload_json
           ) VALUES(?,?,?,?,?,?,?,'recruiting',?,2,?,?,?,?)""",
        (conflict_id, int(chat_id), "coup", "president", 1, int(president["user_id"]),
         int(user_id), clean, 20 if sabotage else 0, now, now + COUP_RECRUITING,
         json.dumps(payload, ensure_ascii=False)),
    )
    role = next((key for key in offices if key in COUP_ELIGIBLE_OFFICES), "sabotage_hero" if sabotage else "")
    invited_role = next((key for key in invite_offices if key in COUP_ELIGIBLE_OFFICES), "sabotage_hero" if invite_sabotage else "")
    await conn.execute(
        "INSERT INTO government_conflict_members_v131(conflict_id,user_id,side,status,role_key,points,last_action_at,invited_by,created_at) VALUES(?,?,'conspirator','accepted',?,0,0,0,?)",
        (conflict_id, int(user_id), role, now),
    )
    await conn.execute(
        "INSERT INTO government_conflict_members_v131(conflict_id,user_id,side,status,role_key,points,last_action_at,invited_by,created_at) VALUES(?,?,'conspirator','invited',?,0,0,?,?)",
        (conflict_id, int(invited_id), invited_role, int(user_id), now),
    )
    await conn.commit()
    return conflict_id


async def _respond_coup_invite(core: Any, bot: Any, chat_id: int, user_id: int, conflict_id: str, accept: bool) -> str:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_conflicts_v131 WHERE conflict_id=? AND chat_id=? AND conflict_type='coup' AND stage='recruiting'",
        (str(conflict_id), int(chat_id)),
    )
    conflict = await cursor.fetchone()
    if conflict is None:
        raise ValueError("Приглашение больше не действует.")
    cursor = await conn.execute(
        "SELECT * FROM government_conflict_members_v131 WHERE conflict_id=? AND user_id=? AND status='invited'",
        (str(conflict_id), int(user_id)),
    )
    invite = await cursor.fetchone()
    if invite is None:
        raise PermissionError("Для тебя нет активного приглашения.")
    await conn.execute(
        "UPDATE government_conflict_members_v131 SET status=? WHERE conflict_id=? AND user_id=?",
        ("accepted" if accept else "declined", str(conflict_id), int(user_id)),
    )
    await conn.commit()
    if not accept:
        return "Приглашение отклонено."
    cursor = await conn.execute(
        "SELECT COUNT(*) amount FROM government_conflict_members_v131 WHERE conflict_id=? AND status='accepted' AND side='conspirator'",
        (str(conflict_id),),
    )
    count = int((await cursor.fetchone())["amount"])
    if count >= 2:
        await conn.execute(
            "UPDATE government_conflicts_v131 SET stage='preparation',stage_ends_at=? WHERE conflict_id=? AND stage='recruiting'",
            (_now() + COUP_PREPARATION, str(conflict_id)),
        )
        await conn.commit()
        return "Заговор сформирован. Началась шестичасовая подготовка."
    return "Ты вступил в заговор."


async def _coup_invite(core: Any, chat_id: int, user_id: int, conflict_id: str, target_id: int) -> str:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_conflicts_v131 WHERE conflict_id=? AND chat_id=? AND conflict_type='coup' AND stage IN ('recruiting','preparation')",
        (str(conflict_id), int(chat_id)),
    )
    conflict = await cursor.fetchone()
    if conflict is None:
        raise ValueError("Активный заговор не найден.")
    cursor = await conn.execute(
        "SELECT 1 FROM government_conflict_members_v131 WHERE conflict_id=? AND user_id=? AND status='accepted'",
        (str(conflict_id), int(user_id)),
    )
    if await cursor.fetchone() is None:
        raise PermissionError("Только участник заговора может вербовать сообщников.")
    eligible, offices, sabotage = await _coup_eligible(core, chat_id, target_id)
    if not eligible or int(target_id) == int(conflict["target_user_id"]):
        raise ValueError("Этот участник не подходит для заговора.")
    role = next((key for key in offices if key in COUP_ELIGIBLE_OFFICES), "sabotage_hero" if sabotage else "")
    await conn.execute(
        """INSERT INTO government_conflict_members_v131(
             conflict_id,user_id,side,status,role_key,points,last_action_at,invited_by,created_at
           ) VALUES(?,?,'conspirator','invited',?,0,0,?,?) ON CONFLICT(conflict_id,user_id) DO UPDATE SET
             status=CASE WHEN government_conflict_members_v131.status='declined' THEN 'invited' ELSE government_conflict_members_v131.status END,
             invited_by=excluded.invited_by,role_key=excluded.role_key""",
        (str(conflict_id), int(target_id), role, int(user_id), _now()),
    )
    await conn.commit()
    return "Тайное приглашение отправлено."


async def _coup_action(core: Any, chat_id: int, user_id: int, conflict_id: str, action: str) -> str:
    valid = {"divert": (8, 16), "forge": (10, 18), "sway": (10, 20), "kompromat": (8, 18)}
    if action not in valid:
        raise ValueError("Неизвестное действие заговора.")
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_conflicts_v131 WHERE conflict_id=? AND chat_id=? AND conflict_type='coup' AND stage='preparation'",
        (str(conflict_id), int(chat_id)),
    )
    conflict = await cursor.fetchone()
    if conflict is None or int(conflict["stage_ends_at"]) <= _now():
        raise ValueError("Подготовка заговора завершена.")
    cursor = await conn.execute(
        "SELECT * FROM government_conflict_members_v131 WHERE conflict_id=? AND user_id=? AND status='accepted' AND side='conspirator'",
        (str(conflict_id), int(user_id)),
    )
    member = await cursor.fetchone()
    if member is None:
        raise PermissionError("Ты не входишь в заговор.")
    if int(member["last_action_at"] or 0) + COUP_ACTION_COOLDOWN > _now():
        raise ValueError(f"Следующее тайное действие доступно через {_remaining(int(member['last_action_at']) + COUP_ACTION_COOLDOWN)}.")
    low, high = valid[action]
    points = low + secrets.randbelow(high - low + 1)
    if str(member["role_key"]) == "sabotage_hero":
        points += 5
    await conn.execute(
        "UPDATE government_conflicts_v131 SET plot_score=plot_score+? WHERE conflict_id=?",
        (points, str(conflict_id)),
    )
    await conn.execute(
        "UPDATE government_conflict_members_v131 SET points=points+?,last_action_at=? WHERE conflict_id=? AND user_id=?",
        (points, _now(), str(conflict_id), int(user_id)),
    )
    await conn.commit()
    return f"Подготовка усилена на {points} очков."


async def _counterintel(core: Any, bot: Any, chat_id: int, user_id: int) -> str:
    offices = await _offices(core, chat_id, user_id)
    allowed = set(offices) & {"president", "security", "prosecutor", "oversight"}
    if int(user_id) == int(core.DEVELOPER_ID):
        allowed.add("security")
    if not allowed:
        raise PermissionError("Контрразведка доступна президенту, Совбезу, прокуратуре и Надзору.")
    conflict = await _active_conflict(core, chat_id)
    if conflict is None or str(conflict["conflict_type"]) != "coup" or str(conflict["stage"]) not in {"recruiting", "preparation"}:
        return "Признаков активного заговора не обнаружено."
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_conflict_members_v131 WHERE conflict_id=? AND user_id=?",
        (str(conflict["conflict_id"]), int(user_id)),
    )
    own = await cursor.fetchone()
    if own is not None and str(own["status"]) == "accepted":
        raise PermissionError("Участник заговора не может проводить контрразведку против самого себя.")
    cursor = await conn.execute(
        "SELECT last_action_at FROM government_conflict_members_v131 WHERE conflict_id=? AND user_id=? AND side='counterintel'",
        (str(conflict["conflict_id"]), int(user_id)),
    )
    row = await cursor.fetchone()
    if row and int(row["last_action_at"] or 0) + COUP_ACTION_COOLDOWN > _now():
        raise ValueError(f"Следующая проверка доступна через {_remaining(int(row['last_action_at']) + COUP_ACTION_COOLDOWN)}.")
    office = next(iter(allowed))
    base = {"security": 22, "prosecutor": 20, "oversight": 18, "president": 12}.get(office, 15)
    defense = base + secrets.randbelow(9)
    chance = max(5, min(75, 15 + defense + int(conflict["defense_score"]) // 3 - int(conflict["plot_score"]) // 5))
    roll = secrets.randbelow(100) + 1
    await conn.execute(
        """INSERT INTO government_conflict_members_v131(
             conflict_id,user_id,side,status,role_key,points,last_action_at,invited_by,created_at
           ) VALUES(?,?,'counterintel','accepted',?,?,?,0,?) ON CONFLICT(conflict_id,user_id) DO UPDATE SET
             side='counterintel',status='accepted',role_key=excluded.role_key,
             points=government_conflict_members_v131.points+excluded.points,last_action_at=excluded.last_action_at""",
        (str(conflict["conflict_id"]), int(user_id), office, defense, _now(), _now()),
    )
    await conn.execute(
        "UPDATE government_conflicts_v131 SET defense_score=defense_score+? WHERE conflict_id=?",
        (defense, str(conflict["conflict_id"])),
    )
    await conn.commit()
    if roll <= chance:
        fresh_cursor = await conn.execute("SELECT * FROM government_conflicts_v131 WHERE conflict_id=?", (str(conflict["conflict_id"]),))
        fresh = await fresh_cursor.fetchone()
        if fresh is not None:
            await _resolve_coup(core, bot, fresh, forced_success=False, discovered=True)
        return "Заговор раскрыт. Участники задержаны."
    return "Проверка завершена. Прямых доказательств пока нет."


async def _coup_chance(core: Any, conflict: Any) -> tuple[int, list[int]]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT user_id,role_key FROM government_conflict_members_v131 WHERE conflict_id=? AND side='conspirator' AND status='accepted'",
        (str(conflict["conflict_id"]),),
    )
    members = list(await cursor.fetchall())
    member_ids = [int(row["user_id"]) for row in members]
    bonus = 25
    for row in members:
        role = str(row["role_key"])
        if role == "chair":
            bonus += 15
        elif role == "oversight":
            bonus += 15
        elif role == "finance":
            bonus += 10
        elif role == "deputy":
            bonus += 10
        elif role == "sabotage_hero":
            bonus += 20
    bonus += min(30, int(conflict["plot_score"]) // 2)
    president = await _office_holder(core, int(conflict["chat_id"]), "president", 1)
    if president is not None and int(president["trust"] or 50) < 30:
        bonus += 10
    if await _treasury(core, int(conflict["chat_id"])) <= 0:
        bonus += 10
    bonus -= min(30, int(conflict["defense_score"] or 0))
    for loyal_office in ("prosecutor", "security"):
        holder = await _office_holder(core, int(conflict["chat_id"]), loyal_office, 1)
        if holder is not None and int(holder["user_id"]) not in member_ids:
            bonus -= 15
    return max(10, min(85, bonus)), member_ids


async def _resolve_coup(core: Any, bot: Any, conflict: Any, forced_success: bool | None = None, discovered: bool = False) -> None:
    conflict_id = str(conflict["conflict_id"])
    chat_id = int(conflict["chat_id"])
    conn = core.db._require_connection()
    chance, member_ids = await _coup_chance(core, conflict)
    roll = secrets.randbelow(100) + 1
    success = bool(forced_success) if forced_success is not None else roll <= chance
    if discovered:
        success = False
    outcome = "coup_win" if success else "coup_failed"
    payload = _json(conflict["payload_json"], {})
    payload.update({"success_chance": chance, "launch_roll": roll, "discovered": bool(discovered)})
    cursor = await conn.execute(
        "UPDATE government_conflicts_v131 SET stage='resolved',outcome=?,payload_json=?,resolved_at=? WHERE conflict_id=? AND stage NOT IN ('resolved','failed','cancelled')",
        (outcome, json.dumps(payload, ensure_ascii=False), _now(), conflict_id),
    )
    await conn.commit()
    if int(cursor.rowcount or 0) <= 0:
        return
    names = [await _name(core, chat_id, user_id) for user_id in member_ids]
    if success:
        await _remove_offices(core, chat_id, int(conflict["target_user_id"]), "president", 1)
        until_at = _now() + COUNCIL_TERM
        await conn.execute(
            """INSERT INTO government_council_v131(chat_id,conflict_id,members_json,until_at,election_called,created_at)
               VALUES(?,?,?,?,0,?) ON CONFLICT(chat_id) DO UPDATE SET conflict_id=excluded.conflict_id,
               members_json=excluded.members_json,until_at=excluded.until_at,election_called=0,created_at=excluded.created_at""",
            (chat_id, conflict_id, json.dumps(member_ids), until_at, _now()),
        )
        await conn.commit()
        await gov._publish(
            bot,
            chat_id,
            "🗡 <b>ДВОРЦОВЫЙ ПЕРЕВОРОТ УДАЛСЯ</b>\n\n"
            f"Президент свергнут. Заговорщики: <b>{html.escape(', '.join(names))}</b>.\n"
            f"Шанс операции: <b>{chance}%</b>, бросок: <b>{roll}</b>.\n\n"
            "Власть на 12 часов переходит Революционному совету. После этого откроются досрочные выборы.",
        )
        return
    total_confiscated = 0
    for member_id in member_ids:
        await _remove_offices(core, chat_id, member_id)
        player = await _player(core, chat_id, member_id)
        penalty = min(10_000, max(500, max(0, int(player["points"])) // 10))
        total_confiscated += await _punish_points(core, chat_id, member_id, penalty, "failed_coup_confiscation_v131")
        await _set_ban(core, "government_election_bans_v131", chat_id, member_id, 24 * 60 * 60, "Провал дворцового переворота")
        await _set_ban(core, "government_conflict_bans_v131", chat_id, member_id, 48 * 60 * 60, "Провал дворцового переворота")
        await _issue_finance_sanction(core, bot, chat_id, member_id, 24 * 60 * 60, "Участие в провалившемся дворцовом перевороте")
    await conn.execute(
        "UPDATE government_offices_v127 SET trust=MIN(100,trust+15) WHERE chat_id=? AND office_key='president' AND seat_no=1 AND user_id=?",
        (chat_id, int(conflict["target_user_id"])),
    )
    await conn.commit()
    await gov._publish(
        bot,
        chat_id,
        "🚨 <b>ДВОРЦОВЫЙ ПЕРЕВОРОТ РАСКРЫТ</b>\n\n"
        f"Участники: <b>{html.escape(', '.join(names))}</b>.\n"
        f"Шанс операции: <b>{chance}%</b>, бросок: <b>{roll}</b>.\n"
        f"Конфисковано: <b>{_fmt(total_confiscated)}</b>.\n\n"
        "Заговорщики лишены должностей, получили финансовые санкции и запрет на выборы.",
    )


async def _launch_coup(core: Any, bot: Any, chat_id: int, user_id: int, conflict_id: str) -> str:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_conflicts_v131 WHERE conflict_id=? AND chat_id=? AND conflict_type='coup' AND stage='preparation'",
        (str(conflict_id), int(chat_id)),
    )
    conflict = await cursor.fetchone()
    if conflict is None:
        raise ValueError("Активная подготовка не найдена.")
    cursor = await conn.execute(
        "SELECT 1 FROM government_conflict_members_v131 WHERE conflict_id=? AND user_id=? AND side='conspirator' AND status='accepted'",
        (str(conflict_id), int(user_id)),
    )
    if await cursor.fetchone() is None:
        raise PermissionError("Только заговорщик может начать операцию.")
    if int(conflict["plot_score"] or 0) < 50:
        raise ValueError("Для запуска нужно накопить минимум 50 очков подготовки.")
    await _resolve_coup(core, bot, conflict)
    return "Операция началась. Итог опубликован в беседе."


async def _council(core: Any, chat_id: int) -> Any | None:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_council_v131 WHERE chat_id=? AND until_at>?",
        (int(chat_id), _now()),
    )
    return await cursor.fetchone()


async def _require_council_member(core: Any, chat_id: int, user_id: int) -> Any:
    council = await _council(core, chat_id)
    if council is None:
        raise PermissionError("Революционный совет сейчас не действует.")
    members = [int(value) for value in _json(council["members_json"], [])]
    if int(user_id) not in members and int(user_id) != int(core.DEVELOPER_ID):
        raise PermissionError("Это действие доступно только Революционному совету.")
    return council


async def _council_action(core: Any, bot: Any, chat_id: int, user_id: int, action: str, data: dict[str, Any]) -> str:
    council = await _require_council_member(core, chat_id, user_id)
    conn = core.db._require_connection()
    if action == "council_freeze":
        await institutions._policy(core, chat_id)
        await conn.execute(
            "UPDATE government_policy_v128 SET economic_mode='freeze',mode_ends_at=?,updated_at=? WHERE chat_id=?",
            (_now() + 6 * 60 * 60, _now(), int(chat_id)),
        )
        await conn.commit()
        await gov._publish(bot, chat_id, "🧊 <b>РЕВОЛЮЦИОННЫЙ СОВЕТ ЗАМОРОЗИЛ КРУПНЫЕ ОПЕРАЦИИ</b>\n\nРежим действует 6 часов.")
        return "Экономическая заморозка введена на 6 часов."
    if action == "council_remove_official":
        office_key = str(data.get("office_key") or "")
        if office_key not in APPOINTED_OFFICES:
            raise ValueError("Совет может снять только назначенного чиновника.")
        holder = await _office_holder(core, chat_id, office_key, 1)
        if holder is None:
            raise ValueError("Эта должность уже свободна.")
        target_name = await _name(core, chat_id, int(holder["user_id"]))
        await _remove_offices(core, chat_id, int(holder["user_id"]), office_key, 1)
        await gov._publish(bot, chat_id, f"🗡 <b>РЕШЕНИЕ РЕВОЛЮЦИОННОГО СОВЕТА</b>\n\n{html.escape(str(gov.OFFICES[office_key]['title']))} <b>{html.escape(target_name)}</b> снят с должности.")
        return "Чиновник снят с должности."
    if action == "council_amnesty":
        members = [int(value) for value in _json(council["members_json"], [])]
        lifted = 0
        for member_id in members:
            types = await sanctions.revoke_sanctions(core, chat_id, member_id, int(core.DEVELOPER_ID), reason="Амнистия Революционного совета")
            lifted += len(types)
        return f"Амнистия исполнена. Снято ограничений: {lifted}."
    if action == "council_call_election":
        if int(council["election_called"] or 0):
            raise ValueError("Досрочные выборы уже объявлены.")
        if not await gov._active_election(core, chat_id, "president"):
            await gov._start_election(core, bot, chat_id, "president", int(core.DEVELOPER_ID))
        await conn.execute("UPDATE government_council_v131 SET election_called=1 WHERE chat_id=?", (int(chat_id),))
        await conn.commit()
        return "Досрочные выборы президента объявлены."
    raise ValueError("Неизвестное действие Революционного совета.")


async def _serialize_crisis(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    await _ensure_schema(core)
    conn = core.db._require_connection()
    now = _now()
    offices = await _offices(core, chat_id, user_id)
    sabotage = await _is_sabotage_hero(core, chat_id, user_id)
    cursor = await conn.execute(
        "SELECT next_at FROM government_theft_cooldowns_v131 WHERE chat_id=? AND user_id=?",
        (int(chat_id), int(user_id)),
    )
    cooldown = await cursor.fetchone()
    theft_next = int(cooldown["next_at"] or 0) if cooldown else 0
    cursor = await conn.execute(
        "SELECT * FROM government_thefts_v131 WHERE chat_id=? ORDER BY started_at DESC LIMIT 20",
        (int(chat_id),),
    )
    thefts: list[dict[str, Any]] = []
    can_investigate = bool(set(offices) & set(INVESTIGATOR_OFFICES)) or int(user_id) == int(core.DEVELOPER_ID)
    for row in await cursor.fetchall():
        status = str(row["status"])
        own = int(row["thief_id"]) == int(user_id)
        visible_thief = own or status == "caught" or int(user_id) == int(core.DEVELOPER_ID)
        cursor2 = await conn.execute(
            "SELECT 1 FROM government_theft_investigations_v131 WHERE theft_id=? AND investigator_id=?",
            (str(row["theft_id"]), int(user_id)),
        )
        investigated = await cursor2.fetchone() is not None
        thefts.append({
            "theft_id": str(row["theft_id"]),
            "percent": int(row["percent"]),
            "amount": int(row["amount"]),
            "status": status,
            "started_at": int(row["started_at"]),
            "resolve_at": int(row["resolve_at"]),
            "remaining": _remaining(int(row["resolve_at"])) if status == "pending" else "",
            "investigations": int(row["investigations"] or 0),
            "thief_id": int(row["thief_id"]) if visible_thief else 0,
            "thief_name": await _name(core, chat_id, int(row["thief_id"])) if visible_thief else "Неизвестен",
            "own": own,
            "can_investigate": bool(can_investigate and status == "pending" and not investigated),
            "investigated": investigated,
        })
    conflict = await _active_conflict(core, chat_id)
    conflict_data: dict[str, Any] | None = None
    if conflict is not None:
        conflict_id = str(conflict["conflict_id"])
        cursor = await conn.execute(
            "SELECT * FROM government_conflict_members_v131 WHERE conflict_id=? ORDER BY created_at",
            (conflict_id,),
        )
        members = list(await cursor.fetchall())
        my_member = next((row for row in members if int(row["user_id"]) == int(user_id)), None)
        type_key = str(conflict["conflict_type"])
        if type_key == "militia":
            public_members = [
                {"user_id": int(row["user_id"]), "name": await _name(core, chat_id, int(row["user_id"])),
                 "side": str(row["side"]), "points": int(row["points"]), "status": str(row["status"])}
                for row in members if str(row["status"]) == "accepted"
            ]
            conflict_data = {
                "conflict_id": conflict_id, "type": type_key, "stage": str(conflict["stage"]),
                "target_office": str(conflict["target_office"]), "target_user_id": int(conflict["target_user_id"]),
                "target_name": await _name(core, chat_id, int(conflict["target_user_id"])),
                "reason": str(conflict["reason"]), "threshold": int(conflict["threshold"]),
                "militia_score": int(conflict["militia_score"]), "loyalist_score": int(conflict["loyalist_score"]),
                "stage_ends_at": int(conflict["stage_ends_at"]), "remaining": _remaining(int(conflict["stage_ends_at"])),
                "my_side": str(my_member["side"]) if my_member else "", "members": public_members,
            }
        else:
            is_conspirator = bool(my_member is not None and str(my_member["side"]) == "conspirator" and str(my_member["status"]) in {"accepted", "invited"})
            counterintel = bool(set(offices) & {"president", "security", "prosecutor", "oversight"}) or int(user_id) == int(core.DEVELOPER_ID)
            if is_conspirator or counterintel or int(user_id) == int(core.DEVELOPER_ID):
                visible_members = []
                if is_conspirator or int(user_id) == int(core.DEVELOPER_ID):
                    visible_members = [
                        {"user_id": int(row["user_id"]), "name": await _name(core, chat_id, int(row["user_id"])),
                         "status": str(row["status"]), "role_key": str(row["role_key"]), "points": int(row["points"])}
                        for row in members if str(row["side"]) == "conspirator"
                    ]
                conflict_data = {
                    "conflict_id": conflict_id, "type": type_key, "stage": str(conflict["stage"]),
                    "target_user_id": int(conflict["target_user_id"]),
                    "target_name": await _name(core, chat_id, int(conflict["target_user_id"])),
                    "reason": str(conflict["reason"]) if is_conspirator else "Засекречено",
                    "plot_score": int(conflict["plot_score"]) if is_conspirator else 0,
                    "defense_score": int(conflict["defense_score"]) if counterintel else 0,
                    "stage_ends_at": int(conflict["stage_ends_at"]), "remaining": _remaining(int(conflict["stage_ends_at"])),
                    "my_status": str(my_member["status"]) if my_member else "",
                    "is_conspirator": is_conspirator, "can_counterintel": counterintel,
                    "members": visible_members,
                }
    council = await _council(core, chat_id)
    council_data = None
    if council is not None:
        member_ids = [int(value) for value in _json(council["members_json"], [])]
        council_data = {
            "members": [{"user_id": value, "name": await _name(core, chat_id, value)} for value in member_ids],
            "until_at": int(council["until_at"]), "remaining": _remaining(int(council["until_at"])),
            "election_called": bool(int(council["election_called"])),
            "is_member": int(user_id) in member_ids or int(user_id) == int(core.DEVELOPER_ID),
        }
    election_ban = await _ban_until(core, "government_election_bans_v131", chat_id, user_id)
    conflict_ban = await _ban_until(core, "government_conflict_bans_v131", chat_id, user_id)
    targets = []
    for row in await gov._office_rows(core, chat_id):
        targets.append({
            "office_key": str(row["office_key"]), "seat_no": int(row["seat_no"]),
            "title": str(gov.OFFICES.get(str(row["office_key"]), {"title": row["office_key"]})["title"]),
            "user_id": int(row["user_id"]), "name": str(row["full_name"] or row["user_id"]),
        })
    eligible_coup_users = []
    for person in await gov._eligible_users(core, chat_id):
        if int(person["user_id"]) == int(user_id):
            continue
        ok, person_offices, person_sabotage = await _coup_eligible(core, chat_id, int(person["user_id"]))
        if ok:
            eligible_coup_users.append({
                **person, "offices": person_offices, "sabotage_hero": person_sabotage,
            })
    return {
        "version": VERSION,
        "sabotage_hero": sabotage,
        "offices": offices,
        "theft": {
            "cooldown_seconds": THEFT_COOLDOWN,
            "next_at": theft_next,
            "remaining": _remaining(theft_next) if theft_next > now else "готово",
            "can_attempt": theft_next <= now and not await sanctions.blocking_sanction(core, chat_id, user_id, "finance"),
            "rules": [{"percent": percent, "success": success, "detection": detection} for percent, (success, detection) in THEFT_RULES.items()],
            "items": thefts,
        },
        "conflict": conflict_data,
        "council": council_data,
        "targets": targets,
        "eligible_coup_users": eligible_coup_users,
        "election_ban_until": election_ban,
        "election_ban_remaining": _remaining(election_ban) if election_ban else "",
        "conflict_ban_until": conflict_ban,
        "conflict_ban_remaining": _remaining(conflict_ban) if conflict_ban else "",
        "can_create_coup": bool((set(offices) & COUP_ELIGIBLE_OFFICES or sabotage) and not conflict and not conflict_ban),
        "can_create_militia": bool(not conflict and not conflict_ban),
        "can_investigate": can_investigate,
    }


async def _process_runtime(core: Any, bot: Any) -> None:
    await _ensure_schema(core)
    conn = core.db._require_connection()
    now = _now()
    cursor = await conn.execute(
        "SELECT * FROM government_thefts_v131 WHERE status='pending' AND resolve_at<=? ORDER BY resolve_at",
        (now,),
    )
    for theft in await cursor.fetchall():
        await _resolve_theft(core, bot, theft)
    cursor = await conn.execute(
        "SELECT * FROM government_conflicts_v131 WHERE stage IN ('gathering','battle','recruiting','preparation') AND stage_ends_at<=? ORDER BY stage_ends_at",
        (now,),
    )
    for conflict in await cursor.fetchall():
        kind = str(conflict["conflict_type"])
        stage = str(conflict["stage"])
        if kind == "militia":
            await _resolve_militia(core, bot, conflict, forced_failure=stage == "gathering")
        elif kind == "coup":
            if stage == "recruiting":
                await conn.execute(
                    "UPDATE government_conflicts_v131 SET stage='resolved',outcome='recruitment_failed',resolved_at=? WHERE conflict_id=? AND stage='recruiting'",
                    (now, str(conflict["conflict_id"])),
                )
                await conn.commit()
                await _set_ban(core, "government_conflict_bans_v131", int(conflict["chat_id"]), int(conflict["created_by"]), 24 * 60 * 60, "Заговор не собрал участников")
            else:
                await _resolve_coup(core, bot, conflict)
    cursor = await conn.execute(
        "SELECT * FROM government_council_v131 WHERE until_at<=?",
        (now,),
    )
    for council in await cursor.fetchall():
        chat_id = int(council["chat_id"])
        if not int(council["election_called"] or 0) and not await gov._active_election(core, chat_id, "president"):
            try:
                await gov._start_election(core, bot, chat_id, "president", int(core.DEVELOPER_ID))
            except Exception:
                core.logging.exception("Не удалось открыть выборы после Революционного совета")
        await conn.execute("DELETE FROM government_council_v131 WHERE chat_id=?", (chat_id,))
        await conn.commit()
        await gov._publish(bot, chat_id, "🏛 <b>СРОК РЕВОЛЮЦИОННОГО СОВЕТА ЗАВЕРШЁН</b>\n\nГосударство переходит к досрочным выборам президента.")


async def _runtime_loop(core: Any, bot: Any) -> None:
    await asyncio.sleep(5)
    while True:
        try:
            await _process_runtime(core, bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            core.logging.exception("Ошибка политического цикла Reality 131")
        await asyncio.sleep(15)


def _route_keys(app: Any) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        result.add((str(getattr(route, "method", "") or "").upper(), str(getattr(resource, "canonical", "") or "")))
    return result


def install_government_crisis_v131(core: Any) -> None:
    global _RUNTIME_STARTED
    if getattr(core, "_government_crisis_v131_installed", False):
        return
    core._government_crisis_v131_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION

    original_connect = core.Database.connect

    async def connect_with_crisis(self: Any) -> None:
        await original_connect(self)
        core._government_crisis_v131_schema_ready = False
        await _ensure_schema(core)

    core.Database.connect = connect_with_crisis

    original_nominate = gov._nominate

    async def nominate_with_crisis_ban(core_value: Any, chat_id: int, user_id: int, election_id: str, program: str) -> None:
        await _ensure_schema(core_value)
        until_at = await _ban_until(core_value, "government_election_bans_v131", chat_id, user_id)
        if until_at:
            raise PermissionError(f"Участие в выборах запрещено ещё {_remaining(until_at)}.")
        await original_nominate(core_value, chat_id, user_id, election_id, program)

    gov._nominate = nominate_with_crisis_ban

    original_state = gov._state

    async def state_with_crisis(core_value: Any, bot: Any, chat_id: int, user_id: int) -> dict[str, Any]:
        state = await original_state(core_value, bot, chat_id, user_id)
        state["version"] = VERSION
        state["crisis_v131"] = await _serialize_crisis(core_value, chat_id, user_id)
        return state

    gov._state = state_with_crisis

    async def action_api(request: Any):
        try:
            user, chat_id, data = await gov._auth(core, request)
            user_id = int(user.id)
            action = str(data.get("action") or "")
            bot = request.app["bot"]
            if action == "steal_treasury":
                message = await _start_theft(core, bot, chat_id, user_id, _as_int(data.get("percent")))
            elif action == "investigate_theft":
                message = await _investigate_theft(core, bot, chat_id, user_id, str(data.get("theft_id") or ""))
            elif action == "create_militia":
                conflict_id = await _create_militia(core, bot, chat_id, user_id, str(data.get("office_key") or ""), max(1, _as_int(data.get("seat_no"), 1)), str(data.get("reason") or ""))
                message = f"Ополчение создано: {conflict_id}."
            elif action == "join_militia":
                message = await _join_militia(core, bot, chat_id, user_id, str(data.get("conflict_id") or ""), str(data.get("side") or ""))
            elif action == "militia_action":
                message = await _militia_action(core, chat_id, user_id, str(data.get("conflict_id") or ""), str(data.get("battle_action") or ""))
            elif action == "create_coup":
                conflict_id = await _create_coup(core, chat_id, user_id, _as_int(data.get("target_user_id")), str(data.get("reason") or ""))
                message = f"Тайный заговор создан: {conflict_id}."
            elif action == "respond_coup_invite":
                message = await _respond_coup_invite(core, bot, chat_id, user_id, str(data.get("conflict_id") or ""), bool(data.get("accept")))
            elif action == "coup_invite":
                message = await _coup_invite(core, chat_id, user_id, str(data.get("conflict_id") or ""), _as_int(data.get("target_user_id")))
            elif action == "coup_action":
                message = await _coup_action(core, chat_id, user_id, str(data.get("conflict_id") or ""), str(data.get("coup_action") or ""))
            elif action == "counterintel":
                message = await _counterintel(core, bot, chat_id, user_id)
            elif action == "launch_coup":
                message = await _launch_coup(core, bot, chat_id, user_id, str(data.get("conflict_id") or ""))
            elif action.startswith("council_"):
                message = await _council_action(core, bot, chat_id, user_id, action, data)
            else:
                raise ValueError("Неизвестное кризисное действие.")
            return core.web.json_response({"ok": True, "message": message})
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            core.logging.exception("Ошибка действия Reality 131")
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    async def asset(request: Any):
        name = str(request.match_info["name"])
        path = ASSET_JS if name.endswith(".js") else ASSET_CSS
        if name not in {"crisis-v131.js", "crisis-v131.css"} or not path.is_file():
            raise core.web.HTTPNotFound()
        return core.web.FileResponse(path, headers={"Cache-Control": "no-store", "X-Government-Crisis": "131"})

    @core.web.middleware
    async def crisis_assets_and_index(request: Any, handler: Any):
        path = str(request.path or "")
        if request.method.upper() == "GET" and path in {"/government-v127", "/government-v127/"}:
            source = (APP_DIR / "index.html").read_text(encoding="utf-8")
            if "crisis-v131.css" not in source:
                source = source.replace(
                    '<link rel="stylesheet" href="/government-v127/powers-v128.css?v=128">',
                    '<link rel="stylesheet" href="/government-v127/powers-v128.css?v=128">\n  <link rel="stylesheet" href="/government-v131/crisis-v131.css?v=131">',
                )
            if "crisis-v131.js" not in source:
                source = source.replace(
                    '<script src="/government-v127/powers-v128.js?v=128"></script>',
                    '<script src="/government-v127/powers-v128.js?v=128"></script>\n  <script src="/government-v131/crisis-v131.js?v=131"></script>',
                )
            source = source.replace("REALITY 128", "REALITY 131")
            return core.web.Response(text=source, content_type="text/html", charset="utf-8", headers={"Cache-Control": "no-store", "X-Government": "reality-131"})
        return await handler(request)

    previous_application = core.web.Application

    def application_with_crisis(*args: Any, **kwargs: Any):
        application = previous_application(*args, **kwargs)
        application.middlewares.insert(0, crisis_assets_and_index)
        return application

    core.web.Application = application_with_crisis
    original_start = core.start_webapp_server

    async def start_with_crisis(bot: Any):
        global _RUNTIME_STARTED
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты политического кризиса Reality 131")
        original_runner = core.web.AppRunner

        def runner_factory(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("POST", "/government-v131/api/action") not in keys:
                app.router.add_post("/government-v131/api/action", action_api)
            if ("GET", "/government-v131/{name:crisis-v131\\.css|crisis-v131\\.js}") not in keys:
                app.router.add_get("/government-v131/{name:crisis-v131\\.css|crisis-v131\\.js}", asset)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_factory
        try:
            runner = await original_start(bot)
        finally:
            core.web.AppRunner = original_runner
        if not _RUNTIME_STARTED:
            _RUNTIME_STARTED = True
            core.spawn_background_task(_runtime_loop(core, bot))
        return runner

    core.start_webapp_server = start_with_crisis
