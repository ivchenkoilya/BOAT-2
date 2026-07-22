from __future__ import annotations

import html
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

import government_mandate_luxury_v147 as luxury
import government_v127 as gov


VERSION = "Reality 164 · Президентское управление казной"
ASSET_JS = Path(__file__).resolve().parent / "governmentapp_v127" / "treasury-management-v164.js"
ASSET_CSS = Path(__file__).resolve().parent / "governmentapp_v127" / "treasury-management-v164.css"

STRUCTURES: dict[str, dict[str, str]] = {
    "presidential_admin": {"emoji": "🦅", "title": "Администрация президента"},
    "duma": {"emoji": "🏛", "title": "Государственная дума"},
    "finance_ministry": {"emoji": "💰", "title": "Министерство финансов"},
    "oversight": {"emoji": "🚨", "title": "Государственный надзор"},
    "election_commission": {"emoji": "🗳", "title": "Избирательная комиссия"},
    "event_fund": {"emoji": "🎪", "title": "Фонд государственных событий"},
    "social_fund": {"emoji": "🤝", "title": "Социальный фонд"},
    "reserve": {"emoji": "🛡", "title": "Резервный фонд"},
}


def _route_keys(app: Any) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        result.add(
            (
                str(getattr(route, "method", "") or "").upper(),
                str(getattr(resource, "canonical", "") or ""),
            )
        )
    return result


def _direct_limit(balance: int) -> int:
    available = max(0, int(balance))
    if available <= 0:
        return 0
    return min(available, max(100, min(1_000, available // 100)))


def _daily_limit(balance: int, used: int = 0) -> int:
    basis = max(0, int(balance)) + max(0, int(used))
    if basis <= 0:
        return 0
    return min(basis, max(300, min(3_000, basis * 3 // 100)))


def _day_start() -> int:
    now = datetime.now(gov.MOSCOW)
    return int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())


async def _ensure_schema(core: Any) -> None:
    conn = core.db._require_connection()
    await conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS government_structure_funds_v164(
            chat_id INTEGER NOT NULL,
            structure_key TEXT NOT NULL,
            balance INTEGER NOT NULL DEFAULT 0,
            updated_at INTEGER NOT NULL,
            PRIMARY KEY(chat_id,structure_key)
        );
        CREATE TABLE IF NOT EXISTS government_treasury_operations_v164(
            operation_id TEXT PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            actor_id INTEGER NOT NULL,
            target_type TEXT NOT NULL,
            target_user_id INTEGER NOT NULL DEFAULT 0,
            target_key TEXT NOT NULL DEFAULT '',
            amount INTEGER NOT NULL,
            reason TEXT NOT NULL,
            mode TEXT NOT NULL,
            bill_id TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_treasury_operations_v164_chat_time
            ON government_treasury_operations_v164(chat_id,created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_treasury_operations_v164_actor_time
            ON government_treasury_operations_v164(chat_id,actor_id,created_at DESC);
        """
    )
    await conn.commit()


async def _daily_used(core: Any, chat_id: int, actor_id: int) -> int:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT COALESCE(SUM(amount),0) amount
        FROM government_treasury_operations_v164
        WHERE chat_id=? AND actor_id=? AND mode='direct' AND created_at>=?
        """,
        (int(chat_id), int(actor_id), _day_start()),
    )
    row = await cursor.fetchone()
    return int(row["amount"] if row else 0)


async def _structure_rows(core: Any, chat_id: int) -> list[dict[str, Any]]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT structure_key,balance,updated_at FROM government_structure_funds_v164 WHERE chat_id=?",
        (int(chat_id),),
    )
    stored = {str(row["structure_key"]): row for row in await cursor.fetchall()}
    return [
        {
            "key": key,
            "emoji": spec["emoji"],
            "title": spec["title"],
            "balance": int(stored[key]["balance"] if key in stored else 0),
            "updated_at": int(stored[key]["updated_at"] if key in stored else 0),
        }
        for key, spec in STRUCTURES.items()
    ]


async def _recent_operations(core: Any, chat_id: int) -> list[dict[str, Any]]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT o.*,p.full_name target_name
        FROM government_treasury_operations_v164 o
        LEFT JOIN players p
          ON p.chat_id=o.chat_id AND p.user_id=o.target_user_id
        WHERE o.chat_id=?
        ORDER BY o.created_at DESC
        LIMIT 20
        """,
        (int(chat_id),),
    )
    result: list[dict[str, Any]] = []
    for row in await cursor.fetchall():
        target_type = str(row["target_type"])
        target_key = str(row["target_key"] or "")
        if target_type == "structure":
            target_title = STRUCTURES.get(target_key, {"title": target_key}).get("title", target_key)
        else:
            target_title = str(row["target_name"] or f"ID {int(row['target_user_id'])}")
        result.append(
            {
                "operation_id": str(row["operation_id"]),
                "actor_id": int(row["actor_id"]),
                "target_type": target_type,
                "target_user_id": int(row["target_user_id"]),
                "target_key": target_key,
                "target_title": target_title,
                "amount": int(row["amount"]),
                "reason": str(row["reason"]),
                "mode": str(row["mode"]),
                "bill_id": str(row["bill_id"] or ""),
                "created_at": int(row["created_at"]),
            }
        )
    return result


async def _access(core: Any, chat_id: int, user_id: int) -> dict[str, bool]:
    offices = await gov._user_offices(core, int(chat_id), int(user_id))
    is_admin = int(user_id) == int(core.DEVELOPER_ID)
    is_president = "president" in offices
    sanctioned = await gov._has_active_sanctions(core, int(chat_id), int(user_id))
    return {
        "is_admin": is_admin,
        "is_president": is_president,
        "sanctioned": bool(sanctioned),
        "can_propose": bool(is_admin or is_president),
        "can_direct": bool(is_admin or (is_president and not sanctioned)),
    }


async def _record_operation(
    core: Any,
    chat_id: int,
    actor_id: int,
    target_type: str,
    amount: int,
    reason: str,
    mode: str,
    *,
    target_user_id: int = 0,
    target_key: str = "",
    bill_id: str = "",
) -> str:
    operation_id = secrets.token_urlsafe(12)
    conn = core.db._require_connection()
    await conn.execute(
        """
        INSERT INTO government_treasury_operations_v164(
            operation_id,chat_id,actor_id,target_type,target_user_id,target_key,
            amount,reason,mode,bill_id,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            operation_id,
            int(chat_id),
            int(actor_id),
            str(target_type),
            int(target_user_id),
            str(target_key),
            int(amount),
            str(reason),
            str(mode),
            str(bill_id),
            gov._now(),
        ),
    )
    return operation_id


async def _direct_payment(
    core: Any,
    bot: Any,
    chat_id: int,
    actor_id: int,
    target_user_id: int,
    amount: int,
    reason: str,
) -> str:
    target = await gov._player_dict(core, int(chat_id), int(target_user_id))
    if target is None:
        raise ValueError("Получатель выплаты не найден.")
    if int(target_user_id) == int(actor_id):
        raise PermissionError("Самому себе президент может выделить деньги только через Госдуму.")

    conn = core.db._require_connection()
    state = await gov._ensure_state(core, int(chat_id))
    used = await _daily_used(core, int(chat_id), int(actor_id))
    direct_limit = _direct_limit(int(state["treasury"]))
    daily_limit = _daily_limit(int(state["treasury"]), used)
    if int(amount) > direct_limit:
        raise ValueError(f"Самостоятельный лимит одной выплаты — {gov._fmt(direct_limit)}.")
    if used + int(amount) > daily_limit:
        raise ValueError(f"Дневной лимит прямых расходов — {gov._fmt(daily_limit)}.")

    now = gov._now()
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT treasury FROM government_state_v127 WHERE chat_id=?",
            (int(chat_id),),
        )
        current = await cursor.fetchone()
        if current is None or int(current["treasury"]) < int(amount):
            raise ValueError("В казне недостаточно влияния.")
        await conn.execute(
            "UPDATE government_state_v127 SET treasury=treasury-?,updated_at=? WHERE chat_id=?",
            (int(amount), now, int(chat_id)),
        )
        await conn.execute(
            "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
            (int(amount), now, int(chat_id), int(target_user_id)),
        )
        await conn.execute(
            "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
            (int(chat_id), int(target_user_id), int(amount), "presidential_treasury_payment_v164", now),
        )
        operation_id = await _record_operation(
            core,
            int(chat_id),
            int(actor_id),
            "user",
            int(amount),
            reason,
            "direct",
            target_user_id=int(target_user_id),
        )
        await gov._treasury_log(
            core,
            int(chat_id),
            -int(amount),
            reason,
            "president_payment",
            operation_id,
            int(actor_id),
        )
        await conn.commit()

    await gov._publish(
        bot,
        int(chat_id),
        "💸 <b>ПРЕЗИДЕНТСКАЯ ВЫПЛАТА</b>\n\n"
        f"Получатель: <b>{html.escape(str(target['name']))}</b>\n"
        f"Сумма: <b>{gov._fmt(amount)}</b> влияния\n"
        f"Основание: {html.escape(reason)}\n\n"
        "Операция внесена в публичный журнал казны.",
    )
    return f"Выплачено {gov._fmt(amount)} влияния участнику {target['name']}."


async def _direct_structure_funding(
    core: Any,
    bot: Any,
    chat_id: int,
    actor_id: int,
    structure_key: str,
    amount: int,
    reason: str,
) -> str:
    spec = STRUCTURES.get(str(structure_key))
    if spec is None:
        raise ValueError("Неизвестная государственная структура.")

    conn = core.db._require_connection()
    state = await gov._ensure_state(core, int(chat_id))
    used = await _daily_used(core, int(chat_id), int(actor_id))
    direct_limit = _direct_limit(int(state["treasury"]))
    daily_limit = _daily_limit(int(state["treasury"]), used)
    if int(amount) > direct_limit:
        raise ValueError(f"Самостоятельный лимит одного решения — {gov._fmt(direct_limit)}.")
    if used + int(amount) > daily_limit:
        raise ValueError(f"Дневной лимит прямых расходов — {gov._fmt(daily_limit)}.")

    now = gov._now()
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT treasury FROM government_state_v127 WHERE chat_id=?",
            (int(chat_id),),
        )
        current = await cursor.fetchone()
        if current is None or int(current["treasury"]) < int(amount):
            raise ValueError("В казне недостаточно влияния.")
        await conn.execute(
            "UPDATE government_state_v127 SET treasury=treasury-?,updated_at=? WHERE chat_id=?",
            (int(amount), now, int(chat_id)),
        )
        await conn.execute(
            """
            INSERT INTO government_structure_funds_v164(chat_id,structure_key,balance,updated_at)
            VALUES(?,?,?,?)
            ON CONFLICT(chat_id,structure_key) DO UPDATE SET
              balance=government_structure_funds_v164.balance+excluded.balance,
              updated_at=excluded.updated_at
            """,
            (int(chat_id), str(structure_key), int(amount), now),
        )
        operation_id = await _record_operation(
            core,
            int(chat_id),
            int(actor_id),
            "structure",
            int(amount),
            reason,
            "direct",
            target_key=str(structure_key),
        )
        await gov._treasury_log(
            core,
            int(chat_id),
            -int(amount),
            f"{spec['title']}: {reason}",
            "structure_funding",
            operation_id,
            int(actor_id),
        )
        await conn.commit()

    await gov._publish(
        bot,
        int(chat_id),
        "🏛 <b>ФИНАНСИРОВАНИЕ ГОССТРУКТУРЫ</b>\n\n"
        f"{spec['emoji']} Структура: <b>{html.escape(spec['title'])}</b>\n"
        f"Сумма: <b>{gov._fmt(amount)}</b> влияния\n"
        f"Назначение: {html.escape(reason)}\n\n"
        "Средства переведены на отдельный баланс структуры.",
    )
    return f"{spec['title']} профинансирована на {gov._fmt(amount)} влияния."


async def _create_proposal(
    core: Any,
    bot: Any,
    chat_id: int,
    actor_id: int,
    target_type: str,
    target_user_id: int,
    structure_key: str,
    amount: int,
    reason: str,
) -> str:
    if target_type == "user":
        target = await gov._player_dict(core, int(chat_id), int(target_user_id))
        if target is None:
            raise ValueError("Получатель выплаты не найден.")
        bill_id = await gov._create_bill(
            core,
            bot,
            int(chat_id),
            int(actor_id),
            "budget",
            f"О государственной выплате: {target['name']}"[:120],
            reason,
            {"target_user_id": int(target_user_id), "amount": int(amount)},
        )
        return f"В Госдуму внесён проект выплаты на {gov._fmt(amount)} влияния: {bill_id}."

    spec = STRUCTURES.get(str(structure_key))
    if spec is None:
        raise ValueError("Неизвестная государственная структура.")
    bill_id = await gov._create_bill(
        core,
        bot,
        int(chat_id),
        int(actor_id),
        "structure_budget",
        f"О финансировании: {spec['title']}"[:120],
        reason,
        {"structure_key": str(structure_key), "amount": int(amount)},
    )
    return f"В Госдуму внесён проект финансирования на {gov._fmt(amount)} влияния: {bill_id}."


async def _disburse(
    core: Any,
    bot: Any,
    chat_id: int,
    actor_id: int,
    data: dict[str, Any],
) -> str:
    access = await _access(core, int(chat_id), int(actor_id))
    if not access["can_propose"]:
        raise PermissionError("Управление казной доступно действующему Президенту реальности.")

    target_type = str(data.get("target_type") or "user")
    if target_type not in {"user", "structure"}:
        raise ValueError("Неизвестный тип получателя.")
    amount = gov._as_int(data.get("amount"))
    if amount <= 0 or amount > 1_000_000:
        raise ValueError("Сумма должна быть от 1 до 1 000 000 влияния.")
    reason = str(data.get("reason") or "").strip()
    if len(reason) < 10 or len(reason) > 500:
        raise ValueError("Основание должно содержать от 10 до 500 символов.")

    state = await gov._ensure_state(core, int(chat_id))
    used = await _daily_used(core, int(chat_id), int(actor_id))
    direct_limit = _direct_limit(int(state["treasury"]))
    daily_remaining = max(0, _daily_limit(int(state["treasury"]), used) - used)
    target_user_id = gov._as_int(data.get("target_user_id"))
    structure_key = str(data.get("structure_key") or "")

    requires_bill = (
        not access["can_direct"]
        or amount > direct_limit
        or amount > daily_remaining
        or (target_type == "user" and int(target_user_id) == int(actor_id))
    )
    if requires_bill:
        return await _create_proposal(
            core,
            bot,
            int(chat_id),
            int(actor_id),
            target_type,
            int(target_user_id),
            structure_key,
            int(amount),
            reason,
        )
    if target_type == "user":
        return await _direct_payment(
            core,
            bot,
            int(chat_id),
            int(actor_id),
            int(target_user_id),
            int(amount),
            reason,
        )
    return await _direct_structure_funding(
        core,
        bot,
        int(chat_id),
        int(actor_id),
        structure_key,
        int(amount),
        reason,
    )


def install_government_treasury_management_v164(core: Any) -> None:
    if getattr(core, "_government_treasury_management_v164_installed", False):
        return
    core._government_treasury_management_v164_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION
    gov.BILL_TYPES["structure_budget"] = {
        "emoji": "🏛",
        "title": "Финансирование государственной структуры",
    }

    original_connect = core.Database.connect

    async def connect_with_treasury_management(self: Any) -> None:
        await original_connect(self)
        await _ensure_schema(core)

    core.Database.connect = connect_with_treasury_management

    previous_create_bill = gov._create_bill

    async def create_bill_with_structure_budget(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        author_id: int,
        bill_type: str,
        title: str,
        description: str,
        payload: dict[str, Any],
    ) -> str:
        if str(bill_type) == "structure_budget":
            offices = await gov._user_offices(core_arg, int(chat_id), int(author_id))
            is_admin = int(author_id) == int(core_arg.DEVELOPER_ID)
            if not (is_admin or set(offices) & {"president", "finance", "deputy"}):
                raise PermissionError(
                    "Финансирование госструктуры может предложить президент, министр финансов или депутат."
                )
            structure_key = str((payload or {}).get("structure_key") or "")
            amount = gov._as_int((payload or {}).get("amount"))
            if structure_key not in STRUCTURES:
                raise ValueError("Неизвестная государственная структура.")
            if amount <= 0 or amount > 1_000_000:
                raise ValueError("Размер финансирования должен быть от 1 до 1 000 000.")
            payload = {"structure_key": structure_key, "amount": amount}
        return await previous_create_bill(
            core_arg,
            bot,
            int(chat_id),
            int(author_id),
            str(bill_type),
            str(title),
            str(description),
            dict(payload or {}),
        )

    gov._create_bill = create_bill_with_structure_budget

    previous_enact_bill = gov._enact_bill

    async def enact_bill_with_structure_budget(
        core_arg: Any,
        bot: Any,
        bill: Any,
        actor_id: int,
    ) -> None:
        if str(bill["bill_type"]) != "structure_budget":
            await previous_enact_bill(core_arg, bot, bill, int(actor_id))
            return

        bill_id = str(bill["bill_id"])
        chat_id = int(bill["chat_id"])
        payload = gov._json(bill["payload_json"], {})
        structure_key = str(payload.get("structure_key") or "")
        amount = gov._as_int(payload.get("amount"))
        spec = STRUCTURES.get(structure_key)
        if spec is None or amount <= 0:
            raise ValueError("Параметры финансирования структуры повреждены.")

        law_number = await gov._next_number(core_arg, chat_id, "law_seq")
        law_id = secrets.token_urlsafe(12)
        now = gov._now()
        conn = core_arg.db._require_connection()
        async with core_arg.db.lock:
            cursor = await conn.execute(
                "SELECT treasury FROM government_state_v127 WHERE chat_id=?",
                (chat_id,),
            )
            state = await cursor.fetchone()
            if state is None or int(state["treasury"]) < amount:
                raise ValueError("В казне недостаточно влияния для исполнения закона.")
            cursor = await conn.execute(
                "SELECT 1 FROM government_treasury_operations_v164 WHERE bill_id=? LIMIT 1",
                (bill_id,),
            )
            if await cursor.fetchone() is not None:
                raise ValueError("Этот бюджетный закон уже исполнен.")
            await conn.execute(
                "UPDATE government_state_v127 SET treasury=treasury-?,updated_at=? WHERE chat_id=?",
                (amount, now, chat_id),
            )
            await conn.execute(
                """
                INSERT INTO government_structure_funds_v164(chat_id,structure_key,balance,updated_at)
                VALUES(?,?,?,?)
                ON CONFLICT(chat_id,structure_key) DO UPDATE SET
                  balance=government_structure_funds_v164.balance+excluded.balance,
                  updated_at=excluded.updated_at
                """,
                (chat_id, structure_key, amount, now),
            )
            operation_id = await _record_operation(
                core_arg,
                chat_id,
                int(actor_id),
                "structure",
                amount,
                str(bill["description"]),
                "bill",
                target_key=structure_key,
                bill_id=bill_id,
            )
            await gov._treasury_log(
                core_arg,
                chat_id,
                -amount,
                f"{spec['title']}: {str(bill['title'])}",
                "structure_budget",
                operation_id,
                int(actor_id),
            )
            await conn.execute(
                """
                INSERT INTO government_laws_v127(
                    law_id,chat_id,number,title,text,law_type,payload_json,bill_id,enacted_at,active
                ) VALUES(?,?,?,?,?,?,?,?,?,1)
                """,
                (
                    law_id,
                    chat_id,
                    int(law_number),
                    str(bill["title"]),
                    str(bill["description"]),
                    "structure_budget",
                    json.dumps(payload, ensure_ascii=False),
                    bill_id,
                    now,
                ),
            )
            await conn.execute(
                "UPDATE government_bills_v127 SET status='enacted',resolved_at=? WHERE bill_id=?",
                (now, bill_id),
            )
            await conn.commit()

        await gov._publish(
            bot,
            chat_id,
            f"⚖️ <b>ЗАКОН №{law_number} ВСТУПИЛ В СИЛУ</b>\n\n"
            f"🏛 <b>{html.escape(str(bill['title']))}</b>\n\n"
            f"{html.escape(str(bill['description']))}\n\n"
            f"{spec['emoji']} На баланс структуры «<b>{html.escape(spec['title'])}</b>» "
            f"переведено <b>{gov._fmt(amount)}</b> влияния.",
        )

    gov._enact_bill = enact_bill_with_structure_budget

    previous_state = gov._state

    async def state_with_treasury_management(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        payload = await previous_state(core_arg, bot, int(chat_id), int(user_id))
        await _ensure_schema(core_arg)
        access = await _access(core_arg, int(chat_id), int(user_id))
        used = await _daily_used(core_arg, int(chat_id), int(user_id))
        balance = int((payload.get("treasury") or {}).get("balance") or 0)
        daily_limit = _daily_limit(balance, used)
        structures = await _structure_rows(core_arg, int(chat_id))
        payload["version"] = VERSION
        payload.setdefault("permissions", {})["can_manage_treasury"] = access["can_propose"]
        payload["treasury_management_v164"] = {
            **access,
            "direct_limit": _direct_limit(balance),
            "daily_limit": daily_limit,
            "daily_used": used,
            "daily_remaining": max(0, daily_limit - used),
            "structures": structures,
            "structure_total": sum(int(item["balance"]) for item in structures),
            "recent": await _recent_operations(core_arg, int(chat_id)),
        }
        return payload

    gov._state = state_with_treasury_management

    previous_inject = luxury._inject_assets

    def inject_treasury_management(source: str) -> str:
        source = previous_inject(source)
        if ASSET_CSS.name not in source:
            source = source.replace(
                "</head>",
                f'  <link rel="stylesheet" href="/government-v164/{ASSET_CSS.name}?v=164">\n</head>',
            )
        if ASSET_JS.name not in source:
            source = source.replace(
                "</body>",
                f'  <script src="/government-v164/{ASSET_JS.name}?v=164"></script>\n</body>',
            )
        return source

    luxury._inject_assets = inject_treasury_management

    async def action_api(request: Any):
        try:
            user, chat_id, data = await gov._auth(core, request)
            action = str(data.get("action") or "")
            if action != "treasury_disburse":
                raise ValueError("Неизвестное действие управления казной Reality 164.")
            message = await _disburse(
                core,
                request.app["bot"],
                int(chat_id),
                int(user.id),
                data,
            )
            return core.web.json_response({"ok": True, "message": message})
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    original_start_server = core.start_webapp_server

    async def start_with_treasury_management(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты управления казной Reality 164")
        original_runner = core.web.AppRunner

        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            path = ASSET_JS if name == ASSET_JS.name else ASSET_CSS if name == ASSET_CSS.name else None
            if path is None:
                raise core.web.HTTPNotFound()
            content_type = "application/javascript" if path.suffix == ".js" else "text/css"
            return core.web.FileResponse(
                path,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Content-Type": f"{content_type}; charset=utf-8",
                    "X-Government-Treasury": "164",
                },
            )

        def runner_with_treasury_management(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/government-v164/{name}") not in keys:
                app.router.add_get("/government-v164/{name}", asset)
            if ("POST", "/government-v164/api/action") not in keys:
                app.router.add_post("/government-v164/api/action", action_api)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_treasury_management
        try:
            return await original_start_server(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_treasury_management
