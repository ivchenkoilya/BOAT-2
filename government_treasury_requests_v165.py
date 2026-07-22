from __future__ import annotations

import html
import secrets
from pathlib import Path
from typing import Any

import government_mandate_luxury_v147 as luxury
import government_treasury_management_v164 as treasury
import government_v127 as gov

VERSION = "Reality 165 · Запросы госструктур в казну"
ASSET_JS = Path(__file__).resolve().parent / "governmentapp_v127" / "treasury-requests-v165.js"
ASSET_CSS = Path(__file__).resolve().parent / "governmentapp_v127" / "treasury-requests-v165.css"
PRIORITIES = {"normal": "Обычный", "urgent": "Срочный"}
STRUCTURE_REQUEST_ROLES = {
    "presidential_admin": ("president", "press", "security"),
    "duma": ("chair", "deputy"),
    "finance_ministry": ("finance", "central_bank", "auditor"),
    "oversight": ("oversight", "prosecutor", "supreme_court", "auditor"),
    "election_commission": ("cec",),
    "event_fund": ("president", "press", "security"),
    "social_fund": ("president", "ombudsman"),
    "reserve": ("president", "finance", "security", "central_bank"),
}


def _route_keys(app: Any) -> set[tuple[str, str]]:
    result = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        result.add((
            str(getattr(route, "method", "") or "").upper(),
            str(getattr(resource, "canonical", "") or ""),
        ))
    return result


async def _ensure_schema(core: Any) -> None:
    conn = core.db._require_connection()
    await conn.executescript("""
        CREATE TABLE IF NOT EXISTS government_treasury_requests_v165(
            request_id TEXT PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            requester_id INTEGER NOT NULL,
            office_key TEXT NOT NULL,
            structure_key TEXT NOT NULL,
            amount INTEGER NOT NULL,
            reason TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'normal',
            status TEXT NOT NULL DEFAULT 'pending',
            reviewer_id INTEGER NOT NULL DEFAULT 0,
            review_reason TEXT NOT NULL DEFAULT '',
            bill_id TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL,
            reviewed_at INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_treasury_requests_v165_chat_status
            ON government_treasury_requests_v165(chat_id,status,created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_treasury_requests_v165_requester
            ON government_treasury_requests_v165(chat_id,requester_id,created_at DESC);
    """)
    await conn.commit()


def _requestable_keys(offices: list[str], is_admin: bool) -> list[str]:
    if is_admin:
        return list(treasury.STRUCTURES)
    held = set(map(str, offices))
    return [key for key, roles in STRUCTURE_REQUEST_ROLES.items() if held.intersection(roles)]


async def _access(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    offices = await gov._user_offices(core, chat_id, user_id)
    is_admin = user_id == int(core.DEVELOPER_ID)
    sanctioned = await gov._has_active_sanctions(core, chat_id, user_id)
    requestable = _requestable_keys(offices, is_admin)
    return {
        "offices": offices,
        "is_admin": is_admin,
        "sanctioned": bool(sanctioned),
        "requestable_keys": requestable,
        "can_request": bool(requestable and (is_admin or not sanctioned)),
        "can_review": bool(is_admin or "president" in offices),
    }


async def _request_rows(core: Any, chat_id: int, limit: int = 50) -> list[dict[str, Any]]:
    conn = core.db._require_connection()
    cursor = await conn.execute("""
        SELECT r.*, requester.full_name requester_name,
               requester.username requester_username,
               reviewer.full_name reviewer_name,
               b.status bill_status, b.number bill_number
        FROM government_treasury_requests_v165 r
        LEFT JOIN players requester
          ON requester.chat_id=r.chat_id AND requester.user_id=r.requester_id
        LEFT JOIN players reviewer
          ON reviewer.chat_id=r.chat_id AND reviewer.user_id=r.reviewer_id
        LEFT JOIN government_bills_v127 b ON b.bill_id=r.bill_id
        WHERE r.chat_id=?
        ORDER BY CASE r.status WHEN 'pending' THEN 0 WHEN 'processing' THEN 1 ELSE 2 END,
                 r.created_at DESC
        LIMIT ?
    """, (chat_id, max(1, min(100, limit))))
    result = []
    for row in await cursor.fetchall():
        skey = str(row["structure_key"])
        structure = treasury.STRUCTURES.get(skey, {"emoji": "🏛", "title": skey})
        okey = str(row["office_key"])
        office = gov.OFFICES.get(okey, {"emoji": "🏛", "title": okey})
        requester_name = str(
            row["requester_name"]
            or (f"@{row['requester_username']}" if row["requester_username"] else "")
            or f"ID {int(row['requester_id'])}"
        )
        result.append({
            "request_id": str(row["request_id"]),
            "requester_id": int(row["requester_id"]),
            "requester_name": requester_name,
            "office_key": okey,
            "office_title": str(office.get("title") or okey),
            "office_emoji": str(office.get("emoji") or "🏛"),
            "structure_key": skey,
            "structure_title": str(structure.get("title") or skey),
            "structure_emoji": str(structure.get("emoji") or "🏛"),
            "amount": int(row["amount"]),
            "reason": str(row["reason"]),
            "priority": str(row["priority"]),
            "priority_title": PRIORITIES.get(str(row["priority"]), str(row["priority"])),
            "status": str(row["status"]),
            "reviewer_id": int(row["reviewer_id"]),
            "reviewer_name": str(row["reviewer_name"] or ""),
            "review_reason": str(row["review_reason"] or ""),
            "bill_id": str(row["bill_id"] or ""),
            "bill_status": str(row["bill_status"] or ""),
            "bill_number": int(row["bill_number"] or 0),
            "created_at": int(row["created_at"]),
            "reviewed_at": int(row["reviewed_at"] or 0),
        })
    return result


async def _create_request(core: Any, bot: Any, chat_id: int, requester_id: int,
                          data: dict[str, Any]) -> str:
    await _ensure_schema(core)
    access = await _access(core, chat_id, requester_id)
    if not access["can_request"]:
        if access["sanctioned"]:
            raise PermissionError("Чиновник с активными санкциями не может запрашивать бюджет.")
        raise PermissionError("У вашей должности нет права запрашивать финансирование.")

    skey = str(data.get("structure_key") or "")
    if skey not in access["requestable_keys"]:
        raise PermissionError("Эта структура не относится к полномочиям вашей должности.")
    structure = treasury.STRUCTURES.get(skey)
    if structure is None:
        raise ValueError("Неизвестная государственная структура.")

    amount = gov._as_int(data.get("amount"))
    if amount <= 0 or amount > 1_000_000:
        raise ValueError("Сумма должна быть от 1 до 1 000 000 влияния.")
    reason = str(data.get("reason") or "").strip()
    if len(reason) < 10 or len(reason) > 500:
        raise ValueError("Обоснование должно содержать от 10 до 500 символов.")
    priority = str(data.get("priority") or "normal")
    if priority not in PRIORITIES:
        raise ValueError("Неизвестный приоритет запроса.")

    office_key = next(
        (key for key in access["offices"] if key in STRUCTURE_REQUEST_ROLES.get(skey, ())),
        access["offices"][0] if access["offices"] else "creator",
    )
    request_id = secrets.token_urlsafe(12)
    now = gov._now()
    conn = core.db._require_connection()
    async with core.db.lock:
        cursor = await conn.execute("""
            SELECT 1 FROM government_treasury_requests_v165
            WHERE chat_id=? AND requester_id=? AND structure_key=?
              AND status IN ('pending','processing') LIMIT 1
        """, (chat_id, requester_id, skey))
        if await cursor.fetchone() is not None:
            raise ValueError("У вас уже есть активный запрос для этой структуры.")
        await conn.execute("""
            INSERT INTO government_treasury_requests_v165(
                request_id,chat_id,requester_id,office_key,structure_key,amount,
                reason,priority,status,created_at
            ) VALUES(?,?,?,?,?,?,?,?,'pending',?)
        """, (request_id, chat_id, requester_id, office_key, skey, amount,
              reason, priority, now))
        await conn.commit()

    requester = await gov._player_dict(core, chat_id, requester_id)
    office = gov.OFFICES.get(office_key, {"emoji": "🏛", "title": office_key})
    await gov._publish(
        bot, chat_id,
        "🏛 <b>ЗАПРОС ФИНАНСИРОВАНИЯ ИЗ КАЗНЫ</b>\n\n"
        f"{structure['emoji']} Структура: <b>{html.escape(structure['title'])}</b>\n"
        f"{office.get('emoji', '🏛')} Заявитель: "
        f"<b>{html.escape(str((requester or {}).get('name') or requester_id))}</b>\n"
        f"Сумма: <b>{gov._fmt(amount)}</b> влияния\n"
        f"Приоритет: <b>{html.escape(PRIORITIES[priority])}</b>\n"
        f"Обоснование: {html.escape(reason)}\n\n"
        "Запрос передан Президенту реальности на рассмотрение.",
    )
    return f"Запрос на {gov._fmt(amount)} влияния передан президенту."


async def _claim_request(core: Any, chat_id: int, request_id: str,
                         reviewer_id: int) -> Any:
    conn = core.db._require_connection()
    async with core.db.lock:
        cursor = await conn.execute("""
            SELECT * FROM government_treasury_requests_v165
            WHERE request_id=? AND chat_id=?
        """, (request_id, chat_id))
        row = await cursor.fetchone()
        if row is None:
            raise ValueError("Запрос финансирования не найден.")
        if str(row["status"]) != "pending":
            raise ValueError("Этот запрос уже рассмотрен или обрабатывается.")
        cursor = await conn.execute("""
            UPDATE government_treasury_requests_v165
            SET status='processing',reviewer_id=?,reviewed_at=?
            WHERE request_id=? AND chat_id=? AND status='pending'
        """, (reviewer_id, gov._now(), request_id, chat_id))
        if int(cursor.rowcount or 0) != 1:
            raise ValueError("Запрос уже рассматривает другой пользователь.")
        await conn.commit()
    return row


async def _restore_pending(core: Any, chat_id: int, request_id: str) -> None:
    conn = core.db._require_connection()
    await conn.execute("""
        UPDATE government_treasury_requests_v165
        SET status='pending',reviewer_id=0,reviewed_at=0
        WHERE request_id=? AND chat_id=? AND status='processing'
    """, (request_id, chat_id))
    await conn.commit()


async def _review_request(core: Any, bot: Any, chat_id: int, reviewer_id: int,
                          data: dict[str, Any]) -> str:
    await _ensure_schema(core)
    access = await _access(core, chat_id, reviewer_id)
    if not access["can_review"]:
        raise PermissionError("Рассматривать бюджетные запросы может Президент реальности.")

    request_id = str(data.get("request_id") or "")
    decision = str(data.get("decision") or "")
    if decision not in {"approve", "reject"}:
        raise ValueError("Неизвестное решение по запросу.")
    row = await _claim_request(core, chat_id, request_id, reviewer_id)

    skey = str(row["structure_key"])
    structure = treasury.STRUCTURES.get(skey)
    if structure is None:
        await _restore_pending(core, chat_id, request_id)
        raise ValueError("Структура из запроса больше не существует.")

    conn = core.db._require_connection()
    if decision == "reject":
        review_reason = str(data.get("review_reason") or "").strip()
        if len(review_reason) < 5 or len(review_reason) > 300:
            await _restore_pending(core, chat_id, request_id)
            raise ValueError("Причина отказа должна содержать от 5 до 300 символов.")
        await conn.execute("""
            UPDATE government_treasury_requests_v165
            SET status='rejected',review_reason=?,reviewed_at=?
            WHERE request_id=? AND chat_id=? AND status='processing'
        """, (review_reason, gov._now(), request_id, chat_id))
        await conn.commit()
        await gov._publish(
            bot, chat_id,
            "❌ <b>БЮДЖЕТНЫЙ ЗАПРОС ОТКЛОНЁН</b>\n\n"
            f"{structure['emoji']} {html.escape(structure['title'])}\n"
            f"Сумма: <b>{gov._fmt(int(row['amount']))}</b> влияния\n"
            f"Причина: {html.escape(review_reason)}",
        )
        return "Запрос отклонён."

    amount = int(row["amount"])
    reason = str(row["reason"])
    try:
        state = await gov._ensure_state(core, chat_id)
        used = await treasury._daily_used(core, chat_id, reviewer_id)
        direct_limit = treasury._direct_limit(int(state["treasury"]))
        daily_remaining = max(
            0, treasury._daily_limit(int(state["treasury"]), used) - used
        )
        taccess = await treasury._access(core, chat_id, reviewer_id)
        requires_bill = (
            not taccess["can_direct"]
            or amount > direct_limit
            or amount > daily_remaining
        )
        bill_id = ""
        if requires_bill:
            bill_id = await gov._create_bill(
                core, bot, chat_id, reviewer_id, "structure_budget",
                f"О финансировании: {structure['title']}"[:120],
                f"По запросу структуры: {reason}"[:1200],
                {"structure_key": skey, "amount": amount},
            )
            status = "sent_to_duma"
            result = f"Запрос одобрен и передан в Госдуму на {gov._fmt(amount)} влияния."
        else:
            result = await treasury._direct_structure_funding(
                core, bot, chat_id, reviewer_id, skey, amount,
                f"По запросу структуры: {reason}"[:500],
            )
            status = "approved"

        await conn.execute("""
            UPDATE government_treasury_requests_v165
            SET status=?,bill_id=?,review_reason='',reviewed_at=?
            WHERE request_id=? AND chat_id=? AND status='processing'
        """, (status, bill_id, gov._now(), request_id, chat_id))
        await conn.commit()
        if status == "sent_to_duma":
            await gov._publish(
                bot, chat_id,
                "✅ <b>ПРЕЗИДЕНТ ОДОБРИЛ ЗАПРОС СТРУКТУРЫ</b>\n\n"
                f"{structure['emoji']} {html.escape(structure['title'])}\n"
                f"Сумма: <b>{gov._fmt(amount)}</b> влияния\n\n"
                "Расход превышает самостоятельный лимит и передан в Госдуму.",
            )
        return result
    except Exception:
        await _restore_pending(core, chat_id, request_id)
        raise


async def _withdraw_request(core: Any, chat_id: int, actor_id: int,
                            request_id: str) -> str:
    await _ensure_schema(core)
    access = await _access(core, chat_id, actor_id)
    conn = core.db._require_connection()
    async with core.db.lock:
        cursor = await conn.execute("""
            SELECT requester_id,status FROM government_treasury_requests_v165
            WHERE request_id=? AND chat_id=?
        """, (request_id, chat_id))
        row = await cursor.fetchone()
        if row is None:
            raise ValueError("Запрос не найден.")
        if int(row["requester_id"]) != actor_id and not access["is_admin"]:
            raise PermissionError("Отозвать запрос может только его автор.")
        if str(row["status"]) != "pending":
            raise ValueError("Можно отозвать только нерассмотренный запрос.")
        await conn.execute("""
            UPDATE government_treasury_requests_v165
            SET status='withdrawn',reviewer_id=?,reviewed_at=?
            WHERE request_id=? AND chat_id=? AND status='pending'
        """, (actor_id, gov._now(), request_id, chat_id))
        await conn.commit()
    return "Запрос отозван."


def install_government_treasury_requests_v165(core: Any) -> None:
    if getattr(core, "_government_treasury_requests_v165_installed", False):
        return
    core._government_treasury_requests_v165_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION

    original_connect = core.Database.connect

    async def connect_with_treasury_requests(self: Any) -> None:
        await original_connect(self)
        await _ensure_schema(core)

    core.Database.connect = connect_with_treasury_requests
    previous_state = gov._state

    async def state_with_treasury_requests(core_arg: Any, bot: Any, chat_id: int,
                                           user_id: int) -> dict[str, Any]:
        payload = await previous_state(core_arg, bot, chat_id, user_id)
        await _ensure_schema(core_arg)
        access = await _access(core_arg, chat_id, user_id)
        requests = await _request_rows(core_arg, chat_id)
        structures = {
            str(item.get("key")): item
            for item in (payload.get("treasury_management_v164") or {}).get("structures", [])
            if isinstance(item, dict)
        }
        requestable = [
            structures.get(key, {
                "key": key,
                **treasury.STRUCTURES.get(key, {"emoji": "🏛", "title": key}),
                "balance": 0,
                "updated_at": 0,
            })
            for key in access["requestable_keys"]
        ]
        payload["version"] = VERSION
        permissions = payload.setdefault("permissions", {})
        permissions["can_request_structure_funds"] = access["can_request"]
        permissions["can_review_structure_funds"] = access["can_review"]
        payload["treasury_requests_v165"] = {
            **access,
            "requestable_structures": requestable,
            "pending": [item for item in requests if item["status"] in {"pending", "processing"}],
            "mine": [item for item in requests if item["requester_id"] == user_id][:20],
            "recent": requests,
            "pending_count": sum(item["status"] == "pending" for item in requests),
        }
        return payload

    gov._state = state_with_treasury_requests
    previous_inject = luxury._inject_assets

    def inject_treasury_requests(source: str) -> str:
        source = previous_inject(source)
        if ASSET_CSS.name not in source:
            source = source.replace(
                "</head>",
                f'  <link rel="stylesheet" href="/government-v165/{ASSET_CSS.name}?v=165">\n</head>',
            )
        if ASSET_JS.name not in source:
            source = source.replace(
                "</body>",
                f'  <script src="/government-v165/{ASSET_JS.name}?v=165"></script>\n</body>',
            )
        return source

    luxury._inject_assets = inject_treasury_requests

    async def action_api(request: Any):
        try:
            user, chat_id, data = await gov._auth(core, request)
            action = str(data.get("action") or "")
            user_id = int(user.id)
            if action == "treasury_request_create":
                message = await _create_request(
                    core, request.app["bot"], chat_id, user_id, data
                )
            elif action == "treasury_request_review":
                message = await _review_request(
                    core, request.app["bot"], chat_id, user_id, data
                )
            elif action == "treasury_request_withdraw":
                message = await _withdraw_request(
                    core, chat_id, user_id, str(data.get("request_id") or "")
                )
            else:
                raise ValueError("Неизвестное действие запросов казны Reality 165.")
            return core.web.json_response({"ok": True, "message": message})
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    original_start_server = core.start_webapp_server

    async def start_with_treasury_requests(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты запросов казны Reality 165")
        original_runner = core.web.AppRunner

        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            path = ASSET_JS if name == ASSET_JS.name else ASSET_CSS if name == ASSET_CSS.name else None
            if path is None:
                raise core.web.HTTPNotFound()
            content_type = "application/javascript" if path.suffix == ".js" else "text/css"
            return core.web.FileResponse(path, headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "Content-Type": f"{content_type}; charset=utf-8",
                "X-Government-Treasury-Requests": "165",
            })

        def runner_with_treasury_requests(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/government-v165/{name}") not in keys:
                app.router.add_get("/government-v165/{name}", asset)
            if ("POST", "/government-v165/api/action") not in keys:
                app.router.add_post("/government-v165/api/action", action_api)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_treasury_requests
        try:
            return await original_start_server(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_treasury_requests
