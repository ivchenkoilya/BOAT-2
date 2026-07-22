from __future__ import annotations

import html
import json
import secrets
from typing import Any

import government_institutions_v128 as inst
import government_v127 as gov
import sanctions_v126 as sanctions

from government_oversight_deputy_v167_data import DAY, WEEK, OFFICE_KEY, _access, _person, _usage

async def _complaint(core: Any, bot: Any, chat_id: int, author_id: int, data: dict[str, Any]) -> str:
    target_id = gov._as_int(data.get("target_user_id"))
    target, author = await _person(core, chat_id, target_id), await _person(core, chat_id, author_id)
    reason, evidence = str(data.get("reason") or "").strip(), str(data.get("evidence") or "").strip()
    if target_id == author_id:
        raise ValueError("Нельзя подать жалобу на самого себя.")
    if not 10 <= len(reason) <= 500 or len(evidence) > 700:
        raise ValueError("Жалоба: 10–500 символов, доказательства — до 700.")
    case_id, now = secrets.token_urlsafe(10), gov._now()
    conn = core.db._require_connection()
    await conn.execute(
        """
        INSERT INTO government_cases_v128(
          case_id,chat_id,institution,case_type,title,description,target_user_id,status,
          payload_json,created_by,created_at,updated_at,resolved_at
        ) VALUES(?,?,'oversight_deputy','complaint',?,?,?,'open',?,?,?, ?,0)
        """,
        (case_id, chat_id, f"Жалоба на {target['name']}"[:140], reason, target_id,
         json.dumps({"evidence": evidence, "author_name": author["name"]}, ensure_ascii=False),
         author_id, now, now),
    )
    await conn.commit()
    await gov._publish(bot, chat_id, f"📨 <b>ЖАЛОБА ПЕРЕДАНА В НАДЗОР</b>\n\nЗаявитель: <b>{html.escape(author['name'])}</b>\nПроверяемый: <b>{html.escape(target['name'])}</b>\nОснование: {html.escape(reason)}")
    return "Жалоба зарегистрирована."

async def _inspection(core: Any, bot: Any, chat_id: int, actor_id: int, data: dict[str, Any]) -> str:
    access = await _access(core, chat_id, actor_id)
    if not access["can_manage"]:
        raise PermissionError("Проверки доступны руководству Надзора.")
    used, _ = await _usage(core, chat_id, actor_id, "deputy_inspection", DAY)
    limit = 999 if access["is_admin"] else 3 if access["is_head"] else 1
    if used >= limit:
        raise ValueError("Лимит внеплановых проверок за 24 часа исчерпан.")
    complaint_id = str(data.get("complaint_id") or "")
    target_id = gov._as_int(data.get("target_user_id"))
    title = str(data.get("title") or "Проверка на гондонизм").strip()
    facts = str(data.get("facts") or "").strip()
    conn = core.db._require_connection()
    if complaint_id:
        cursor = await conn.execute(
            "SELECT target_user_id,payload_json FROM government_cases_v128 WHERE chat_id=? AND case_id=? AND case_type='complaint'",
            (chat_id, complaint_id),
        )
        complaint = await cursor.fetchone()
        if complaint is None:
            raise ValueError("Жалоба не найдена.")
        target_id = int(complaint["target_user_id"])
        payload = gov._json(complaint["payload_json"], {})
        payload["assigned_to"] = actor_id
        await conn.execute(
            "UPDATE government_cases_v128 SET status='investigating',payload_json=?,updated_at=? WHERE case_id=?",
            (json.dumps(payload, ensure_ascii=False), gov._now(), complaint_id),
        )
    target = await _person(core, chat_id, target_id)
    if not 5 <= len(title) <= 140 or not 10 <= len(facts) <= 1200:
        raise ValueError("Название: 5–140 символов, материалы: 10–1200.")
    case_id, now = secrets.token_urlsafe(10), gov._now()
    await conn.execute(
        """
        INSERT INTO government_cases_v128(
          case_id,chat_id,institution,case_type,title,description,target_user_id,status,
          payload_json,created_by,created_at,updated_at,resolved_at
        ) VALUES(?,?,'oversight_deputy','inspection',?,?,?,'open',?,?,?, ?,0)
        """,
        (case_id, chat_id, title, facts, target_id,
         json.dumps({"complaint_id": complaint_id}, ensure_ascii=False), actor_id, now, now),
    )
    await conn.commit()
    await inst._log(core, chat_id, actor_id, OFFICE_KEY, "deputy_inspection", title, facts, target_id, {"case_id": case_id})
    await gov._publish(bot, chat_id, f"🔍 <b>ОТКРЫТА ВНЕПЛАНОВАЯ ПРОВЕРКА</b>\n\nДело: <code>{case_id}</code>\nПроверяемый: <b>{html.escape(target['name'])}</b>\nПредмет: {html.escape(title)}\n\nДо завершения проверки участник не считается виновным.")
    return "Проверка открыта."

async def _warning(core: Any, bot: Any, chat_id: int, actor_id: int, data: dict[str, Any]) -> str:
    access = await _access(core, chat_id, actor_id)
    if not access["can_manage"]:
        raise PermissionError("Предупреждения доступны руководству Надзора.")
    target_id, reason = gov._as_int(data.get("target_user_id")), str(data.get("reason") or "").strip()
    target = await _person(core, chat_id, target_id)
    if not 5 <= len(reason) <= 500:
        raise ValueError("Причина должна содержать 5–500 символов.")
    used, _ = await _usage(core, chat_id, actor_id, "deputy_warning", DAY)
    limit = 999 if access["is_admin"] else 5 if access["is_head"] else 3
    if used >= limit:
        raise ValueError("Суточный лимит предупреждений исчерпан.")
    expires = gov._now() + DAY
    await inst._log(core, chat_id, actor_id, OFFICE_KEY, "deputy_warning", "Подозреваемый гондон", reason, target_id, {"expires_at": expires})
    await gov._publish(bot, chat_id, f"⚠️ <b>ПРЕДУПРЕЖДЕНИЕ НАДЗОРА</b>\n\nУчастник: <b>{html.escape(target['name'])}</b>\nОснование: {html.escape(reason)}\n\nНа 24 часа присвоен статус <b>«Подозреваемый гондон»</b>. Это не санкция.")
    return "Предупреждение выдано на 24 часа."

async def _case(core: Any, bot: Any, chat_id: int, actor_id: int, data: dict[str, Any], action: str) -> str:
    access = await _access(core, chat_id, actor_id)
    if not access["can_manage"]:
        raise PermissionError("Действие доступно руководству Надзора.")
    case_id = str(data.get("case_id") or "")
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_cases_v128 WHERE chat_id=? AND case_id=? AND institution='oversight_deputy' AND case_type='inspection'",
        (chat_id, case_id),
    )
    row = await cursor.fetchone()
    if row is None or str(row["status"]) not in {"open", "referred"}:
        raise ValueError("Открытое дело не найдено.")
    payload = gov._json(row["payload_json"], {})
    if action == "close":
        text = str(data.get("conclusion") or "").strip()
        if not 5 <= len(text) <= 900:
            raise ValueError("Заключение должно содержать 5–900 символов.")
        payload["conclusion"] = text
        await conn.execute("UPDATE government_cases_v128 SET status='closed',payload_json=?,updated_at=?,resolved_at=? WHERE case_id=?", (json.dumps(payload, ensure_ascii=False), gov._now(), gov._now(), case_id))
        complaint_id = str(payload.get("complaint_id") or "")
        if complaint_id:
            await conn.execute("UPDATE government_cases_v128 SET status='closed',updated_at=?,resolved_at=? WHERE case_id=?", (gov._now(), gov._now(), complaint_id))
        message = f"📁 <b>ПРОВЕРКА ЗАВЕРШЕНА</b>\n\nДело: <code>{case_id}</code>\nЗаключение: {html.escape(text)}"
        result = "Дело закрыто."
    else:
        note = str(data.get("note") or "Требуется дополнительная прокурорская проверка").strip()
        new_id, now = secrets.token_urlsafe(10), gov._now()
        await conn.execute(
            """
            INSERT INTO government_cases_v128(
              case_id,chat_id,institution,case_type,title,description,target_user_id,status,
              payload_json,created_by,created_at,updated_at,resolved_at
            ) VALUES(?,?,'prosecutor','investigation',?,?,?,'open',?,?,?, ?,0)
            """,
            (new_id, chat_id, f"Прокурорская проверка: {row['title']}"[:140],
             f"{row['description']}\n\nМатериалы Надзора: {note}"[:1500], int(row["target_user_id"]),
             json.dumps({"oversight_case_id": case_id}, ensure_ascii=False), actor_id, now, now),
        )
        payload["conclusion"] = note
        await conn.execute("UPDATE government_cases_v128 SET status='referred',payload_json=?,updated_at=? WHERE case_id=?", (json.dumps(payload, ensure_ascii=False), now, case_id))
        message = f"🛡 <b>МАТЕРИАЛЫ ПЕРЕДАНЫ В ПРОКУРАТУРУ</b>\n\nДело Надзора: <code>{case_id}</code>\nПрокурорское дело: <code>{new_id}</code>"
        result = "Материалы переданы прокурору."
    await conn.commit()
    await gov._publish(bot, chat_id, message)
    return result

async def _sanction(core: Any, bot: Any, chat_id: int, actor_id: int, data: dict[str, Any]) -> str:
    access = await _access(core, chat_id, actor_id)
    if not access["can_manage"]:
        raise PermissionError("Предлагать санкции может руководство Надзора.")
    case_id = str(data.get("case_id") or "")
    conn = core.db._require_connection()
    cursor = await conn.execute("SELECT * FROM government_cases_v128 WHERE chat_id=? AND case_id=? AND institution='oversight_deputy' AND case_type='inspection'", (chat_id, case_id))
    row = await cursor.fetchone()
    if row is None or str(row["status"]) not in {"open", "referred"}:
        raise ValueError("Дело не найдено.")
    types = [str(x) for x in data.get("types", []) if str(x) in sanctions.SANCTION_TYPES]
    duration, reason = gov._as_int(data.get("duration"), DAY), str(data.get("reason") or row["description"]).strip()
    if not types or duration not in sanctions.ALLOWED_DURATIONS or not 10 <= len(reason) <= 500:
        raise ValueError("Выбери санкции, допустимый срок и обоснование 10–500 символов.")
    if not await gov._deputy_ids(core, chat_id):
        raise ValueError("Сначала необходимо избрать Госдуму.")
    number, bill_id, now = await gov._next_number(core, chat_id, "bill_seq"), secrets.token_urlsafe(12), gov._now()
    bill_payload = {"target_user_id": int(row["target_user_id"]), "types": types, "duration": duration, "reason": reason, "oversight_case_id": case_id}
    await conn.execute(
        """
        INSERT INTO government_bills_v127(
          bill_id,chat_id,number,title,description,bill_type,payload_json,author_id,
          status,created_at,voting_ends_at,president_review_ends_at,resolved_at
        ) VALUES(?,?,?,?,?,'sanction',?,?,'voting',?,?,0,0)
        """,
        (bill_id, chat_id, number, f"Санкции по делу {case_id}"[:120], reason,
         json.dumps(bill_payload, ensure_ascii=False), actor_id, now, now + gov.BILL_VOTING_SECONDS),
    )
    payload = gov._json(row["payload_json"], {})
    payload.update({"bill_id": bill_id, "conclusion": "Санкции предложены Госдуме."})
    await conn.execute("UPDATE government_cases_v128 SET status='sanction_bill',payload_json=?,updated_at=? WHERE case_id=?", (json.dumps(payload, ensure_ascii=False), now, case_id))
    await conn.commit()
    await gov._publish(bot, chat_id, f"🚨 <b>САНКЦИОННОЕ ПРЕДЛОЖЕНИЕ №{number}</b>\n\nДело: <code>{case_id}</code>\nОснование: {html.escape(reason)}\n\nЗаместитель не наказывает самостоятельно — решение принимает Госдума.")
    return f"Предложение №{number} передано в Госдуму."

async def _report(core: Any, bot: Any, chat_id: int, actor_id: int) -> str:
    access = await _access(core, chat_id, actor_id)
    if not access["can_manage"]:
        raise PermissionError("Отчёт доступен руководству Надзора.")
    used, latest = await _usage(core, chat_id, actor_id, "deputy_weekly_report", WEEK)
    if used and not access["is_admin"]:
        raise ValueError("Следующий отчёт будет доступен через 7 дней после предыдущего.")
    conn = core.db._require_connection()
    since = gov._now() - WEEK
    async def count(sql: str, params: tuple[Any, ...]) -> int:
        cursor = await conn.execute(sql, params)
        return int((await cursor.fetchone())["amount"])
    complaints = await count("SELECT COUNT(*) amount FROM government_cases_v128 WHERE chat_id=? AND institution='oversight_deputy' AND case_type='complaint' AND created_at>=?", (chat_id, since))
    inspections = await count("SELECT COUNT(*) amount FROM government_cases_v128 WHERE chat_id=? AND institution='oversight_deputy' AND case_type='inspection' AND created_at>=?", (chat_id, since))
    closed = await count("SELECT COUNT(*) amount FROM government_cases_v128 WHERE chat_id=? AND institution='oversight_deputy' AND case_type='inspection' AND status='closed' AND updated_at>=?", (chat_id, since))
    warnings = await count("SELECT COUNT(*) amount FROM government_power_log_v128 WHERE chat_id=? AND action_key='deputy_warning' AND created_at>=?", (chat_id, since))
    await inst._log(core, chat_id, actor_id, OFFICE_KEY, "deputy_weekly_report", "Еженедельный отчёт", f"Жалобы {complaints}; проверки {inspections}; предупреждения {warnings}; закрыто {closed}")
    await gov._publish(bot, chat_id, f"📊 <b>ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ НАДЗОРА</b>\n\nЖалоб: <b>{complaints}</b>\nПроверок: <b>{inspections}</b>\nПредупреждений: <b>{warnings}</b>\nЗакрыто дел: <b>{closed}</b>")
    return "Отчёт опубликован."
