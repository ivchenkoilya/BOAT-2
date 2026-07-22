from __future__ import annotations

import hashlib
import html
import json
import random
from typing import Any

import government_crisis_v131 as crisis
import government_election_shadow_v153 as shadow
import government_v127 as gov


VERSION = "Reality 163 · Детективное расследование казны"
QUEST_ROLES = ("finance", "auditor", "oversight", "prosecutor")
ROLE_TITLES = {
    "finance": "Министерство финансов",
    "auditor": "Счётная палата",
    "oversight": "Государственный надзор",
    "prosecutor": "Генеральная прокуратура",
}
ROLE_ICONS = {
    "finance": "💰",
    "auditor": "🧾",
    "oversight": "🚨",
    "prosecutor": "⚖️",
}
DELEGATION_DELAY = 20 * 60
RETRY_DELAY = 5 * 60
ACCUSATION_RETRY = 15 * 60
MAX_WRONG_ACCUSATIONS = 2
MAX_COVER_ACTIONS = 2
COVER_COSTS = {
    "split_route": 10,
    "forge_log": 10,
    "frame_suspect": 15,
    "destroy_trace": 20,
}


def _now() -> int:
    return gov._now()


def _loads(value: Any, default: Any) -> Any:
    if isinstance(value, type(default)):
        return value
    try:
        parsed = json.loads(str(value or ""))
        return parsed if isinstance(parsed, type(default)) else default
    except Exception:
        return default


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _rng(theft_id: str, salt: str) -> random.Random:
    digest = hashlib.sha256(f"{theft_id}:{salt}:reality163".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _finance_task(theft_id: str, amount: int, hard: bool = False) -> dict[str, Any]:
    rng = _rng(theft_id, "finance-hard" if hard else "finance")
    parts = 4 if hard else 3
    split = [max(1, amount // parts) for _ in range(parts)]
    split[-1] += amount - sum(split)
    correct = (
        f"Казна −{gov._fmt(amount)} → дробление "
        + " + ".join(gov._fmt(value) for value in split)
        + " → закрытый теневой контур"
    )
    options = [
        correct,
        f"Казна −{gov._fmt(amount)} → возврат налога → социальная выплата",
        f"Казна −{gov._fmt(amount)} → резерв ЦБ → погашение государственного долга",
    ]
    if hard:
        options.append(
            f"Казна −{gov._fmt(amount)} → покупка акций → комиссия рынка → бюджет"
        )
    rng.shuffle(options)
    answer = str(options.index(correct))
    return {
        "kind": "finance_route",
        "question": "Какой маршрут сохраняет контрольную сумму похищения?",
        "description": "Сопоставь сумму вывода, дробление и конечный закрытый контур.",
        "options": [{"id": str(index), "text": text} for index, text in enumerate(options)],
        "answer": answer,
        "hard": hard,
    }


def _audit_task(theft_id: str, amount: int, started_at: int, hard: bool = False) -> dict[str, Any]:
    rng = _rng(theft_id, "audit-hard" if hard else "audit")
    count = 5 if hard else 4
    anomaly_index = rng.randrange(count)
    records: list[dict[str, Any]] = []
    for index in range(count):
        timestamp = started_at - 90 + index * 37
        value = max(1, amount // 4 + (index - 1) * 3)
        signature = hashlib.sha1(f"{theft_id}:{index}:ok".encode()).hexdigest()[:8].upper()
        note = "контрольная запись"
        if index == anomaly_index:
            timestamp = started_at + 48
            value += 17
            signature = hashlib.sha1(f"{theft_id}:{index}:fake".encode()).hexdigest()[:8].upper()
            note = "запись изменена после операции"
        records.append(
            {
                "id": str(index),
                "time": timestamp,
                "amount": value,
                "signature": signature,
                "note": note,
            }
        )
    return {
        "kind": "audit_record",
        "question": "Какая запись журнала была подделана?",
        "description": "Сравни время, сумму и цифровую подпись документов.",
        "records": records,
        "answer": str(anomaly_index),
        "hard": hard,
    }


async def ensure_schema(core: Any) -> None:
    if getattr(core.db, "_government_theft_quest_v163_schema", False):
        return
    await crisis._ensure_schema(core)
    await shadow._ensure_schema(core)
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS government_theft_cases_v163(
                theft_id TEXT PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                case_no INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'investigation',
                original_amount INTEGER NOT NULL,
                loot_remaining INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                resolve_at INTEGER NOT NULL,
                public_clues_json TEXT NOT NULL DEFAULT '[]',
                shortlist_json TEXT NOT NULL DEFAULT '[]',
                framed_user_id INTEGER NOT NULL DEFAULT 0,
                wrong_accusations INTEGER NOT NULL DEFAULT 0,
                last_accusation_at INTEGER NOT NULL DEFAULT 0,
                cover_actions_json TEXT NOT NULL DEFAULT '[]',
                updated_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_theft_cases_chat_v163
            ON government_theft_cases_v163(chat_id,status,created_at DESC);

            CREATE TABLE IF NOT EXISTS government_theft_suspects_v163(
                theft_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                suspect_code TEXT NOT NULL,
                display_name TEXT NOT NULL,
                username TEXT NOT NULL DEFAULT '',
                points_before INTEGER NOT NULL,
                updated_at_before INTEGER NOT NULL DEFAULT 0,
                had_access INTEGER NOT NULL DEFAULT 0,
                offices_json TEXT NOT NULL DEFAULT '[]',
                activity_before INTEGER NOT NULL DEFAULT 0,
                route_match INTEGER NOT NULL DEFAULT 0,
                audit_match INTEGER NOT NULL DEFAULT 0,
                framed INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(theft_id,user_id),
                UNIQUE(theft_id,suspect_code)
            );

            CREATE TABLE IF NOT EXISTS government_theft_tasks_v163(
                theft_id TEXT NOT NULL,
                office_key TEXT NOT NULL,
                assignee_id INTEGER NOT NULL DEFAULT 0,
                delegate_id INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                available_at INTEGER NOT NULL DEFAULT 0,
                completed_at INTEGER NOT NULL DEFAULT 0,
                task_json TEXT NOT NULL DEFAULT '{}',
                result_json TEXT NOT NULL DEFAULT '{}',
                clue TEXT NOT NULL DEFAULT '',
                PRIMARY KEY(theft_id,office_key)
            );

            CREATE TABLE IF NOT EXISTS government_theft_cover_actions_v163(
                theft_id TEXT NOT NULL,
                actor_id INTEGER NOT NULL,
                action_key TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                cost INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                PRIMARY KEY(theft_id,action_key)
            );
            """
        )
        await conn.commit()
    core.db._government_theft_quest_v163_schema = True


async def _player_row(core: Any, chat_id: int, user_id: int) -> Any | None:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT user_id,full_name,username,points,updated_at FROM players WHERE chat_id=? AND user_id=?",
        (int(chat_id), int(user_id)),
    )
    return await cursor.fetchone()


async def _holder(core: Any, chat_id: int, office_key: str, at: int) -> int:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT user_id FROM government_offices_v127
        WHERE chat_id=? AND office_key=? AND starts_at<=? AND ends_at>?
        ORDER BY starts_at DESC LIMIT 1
        """,
        (int(chat_id), str(office_key), int(at), int(at)),
    )
    row = await cursor.fetchone()
    return int(row["user_id"]) if row else 0


async def _candidate_rows(core: Any, theft: Any) -> list[dict[str, Any]]:
    chat_id = int(theft["chat_id"])
    thief_id = int(theft["thief_id"])
    started_at = int(theft["started_at"])
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT p.user_id,p.full_name,p.username,p.points,p.updated_at,
               GROUP_CONCAT(DISTINCT o.office_key) AS offices
        FROM players p
        LEFT JOIN government_offices_v127 o
          ON o.chat_id=p.chat_id AND o.user_id=p.user_id
         AND o.starts_at<=? AND o.ends_at>?
        WHERE p.chat_id=?
        GROUP BY p.user_id,p.full_name,p.username,p.points,p.updated_at
        ORDER BY CASE WHEN COUNT(o.office_key)>0 THEN 0 ELSE 1 END,
                 p.updated_at DESC,p.points DESC
        LIMIT 24
        """,
        (started_at, started_at, chat_id),
    )
    raw = list(await cursor.fetchall())
    by_id: dict[int, dict[str, Any]] = {}
    for row in raw:
        offices = [value for value in str(row["offices"] or "").split(",") if value]
        by_id[int(row["user_id"])] = {
            "user_id": int(row["user_id"]),
            "name": str(row["full_name"] or row["username"] or row["user_id"]),
            "username": str(row["username"] or ""),
            "points": int(row["points"] or 0),
            "updated_at": int(row["updated_at"] or 0),
            "offices": offices,
            "had_access": bool(offices),
        }
    if thief_id not in by_id:
        row = await _player_row(core, chat_id, thief_id)
        if row is not None:
            offices = await gov._user_offices(core, chat_id, thief_id)
            by_id[thief_id] = {
                "user_id": thief_id,
                "name": str(row["full_name"] or row["username"] or thief_id),
                "username": str(row["username"] or ""),
                "points": int(row["points"] or 0),
                "updated_at": int(row["updated_at"] or 0),
                "offices": offices,
                "had_access": bool(offices),
            }
    officials = [item for item in by_id.values() if item["had_access"]]
    others = [item for item in by_id.values() if not item["had_access"]]
    rng = _rng(str(theft["theft_id"]), "suspects")
    rng.shuffle(officials)
    rng.shuffle(others)
    selected = officials[:8]
    if thief_id not in {item["user_id"] for item in selected} and thief_id in by_id:
        if len(selected) >= 8:
            selected[-1] = by_id[thief_id]
        else:
            selected.append(by_id[thief_id])
    while len(selected) < 5 and others:
        selected.append(others.pop())
    rng.shuffle(selected)
    return selected


async def create_case(core: Any, theft: Any) -> None:
    await ensure_schema(core)
    if str(theft["status"]) != "pending":
        return
    theft_id = str(theft["theft_id"])
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT 1 FROM government_theft_cases_v163 WHERE theft_id=?",
        (theft_id,),
    )
    if await cursor.fetchone() is not None:
        return
    suspects = await _candidate_rows(core, theft)
    if not suspects:
        return
    chat_id = int(theft["chat_id"])
    started_at = int(theft["started_at"])
    amount = int(theft["amount"])
    cursor = await conn.execute(
        "SELECT COALESCE(MAX(case_no),0)+1 AS value FROM government_theft_cases_v163 WHERE chat_id=?",
        (chat_id,),
    )
    case_no = int((await cursor.fetchone())["value"])
    rng = _rng(theft_id, "matches")
    decoys = [item["user_id"] for item in suspects if int(item["user_id"]) != int(theft["thief_id"])]
    route_ids = {int(theft["thief_id"])}
    audit_ids = {int(theft["thief_id"])}
    if decoys:
        route_ids.add(rng.choice(decoys))
    remaining = [value for value in decoys if value not in route_ids]
    if remaining:
        audit_ids.add(rng.choice(remaining))
    elif decoys:
        audit_ids.add(rng.choice(decoys))
    now = _now()
    async with core.db.lock:
        await conn.execute(
            """
            INSERT OR IGNORE INTO government_theft_cases_v163(
                theft_id,chat_id,case_no,status,original_amount,loot_remaining,
                created_at,resolve_at,updated_at
            ) VALUES(?,?,?,'investigation',?,?,?,?,?)
            """,
            (theft_id, chat_id, case_no, amount, amount, started_at, int(theft["resolve_at"]), now),
        )
        for index, item in enumerate(suspects, start=1):
            cursor = await conn.execute(
                "SELECT COUNT(*) AS value FROM score_log WHERE chat_id=? AND user_id=? AND created_at BETWEEN ? AND ?",
                (chat_id, int(item["user_id"]), started_at - 2 * 60 * 60, started_at),
            )
            activity = int((await cursor.fetchone())["value"])
            await conn.execute(
                """
                INSERT OR IGNORE INTO government_theft_suspects_v163(
                    theft_id,user_id,suspect_code,display_name,username,points_before,
                    updated_at_before,had_access,offices_json,activity_before,
                    route_match,audit_match,framed
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,0)
                """,
                (
                    theft_id,
                    int(item["user_id"]),
                    f"S{index}",
                    str(item["name"]),
                    str(item["username"]),
                    int(item["points"]),
                    int(item["updated_at"]),
                    1 if item["had_access"] else 0,
                    _dumps(list(item["offices"])),
                    activity,
                    1 if int(item["user_id"]) in route_ids else 0,
                    1 if int(item["user_id"]) in audit_ids else 0,
                ),
            )
        for office_key in QUEST_ROLES:
            assignee = await _holder(core, chat_id, office_key, started_at)
            if office_key == "finance":
                task = _finance_task(theft_id, amount)
            elif office_key == "auditor":
                task = _audit_task(theft_id, amount, started_at)
            else:
                task = {"kind": office_key}
            await conn.execute(
                """
                INSERT OR IGNORE INTO government_theft_tasks_v163(
                    theft_id,office_key,assignee_id,delegate_id,status,attempts,
                    available_at,completed_at,task_json,result_json,clue
                ) VALUES(?,?,?,0,'pending',0,?,0,?,'{}','')
                """,
                (theft_id, office_key, assignee, started_at, _dumps(task)),
            )
        await conn.commit()


async def backfill_pending(core: Any) -> None:
    await ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT t.* FROM government_thefts_v131 t
        LEFT JOIN government_theft_cases_v163 c ON c.theft_id=t.theft_id
        WHERE t.status='pending' AND c.theft_id IS NULL
        ORDER BY t.started_at
        """
    )
    for theft in await cursor.fetchall():
        await create_case(core, theft)


async def _case(core: Any, chat_id: int, theft_id: str) -> Any:
    await ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_theft_cases_v163 WHERE theft_id=? AND chat_id=?",
        (str(theft_id), int(chat_id)),
    )
    row = await cursor.fetchone()
    if row is None:
        raise ValueError("Уголовное дело не найдено.")
    return row


async def _theft(core: Any, chat_id: int, theft_id: str) -> Any:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_thefts_v131 WHERE theft_id=? AND chat_id=?",
        (str(theft_id), int(chat_id)),
    )
    row = await cursor.fetchone()
    if row is None:
        raise ValueError("Операция казны не найдена.")
    return row


async def _tasks(core: Any, theft_id: str) -> list[Any]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_theft_tasks_v163 WHERE theft_id=? ORDER BY CASE office_key WHEN 'finance' THEN 1 WHEN 'auditor' THEN 2 WHEN 'oversight' THEN 3 ELSE 4 END",
        (str(theft_id),),
    )
    return list(await cursor.fetchall())


async def _suspects(core: Any, theft_id: str) -> list[Any]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_theft_suspects_v163 WHERE theft_id=? ORDER BY suspect_code",
        (str(theft_id),),
    )
    return list(await cursor.fetchall())


def _done(task: Any) -> bool:
    return str(task["status"]) in {"completed", "failed"}


def _unlocked(office_key: str, tasks: dict[str, Any]) -> bool:
    if office_key in {"finance", "auditor"}:
        return True
    if office_key == "oversight":
        return _done(tasks["finance"]) or _done(tasks["auditor"])
    if office_key == "prosecutor":
        return all(_done(tasks[key]) for key in ("finance", "auditor", "oversight"))
    return False


async def _append_clue(core: Any, theft_id: str, office_key: str, text: str, confidence: str) -> None:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT public_clues_json FROM government_theft_cases_v163 WHERE theft_id=?",
        (str(theft_id),),
    )
    row = await cursor.fetchone()
    clues = _loads(row["public_clues_json"] if row else "[]", [])
    clues.append(
        {
            "office_key": str(office_key),
            "title": ROLE_TITLES.get(str(office_key), str(office_key)),
            "icon": ROLE_ICONS.get(str(office_key), "🔎"),
            "text": str(text),
            "confidence": str(confidence),
            "created_at": _now(),
        }
    )
    await conn.execute(
        "UPDATE government_theft_cases_v163 SET public_clues_json=?,updated_at=? WHERE theft_id=?",
        (_dumps(clues), _now(), str(theft_id)),
    )


async def _compat_evidence(
    core: Any,
    theft_id: str,
    office_key: str,
    investigator_id: int,
    points: int,
    clue: str,
) -> None:
    conn = core.db._require_connection()
    await conn.execute(
        """
        INSERT INTO government_theft_evidence_v153(
            theft_id,office_key,investigator_id,points,clue,created_at
        ) VALUES(?,?,?,?,?,?)
        ON CONFLICT(theft_id,office_key) DO UPDATE SET
          investigator_id=excluded.investigator_id,
          points=MAX(government_theft_evidence_v153.points,excluded.points),
          clue=excluded.clue,created_at=excluded.created_at
        """,
        (str(theft_id), str(office_key), int(investigator_id), int(points), str(clue), _now()),
    )


async def _task_for_action(core: Any, chat_id: int, user_id: int, theft_id: str, office_key: str) -> tuple[Any, Any, dict[str, Any]]:
    case = await _case(core, chat_id, theft_id)
    theft = await _theft(core, chat_id, theft_id)
    if str(case["status"]) != "investigation" or str(theft["status"]) != "pending":
        raise ValueError("Расследование уже завершено.")
    task_rows = await _tasks(core, theft_id)
    task_map = {str(row["office_key"]): row for row in task_rows}
    if office_key not in task_map:
        raise ValueError("Этап расследования не найден.")
    task = task_map[office_key]
    allowed = int(user_id) in {int(task["assignee_id"] or 0), int(task["delegate_id"] or 0), int(core.DEVELOPER_ID)}
    if not allowed:
        raise PermissionError("Этот этап закреплён за другой государственной структурой.")
    if not _unlocked(office_key, task_map):
        raise ValueError("Сначала должны завершиться предыдущие этапы расследования.")
    if str(task["status"]) in {"completed", "failed"}:
        raise ValueError("Эта структура уже завершила свою часть расследования.")
    if int(task["available_at"] or 0) > _now():
        raise ValueError(f"Повторная проверка доступна через {gov._remaining(int(task['available_at']))}.")
    return case, theft, task_map


async def perform_task(
    core: Any,
    chat_id: int,
    user_id: int,
    theft_id: str,
    office_key: str,
    payload: dict[str, Any],
) -> str:
    office_key = str(office_key)
    if office_key not in {"finance", "auditor", "oversight"}:
        raise ValueError("Неизвестный этап расследования.")
    case, theft, task_map = await _task_for_action(core, chat_id, user_id, theft_id, office_key)
    task = task_map[office_key]
    conn = core.db._require_connection()
    now = _now()
    if office_key in {"finance", "auditor"}:
        data = _loads(task["task_json"], {})
        answer = str(payload.get("answer") or "")
        correct = answer == str(data.get("answer") or "")
        attempts = int(task["attempts"] or 0) + 1
        if not correct and attempts < 2:
            await conn.execute(
                "UPDATE government_theft_tasks_v163 SET attempts=?,available_at=? WHERE theft_id=? AND office_key=?",
                (attempts, now + RETRY_DELAY, str(theft_id), office_key),
            )
            await conn.commit()
            return "Ответ не совпал с контрольными данными. Повторная попытка будет доступна через 5 минут."
        suspects = await _suspects(core, theft_id)
        match_field = "route_match" if office_key == "finance" else "audit_match"
        matched = [str(row["suspect_code"]) for row in suspects if int(row[match_field] or 0)]
        confidence = "strong" if correct else "weak"
        if office_key == "finance":
            clue = (
                f"Денежный маршрут связан с контурами {', '.join(matched)}. "
                + ("Контрольная сумма совпала." if correct else "Часть маршрута восстановлена с низкой точностью.")
            )
        else:
            clue = (
                f"Цифровая подпись журнала связана с контурами {', '.join(matched)}. "
                + ("Подделанная запись подтверждена." if correct else "Подлинность части журнала остаётся спорной.")
            )
        result = {"correct": correct, "matched_codes": matched, "answer": answer}
        status = "completed" if correct else "failed"
        async with core.db.lock:
            await conn.execute(
                """
                UPDATE government_theft_tasks_v163
                SET status=?,attempts=?,completed_at=?,result_json=?,clue=?
                WHERE theft_id=? AND office_key=?
                """,
                (status, attempts, now, _dumps(result), clue, str(theft_id), office_key),
            )
            await _append_clue(core, theft_id, office_key, clue, confidence)
            await _compat_evidence(core, theft_id, office_key, user_id, 3 if correct else 1, clue)
            await conn.commit()
        return clue

    selected_raw = payload.get("suspect_ids") or []
    if not isinstance(selected_raw, list):
        selected_raw = [selected_raw]
    selected = []
    for value in selected_raw:
        try:
            selected.append(int(value))
        except (TypeError, ValueError):
            continue
    selected = list(dict.fromkeys(selected))
    if not 1 <= len(selected) <= 2:
        raise ValueError("Надзор должен выбрать одного или двух приоритетных подозреваемых.")
    suspects = await _suspects(core, theft_id)
    valid_ids = {int(row["user_id"]) for row in suspects}
    if any(value not in valid_ids for value in selected):
        raise ValueError("Выбран неизвестный подозреваемый.")
    thief_id = int(theft["thief_id"])
    contains = thief_id in selected
    codes = [str(row["suspect_code"]) for row in suspects if int(row["user_id"]) in selected]
    clue = (
        f"Надзор сформировал приоритетный круг: {', '.join(codes)}. "
        + ("Версия согласуется с финансовыми и техническими следами." if contains else "Версия содержит противоречия и требует особой проверки прокуратуры.")
    )
    result = {"selected_ids": selected, "selected_codes": codes, "contains_thief": contains}
    async with core.db.lock:
        await conn.execute(
            """
            UPDATE government_theft_tasks_v163
            SET status='completed',attempts=attempts+1,completed_at=?,result_json=?,clue=?
            WHERE theft_id=? AND office_key='oversight'
            """,
            (now, _dumps(result), clue, str(theft_id)),
        )
        await conn.execute(
            "UPDATE government_theft_cases_v163 SET shortlist_json=?,updated_at=? WHERE theft_id=?",
            (_dumps(selected), now, str(theft_id)),
        )
        await _append_clue(core, theft_id, "oversight", clue, "strong" if contains else "weak")
        await _compat_evidence(core, theft_id, "oversight", user_id, 2 if contains else 1, clue)
        await conn.commit()
    return clue


async def accuse(
    core: Any,
    bot: Any,
    chat_id: int,
    user_id: int,
    theft_id: str,
    suspect_id: int,
    evidence_keys: list[str],
) -> str:
    case, theft, task_map = await _task_for_action(core, chat_id, user_id, theft_id, "prosecutor")
    evidence = {str(value) for value in evidence_keys}
    if not {"finance", "auditor", "oversight"}.issubset(evidence):
        raise ValueError("Для обвинения приложи материалы Минфина, Счётной палаты и Надзора.")
    suspects = await _suspects(core, theft_id)
    suspect = next((row for row in suspects if int(row["user_id"]) == int(suspect_id)), None)
    if suspect is None:
        raise ValueError("Подозреваемый не найден в материалах дела.")
    task = task_map["prosecutor"]
    now = _now()
    correct = int(suspect_id) == int(theft["thief_id"])
    conn = core.db._require_connection()
    if correct:
        clue = f"Прокуратура связала все доказательства с контуром {suspect['suspect_code']}. Обвинение подтверждено."
        async with core.db.lock:
            await conn.execute(
                """
                UPDATE government_theft_tasks_v163
                SET status='completed',attempts=attempts+1,completed_at=?,result_json=?,clue=?
                WHERE theft_id=? AND office_key='prosecutor'
                """,
                (now, _dumps({"accused_id": int(suspect_id), "correct": True}), clue, str(theft_id)),
            )
            await conn.execute(
                "UPDATE government_theft_cases_v163 SET status='caught',updated_at=? WHERE theft_id=?",
                (now, str(theft_id)),
            )
            await _append_clue(core, theft_id, "prosecutor", clue, "confirmed")
            await _compat_evidence(core, theft_id, "prosecutor", user_id, 3, clue)
            await conn.commit()
        fresh = await _theft(core, chat_id, theft_id)
        await crisis._catch_theft(core, bot, fresh, int(user_id))
        return "Обвинение доказано. Казнокрад раскрыт, деньги возвращены в казну."

    attempts = int(task["attempts"] or 0) + 1
    wrong = int(case["wrong_accusations"] or 0) + 1
    accused_name = str(suspect["display_name"])
    compensation = 50
    async with core.db.lock:
        cursor = await conn.execute(
            "UPDATE government_state_v127 SET treasury=treasury-?,updated_at=? WHERE chat_id=? AND treasury>=?",
            (compensation, now, int(chat_id), compensation),
        )
        if int(cursor.rowcount or 0) > 0:
            await conn.execute(
                "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                (compensation, now, int(chat_id), int(suspect_id)),
            )
            await conn.execute(
                "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                (int(chat_id), int(suspect_id), compensation, "false_accusation_compensation_v163", now),
            )
        await conn.execute(
            """
            UPDATE government_theft_tasks_v163
            SET attempts=?,available_at=?,result_json=?
            WHERE theft_id=? AND office_key='prosecutor'
            """,
            (attempts, now + ACCUSATION_RETRY, _dumps({"accused_id": int(suspect_id), "correct": False}), str(theft_id)),
        )
        await conn.execute(
            "UPDATE government_theft_cases_v163 SET wrong_accusations=?,last_accusation_at=?,updated_at=? WHERE theft_id=?",
            (wrong, now, now, str(theft_id)),
        )
        if wrong >= MAX_WRONG_ACCUSATIONS:
            new_resolve = min(int(theft["resolve_at"]), now + 5 * 60)
            await conn.execute(
                "UPDATE government_theft_cases_v163 SET resolve_at=? WHERE theft_id=?",
                (new_resolve, str(theft_id)),
            )
            await conn.execute(
                "UPDATE government_thefts_v131 SET resolve_at=? WHERE theft_id=? AND status='pending'",
                (new_resolve, str(theft_id)),
            )
        await conn.commit()
    await gov._publish(
        bot,
        int(chat_id),
        "⚖️ <b>ОБВИНЕНИЕ НЕ ПОДТВЕРЖДЕНО</b>\n\n"
        f"Подозреваемый: <b>{html.escape(accused_name)}</b>\n"
        f"Компенсация: <b>{gov._fmt(compensation)}</b> влияния.\n"
        + ("После второй ошибки следы исчезнут через 5 минут." if wrong >= MAX_WRONG_ACCUSATIONS else "Прокуратура сможет пересобрать дело через 15 минут."),
    )
    return "Обвинение оказалось ошибочным. Дело отправлено на повторную проверку."


async def cover_action(
    core: Any,
    chat_id: int,
    user_id: int,
    theft_id: str,
    action_key: str,
    target_id: int = 0,
) -> str:
    case = await _case(core, chat_id, theft_id)
    theft = await _theft(core, chat_id, theft_id)
    if str(case["status"]) != "investigation" or str(theft["status"]) != "pending":
        raise ValueError("Скрывать следы уже поздно.")
    if int(theft["thief_id"]) != int(user_id):
        raise PermissionError("Этот раздел доступен только организатору хищения.")
    action_key = str(action_key)
    if action_key not in COVER_COSTS:
        raise ValueError("Неизвестный способ сокрытия следов.")
    used = _loads(case["cover_actions_json"], [])
    if action_key in used:
        raise ValueError("Этот способ уже использован.")
    if len(used) >= MAX_COVER_ACTIONS:
        raise ValueError("Можно провести не больше двух операций сокрытия.")
    cost = max(1, int(case["original_amount"]) * COVER_COSTS[action_key] // 100)
    if int(case["loot_remaining"]) <= cost:
        raise ValueError("Оставшейся добычи недостаточно для этой операции.")
    conn = core.db._require_connection()
    now = _now()
    payload: dict[str, Any] = {}
    public_clue = ""
    if action_key == "frame_suspect":
        suspects = await _suspects(core, theft_id)
        valid = {int(row["user_id"]) for row in suspects if int(row["user_id"]) != int(user_id)}
        if int(target_id) not in valid:
            raise ValueError("Выбери другого участника из списка подозреваемых.")
        payload["target_id"] = int(target_id)
    used.append(action_key)
    new_loot = max(0, int(case["loot_remaining"]) - cost)
    async with core.db.lock:
        await conn.execute(
            """
            INSERT INTO government_theft_cover_actions_v163(
                theft_id,actor_id,action_key,payload_json,cost,created_at
            ) VALUES(?,?,?,?,?,?)
            """,
            (str(theft_id), int(user_id), action_key, _dumps(payload), cost, now),
        )
        await conn.execute(
            "UPDATE government_theft_cases_v163 SET loot_remaining=?,cover_actions_json=?,updated_at=? WHERE theft_id=?",
            (new_loot, _dumps(used), now, str(theft_id)),
        )
        if action_key == "split_route":
            await conn.execute(
                "UPDATE government_theft_tasks_v163 SET task_json=? WHERE theft_id=? AND office_key='finance' AND status='pending'",
                (_dumps(_finance_task(str(theft_id), int(case["original_amount"]), True)), str(theft_id)),
            )
        elif action_key == "forge_log":
            await conn.execute(
                "UPDATE government_theft_tasks_v163 SET task_json=? WHERE theft_id=? AND office_key='auditor' AND status='pending'",
                (_dumps(_audit_task(str(theft_id), int(case["original_amount"]), int(case["created_at"]), True)), str(theft_id)),
            )
        elif action_key == "frame_suspect":
            await conn.execute(
                "UPDATE government_theft_suspects_v163 SET framed=CASE WHEN user_id=? THEN 1 ELSE framed END WHERE theft_id=?",
                (int(target_id), str(theft_id)),
            )
            await conn.execute(
                "UPDATE government_theft_cases_v163 SET framed_user_id=? WHERE theft_id=?",
                (int(target_id), str(theft_id)),
            )
        elif action_key == "destroy_trace":
            new_resolve = max(now + 10 * 60, int(case["resolve_at"]) - 15 * 60)
            await conn.execute(
                "UPDATE government_theft_cases_v163 SET resolve_at=? WHERE theft_id=?",
                (new_resolve, str(theft_id)),
            )
            await conn.execute(
                "UPDATE government_thefts_v131 SET resolve_at=? WHERE theft_id=? AND status='pending'",
                (new_resolve, str(theft_id)),
            )
            public_clue = "Система обнаружила уничтожение журналов: время расследования сократилось на 15 минут."
            await _append_clue(core, theft_id, "system", public_clue, "strong")
        await conn.commit()
    labels = {
        "split_route": "Денежный маршрут разделён на дополнительные контуры.",
        "forge_log": "В журнал казны добавлена поддельная запись.",
        "frame_suspect": "На другого подозреваемого создан ложный след.",
        "destroy_trace": "Часть журналов уничтожена, срок следствия сокращён.",
    }
    return f"{labels[action_key]} Потрачено {gov._fmt(cost)} из будущей добычи."


async def delegate_task(
    core: Any,
    chat_id: int,
    user_id: int,
    theft_id: str,
    office_key: str,
    target_id: int,
) -> str:
    case = await _case(core, chat_id, theft_id)
    offices = await gov._user_offices(core, chat_id, user_id)
    if int(user_id) != int(core.DEVELOPER_ID) and "president" not in offices:
        raise PermissionError("Временного следователя назначает Президент реальности.")
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_theft_tasks_v163 WHERE theft_id=? AND office_key=?",
        (str(theft_id), str(office_key)),
    )
    task = await cursor.fetchone()
    if task is None or str(task["status"]) in {"completed", "failed"}:
        raise ValueError("Этот этап уже завершён или не существует.")
    if int(task["assignee_id"] or 0) and _now() < int(case["created_at"]) + DELEGATION_DELAY:
        raise ValueError("Действующему руководителю структуры ещё предоставлено время на проверку.")
    player = await _player_row(core, chat_id, target_id)
    if player is None:
        raise ValueError("Участник не найден в этой беседе.")
    await conn.execute(
        "UPDATE government_theft_tasks_v163 SET delegate_id=? WHERE theft_id=? AND office_key=?",
        (int(target_id), str(theft_id), str(office_key)),
    )
    await conn.commit()
    return f"Временный следователь назначен на этап «{ROLE_TITLES.get(str(office_key), office_key)}»."


async def mark_caught(core: Any, theft_id: str) -> None:
    await ensure_schema(core)
    conn = core.db._require_connection()
    await conn.execute(
        "UPDATE government_theft_cases_v163 SET status='caught',updated_at=? WHERE theft_id=?",
        (_now(), str(theft_id)),
    )
    await conn.commit()


async def resolve_escape(core: Any, bot: Any, theft: Any) -> bool:
    await ensure_schema(core)
    theft_id = str(theft["theft_id"])
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_theft_cases_v163 WHERE theft_id=?",
        (theft_id,),
    )
    case = await cursor.fetchone()
    if case is None or str(case["status"]) != "investigation":
        return False
    chat_id = int(theft["chat_id"])
    thief_id = int(theft["thief_id"])
    original = int(case["original_amount"])
    payout = int(case["loot_remaining"])
    now = _now()
    async with core.db.lock:
        cursor = await conn.execute(
            "UPDATE government_thefts_v131 SET status='escaped',resolved_at=? WHERE theft_id=? AND status='pending'",
            (now, theft_id),
        )
        if int(cursor.rowcount or 0) <= 0:
            await conn.rollback()
            return True
        await conn.execute(
            "UPDATE government_theft_cases_v163 SET status='escaped',updated_at=? WHERE theft_id=?",
            (now, theft_id),
        )
        if payout > 0:
            await conn.execute(
                "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                (payout, now, chat_id, thief_id),
            )
            await conn.execute(
                "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                (chat_id, thief_id, payout, "treasury_theft_quest_v163", now),
            )
        await conn.commit()
    burned = max(0, original - payout)
    await gov._publish(
        bot,
        chat_id,
        "🕶 <b>КАЗНОКРАД УШЁЛ ОТ СЛЕДСТВИЯ</b>\n\n"
        f"Потеря казны: <b>{gov._fmt(original)}</b> влияния.\n"
        f"Преступник сохранил: <b>{gov._fmt(payout)}</b>.\n"
        + (f"На сокрытие следов потрачено: <b>{gov._fmt(burned)}</b>." if burned else "Следствие не смогло собрать обвинение."),
    )
    return True


async def _current_points(core: Any, chat_id: int, user_ids: list[int]) -> dict[int, int]:
    if not user_ids:
        return {}
    conn = core.db._require_connection()
    placeholders = ",".join("?" for _ in user_ids)
    cursor = await conn.execute(
        f"SELECT user_id,points FROM players WHERE chat_id=? AND user_id IN ({placeholders})",
        (int(chat_id), *[int(value) for value in user_ids]),
    )
    return {int(row["user_id"]): int(row["points"] or 0) for row in await cursor.fetchall()}


def _movement(delta: int) -> str:
    if delta >= 500:
        return "крупное необъяснимое увеличение"
    if delta > 0:
        return "небольшое увеличение"
    if delta <= -500:
        return "крупный вывод или вложение"
    if delta < 0:
        return "небольшое уменьшение"
    return "без заметного изменения"


async def serialize(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    await backfill_pending(core)
    conn = core.db._require_connection()
    now = _now()
    offices = await gov._user_offices(core, chat_id, user_id)
    cursor = await conn.execute(
        """
        SELECT c.*,t.thief_id,t.percent,t.amount,t.status AS theft_status,t.started_at,
               t.resolve_at AS theft_resolve_at,t.caught_at,t.resolved_at
        FROM government_theft_cases_v163 c
        JOIN government_thefts_v131 t ON t.theft_id=c.theft_id
        WHERE c.chat_id=?
        ORDER BY c.created_at DESC LIMIT 12
        """,
        (int(chat_id),),
    )
    cases = []
    for row in await cursor.fetchall():
        theft_id = str(row["theft_id"])
        tasks_list = await _tasks(core, theft_id)
        tasks = {str(task["office_key"]): task for task in tasks_list}
        suspects = await _suspects(core, theft_id)
        current = await _current_points(core, chat_id, [int(item["user_id"]) for item in suspects])
        task_states = []
        my_tasks = []
        for office_key in QUEST_ROLES:
            task = tasks[office_key]
            assignee_id = int(task["delegate_id"] or task["assignee_id"] or 0)
            assignee_name = "Вакантно"
            if assignee_id:
                player = await _player_row(core, chat_id, assignee_id)
                if player is not None:
                    assignee_name = str(player["full_name"] or player["username"] or assignee_id)
            unlocked = _unlocked(office_key, tasks)
            task_states.append(
                {
                    "office_key": office_key,
                    "title": ROLE_TITLES[office_key],
                    "icon": ROLE_ICONS[office_key],
                    "status": str(task["status"]),
                    "attempts": int(task["attempts"] or 0),
                    "assignee_id": assignee_id,
                    "assignee_name": assignee_name,
                    "unlocked": unlocked,
                    "remaining": gov._remaining(int(task["available_at"])) if int(task["available_at"] or 0) > now else "",
                }
            )
            allowed = int(user_id) in {
                int(task["assignee_id"] or 0),
                int(task["delegate_id"] or 0),
                int(core.DEVELOPER_ID),
            }
            if not allowed or str(row["status"]) != "investigation":
                continue
            data = _loads(task["task_json"], {})
            data.pop("answer", None)
            my_task: dict[str, Any] = {
                "office_key": office_key,
                "title": ROLE_TITLES[office_key],
                "icon": ROLE_ICONS[office_key],
                "status": str(task["status"]),
                "attempts": int(task["attempts"] or 0),
                "unlocked": unlocked,
                "available": int(task["available_at"] or 0) <= now,
                "remaining": gov._remaining(int(task["available_at"])) if int(task["available_at"] or 0) > now else "",
                "task": data,
            }
            if office_key in {"oversight", "prosecutor"}:
                finance_result = _loads(tasks["finance"]["result_json"], {})
                audit_result = _loads(tasks["auditor"]["result_json"], {})
                finance_codes = set(finance_result.get("matched_codes") or [])
                audit_codes = set(audit_result.get("matched_codes") or [])
                suspect_items = []
                for suspect in suspects:
                    code = str(suspect["suspect_code"])
                    delta = int(current.get(int(suspect["user_id"]), int(suspect["points_before"]))) - int(suspect["points_before"])
                    risk = 0
                    if int(suspect["had_access"]):
                        risk += 25
                    if code in finance_codes:
                        risk += 30
                    if code in audit_codes:
                        risk += 25
                    if int(suspect["framed"]):
                        risk += 18
                    if int(suspect["activity_before"] or 0) >= 3:
                        risk += 10
                    suspect_items.append(
                        {
                            "user_id": int(suspect["user_id"]),
                            "code": code,
                            "name": str(suspect["display_name"]),
                            "username": str(suspect["username"] or ""),
                            "had_access": bool(int(suspect["had_access"])),
                            "offices": _loads(suspect["offices_json"], []),
                            "activity": "высокая" if int(suspect["activity_before"] or 0) >= 3 else "обычная",
                            "balance_trace": _movement(delta),
                            "route_link": code in finance_codes if _done(tasks["finance"]) else None,
                            "audit_link": code in audit_codes if _done(tasks["auditor"]) else None,
                            "anomaly": bool(int(suspect["framed"])),
                            "risk": min(99, risk),
                        }
                    )
                my_task["suspects"] = suspect_items
                my_task["clues"] = _loads(row["public_clues_json"], [])
            my_tasks.append(my_task)
        is_thief = int(row["thief_id"]) == int(user_id) and str(row["status"]) == "investigation"
        cover_used = _loads(row["cover_actions_json"], [])
        thief_panel = None
        if is_thief:
            thief_panel = {
                "loot_remaining": int(row["loot_remaining"]),
                "used": cover_used,
                "max_actions": MAX_COVER_ACTIONS,
                "actions": [
                    {"key": "split_route", "title": "Разделить денежный маршрут", "cost_percent": 10, "available": "split_route" not in cover_used},
                    {"key": "forge_log", "title": "Подделать журнал казны", "cost_percent": 10, "available": "forge_log" not in cover_used},
                    {"key": "frame_suspect", "title": "Подставить подозреваемого", "cost_percent": 15, "available": "frame_suspect" not in cover_used},
                    {"key": "destroy_trace", "title": "Уничтожить часть следов", "cost_percent": 20, "available": "destroy_trace" not in cover_used},
                ],
                "targets": [
                    {"user_id": int(item["user_id"]), "code": str(item["suspect_code"]), "name": str(item["display_name"])}
                    for item in suspects if int(item["user_id"]) != int(user_id)
                ],
            }
        can_delegate = int(user_id) == int(core.DEVELOPER_ID) or "president" in offices
        delegate_tasks = []
        if can_delegate and str(row["status"]) == "investigation":
            for task in tasks_list:
                if str(task["status"]) in {"completed", "failed"}:
                    continue
                if not int(task["assignee_id"] or 0) or now >= int(row["created_at"]) + DELEGATION_DELAY:
                    delegate_tasks.append(str(task["office_key"]))
        cases.append(
            {
                "theft_id": theft_id,
                "case_no": int(row["case_no"]),
                "status": str(row["status"]),
                "theft_status": str(row["theft_status"]),
                "amount": int(row["original_amount"]),
                "percent": int(row["percent"]),
                "created_at": int(row["created_at"]),
                "resolve_at": int(row["resolve_at"]),
                "remaining": gov._remaining(int(row["resolve_at"])) if str(row["status"]) == "investigation" else "",
                "suspect_count": len(suspects),
                "wrong_accusations": int(row["wrong_accusations"] or 0),
                "clues": _loads(row["public_clues_json"], []),
                "tasks": task_states,
                "my_tasks": my_tasks,
                "thief_panel": thief_panel,
                "can_delegate": can_delegate,
                "delegate_tasks": delegate_tasks,
                "delegate_targets": [
                    {"user_id": int(item["user_id"]), "name": str(item["display_name"])} for item in suspects
                ] if can_delegate else [],
            }
        )
    return {
        "version": VERSION,
        "roles": [
            {"key": key, "title": ROLE_TITLES[key], "icon": ROLE_ICONS[key]} for key in QUEST_ROLES
        ],
        "cases": cases,
    }
