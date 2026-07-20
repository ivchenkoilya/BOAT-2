from __future__ import annotations

import html
import math
import secrets
import time
from pathlib import Path
from typing import Any

from aiogram import F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

import finance_system_v112 as finance


VERSION = "Reality 118 · Заявки на заём"
REQUEST_TTL = 24 * 60 * 60
APP_DIR = Path(__file__).resolve().parent / "financeapp_v118"


def _now() -> int:
    return int(time.time())


def _fmt(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _request_markup(request_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить заявку",
                    callback_data=f"fin118:approve:{request_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"fin118:reject:{request_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Отозвать заявку",
                    callback_data=f"fin118:cancel:{request_id}",
                )
            ],
        ]
    )


def _chat_id(start_param: str | None, request: Any, data: dict[str, Any]) -> int:
    raw = str(start_param or data.get("chat_id") or request.query.get("chat_id") or "").strip()
    if raw.startswith("finance_"):
        raw = raw[8:]
    try:
        chat_id = int(raw)
    except (TypeError, ValueError):
        raise ValueError("Не найдена беседа для заявки.")
    if chat_id >= 0:
        raise ValueError("Заявки работают только внутри групповой беседы.")
    return chat_id


async def _expire_requests(core: Any, chat_id: int, borrower_id: int | None = None) -> None:
    conn = core.db._require_connection()
    where = ["chat_id=?", "status='pending'", "expires_at<=?"]
    args: list[Any] = [chat_id, _now()]
    if borrower_id is not None:
        where.append("borrower_id=?")
        args.append(int(borrower_id))
    async with core.db.lock:
        await conn.execute(
            f"UPDATE finance_loan_requests_v118 SET status='expired',completed_at=? WHERE {' AND '.join(where)}",
            (_now(), *args),
        )
        await conn.commit()


async def _pending_payload(core: Any, chat_id: int, borrower_id: int) -> dict[str, Any] | None:
    await _expire_requests(core, chat_id, borrower_id)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT r.*,COALESCE(p.full_name,'Участник') lender_name
        FROM finance_loan_requests_v118 r
        LEFT JOIN players p ON p.chat_id=r.chat_id AND p.user_id=r.target_lender_id
        WHERE r.chat_id=? AND r.borrower_id=? AND r.status='pending'
        ORDER BY r.created_at DESC LIMIT 1
        """,
        (chat_id, borrower_id),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "request_id": str(row["request_id"]),
        "lender_id": int(row["target_lender_id"]),
        "lender_name": str(row["lender_name"]),
        "amount": int(row["amount"]),
        "interest": int(row["interest_percent"]),
        "days": int(row["term_days"]),
        "total_due": int(row["total_due"]),
        "expires_at": int(row["expires_at"]),
        "status": str(row["status"]),
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


def install_finance_loan_requests_v118(core: Any) -> None:
    if getattr(core, "_finance_loan_requests_v118_installed", False):
        return
    core._finance_loan_requests_v118_installed = True
    core.FINANCE_SYSTEM_VERSION = VERSION

    original_connect = core.Database.connect

    async def connect_with_requests(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS finance_loan_requests_v118(
                    request_id TEXT PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    borrower_id INTEGER NOT NULL,
                    target_lender_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    interest_percent INTEGER NOT NULL,
                    term_days INTEGER NOT NULL,
                    total_due INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    message_id INTEGER,
                    lender_id INTEGER,
                    loan_id TEXT,
                    completed_at INTEGER
                );
                CREATE INDEX IF NOT EXISTS idx_finance_request_borrower
                ON finance_loan_requests_v118(chat_id,borrower_id,status,created_at);
                CREATE INDEX IF NOT EXISTS idx_finance_request_lender
                ON finance_loan_requests_v118(chat_id,target_lender_id,status,created_at);
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_requests

    async def request_api(request: Any):
        user, start_param = core._webapp_auth(request)
        if user is None:
            return core.web.json_response(
                {"ok": False, "reason": start_param or "Нет авторизации Telegram."},
                status=401,
            )
        try:
            if request.method == "POST":
                try:
                    data = await request.json()
                    if not isinstance(data, dict):
                        data = {}
                except Exception:
                    data = {}
            else:
                data = {}
            chat_id = _chat_id(start_param, request, data)
            borrower_id = int(user.id)
            borrower = await core.db.get_player(chat_id, borrower_id)
            if borrower is None:
                raise PermissionError("Сначала используй бота в этой беседе.")

            if request.method == "GET":
                return core.web.json_response(
                    {"ok": True, "pending": await _pending_payload(core, chat_id, borrower_id)}
                )

            lender_id = _safe_int(data.get("lender_id"))
            amount = _safe_int(data.get("amount"))
            interest = _safe_int(data.get("interest"), -1)
            days = _safe_int(data.get("days"), -1)
            if lender_id <= 0 or lender_id == borrower_id:
                raise ValueError("Выбери другого участника в качестве кредитора.")
            if amount < finance.LOAN_MIN or amount > finance.LOAN_MAX:
                raise ValueError(f"Сумма заявки: {finance.LOAN_MIN}–{_fmt(finance.LOAN_MAX)}.")
            if interest < 0 or interest > finance.LOAN_INTEREST_MAX:
                raise ValueError(f"Процент должен быть от 0 до {finance.LOAN_INTEREST_MAX}%.")
            if days < finance.LOAN_TERM_MIN_DAYS or days > finance.LOAN_TERM_MAX_DAYS:
                raise ValueError(
                    f"Срок должен быть от {finance.LOAN_TERM_MIN_DAYS} до {finance.LOAN_TERM_MAX_DAYS} дней."
                )

            await finance._mark_overdue(core, chat_id=chat_id, user_id=borrower_id)
            await finance._mark_overdue(core, chat_id=chat_id, user_id=lender_id)
            if await finance._has_overdue(core, chat_id, borrower_id):
                raise ValueError("Сначала погаси просроченный долг.")
            if await finance._has_overdue(core, chat_id, lender_id):
                raise ValueError("У выбранного кредитора есть просроченный долг.")
            if await finance._is_blocked(core, chat_id, lender_id):
                raise ValueError("Выбранному участнику заблокированы финансовые операции.")
            if await _pending_payload(core, chat_id, borrower_id) is not None:
                raise ValueError("У тебя уже есть активная заявка. Отзови её в чате или дождись решения.")

            conn = core.db._require_connection()
            cursor = await conn.execute(
                "SELECT * FROM players WHERE chat_id=? AND user_id=?",
                (chat_id, lender_id),
            )
            lender = await cursor.fetchone()
            if lender is None:
                raise ValueError("Выбранный участник ещё не использовал бота в этой беседе.")
            if int(lender["points"]) < amount:
                raise ValueError(
                    f"У выбранного участника сейчас недостаточно влияния: {_fmt(int(lender['points']))}."
                )

            role_name, limit = finance._role_limit(core, int(borrower.points))
            cursor = await conn.execute(
                """
                SELECT COALESCE(SUM(total_due-repaid),0) total
                FROM finance_loans_v112
                WHERE chat_id=? AND borrower_id=? AND status IN ('active','overdue','offered')
                """,
                (chat_id, borrower_id),
            )
            outstanding = _safe_int((await cursor.fetchone())["total"])
            total_due = math.ceil(amount * (100 + interest) / 100)
            if outstanding + total_due > limit:
                raise ValueError(
                    f"Лимит долга роли «{role_name}» — {_fmt(limit)}. Уже занято: {_fmt(outstanding)}."
                )

            request_id = secrets.token_urlsafe(9)
            now = _now()
            async with core.db.lock:
                await conn.execute(
                    """
                    INSERT INTO finance_loan_requests_v118(
                        request_id,chat_id,borrower_id,target_lender_id,amount,
                        interest_percent,term_days,total_due,status,created_at,expires_at
                    ) VALUES(?,?,?,?,?,?,?,?,'pending',?,?)
                    """,
                    (
                        request_id,
                        chat_id,
                        borrower_id,
                        lender_id,
                        amount,
                        interest,
                        days,
                        total_due,
                        now,
                        now + REQUEST_TTL,
                    ),
                )
                await conn.commit()

            borrower_name = html.escape(str(borrower.full_name))
            lender_name = html.escape(str(lender["full_name"] or f"ID {lender_id}"))
            reliability, label, _ = finance._credit_text(
                await finance._credit_stats(core, chat_id, borrower_id)
            )
            bot = request.app["bot"]
            try:
                message = await bot.send_message(
                    chat_id,
                    "📣 <b>ЗАЯВКА НА ЗАЁМ</b>\n\n"
                    f"Заявитель: <a href=\"tg://user?id={borrower_id}\">{borrower_name}</a>\n"
                    f"Обращается к: <a href=\"tg://user?id={lender_id}\">{lender_name}</a>\n\n"
                    f"Нужно: <b>{_fmt(amount)}</b> влияния\n"
                    f"Процент: <b>{interest}%</b>\n"
                    f"Вернуть: <b>{_fmt(total_due)}</b>\n"
                    f"Срок: <b>{days} дн.</b>\n"
                    f"Репутация заявителя: <b>{label} · {reliability}%</b>\n\n"
                    "Одобрить или отклонить заявку может только выбранный кредитор. "
                    "Заявка действует 24 часа.",
                    reply_markup=_request_markup(request_id),
                )
            except Exception:
                async with core.db.lock:
                    await conn.execute(
                        "UPDATE finance_loan_requests_v118 SET status='expired',completed_at=? WHERE request_id=?",
                        (_now(), request_id),
                    )
                    await conn.commit()
                raise ValueError("Telegram не разрешил опубликовать заявку в этой беседе.")

            async with core.db.lock:
                await conn.execute(
                    "UPDATE finance_loan_requests_v118 SET message_id=? WHERE request_id=?",
                    (int(message.message_id), request_id),
                )
                await conn.commit()
            return core.web.json_response(
                {
                    "ok": True,
                    "message": "Заявка опубликована в чате. Кредитор получил кнопки решения.",
                    "pending": await _pending_payload(core, chat_id, borrower_id),
                }
            )
        except PermissionError as error:
            return core.web.json_response({"ok": False, "reason": str(error)}, status=403)
        except ValueError as error:
            return core.web.json_response({"ok": False, "reason": str(error)}, status=400)
        except Exception:
            return core.web.json_response(
                {"ok": False, "reason": "Не удалось создать заявку. Попробуй ещё раз."},
                status=500,
            )

    core.finance_request_api_v118 = request_api

    async def _load_request(request_id: str) -> Any | None:
        conn = core.db._require_connection()
        cursor = await conn.execute(
            "SELECT * FROM finance_loan_requests_v118 WHERE request_id=?",
            (request_id,),
        )
        return await cursor.fetchone()

    @core.router.callback_query(F.data.startswith("fin118:approve:"))
    async def approve_request_v118(callback: CallbackQuery) -> None:
        if not callback.from_user:
            return
        request_id = str(callback.data or "").split(":", 2)[-1]
        initial = await _load_request(request_id)
        if initial is None or str(initial["status"]) != "pending":
            await callback.answer("Заявка уже обработана.", show_alert=True)
            return
        if int(initial["target_lender_id"]) != int(callback.from_user.id):
            await callback.answer("Одобрить может только выбранный кредитор.", show_alert=True)
            return
        chat_id = int(initial["chat_id"])
        borrower_id = int(initial["borrower_id"])
        lender_id = int(initial["target_lender_id"])
        await finance._mark_overdue(core, chat_id=chat_id, user_id=borrower_id)
        await finance._mark_overdue(core, chat_id=chat_id, user_id=lender_id)

        conn = core.db._require_connection()
        now = _now()
        async with core.db.lock:
            cursor = await conn.execute(
                "SELECT * FROM finance_loan_requests_v118 WHERE request_id=?",
                (request_id,),
            )
            row = await cursor.fetchone()
            if row is None or str(row["status"]) != "pending":
                await callback.answer("Заявка уже обработана.", show_alert=True)
                return
            if int(row["expires_at"]) <= now:
                await conn.execute(
                    "UPDATE finance_loan_requests_v118 SET status='expired',completed_at=? WHERE request_id=?",
                    (now, request_id),
                )
                await conn.commit()
                await callback.answer("Срок заявки истёк.", show_alert=True)
                return
            cursor = await conn.execute(
                "SELECT points,full_name FROM players WHERE chat_id=? AND user_id=?",
                (chat_id, lender_id),
            )
            lender = await cursor.fetchone()
            cursor = await conn.execute(
                "SELECT points,full_name FROM players WHERE chat_id=? AND user_id=?",
                (chat_id, borrower_id),
            )
            borrower = await cursor.fetchone()
            amount = int(row["amount"])
            if lender is None or int(lender["points"]) < amount:
                await callback.answer("У тебя недостаточно влияния для одобрения.", show_alert=True)
                return
            cursor = await conn.execute(
                "SELECT 1 FROM finance_loans_v112 WHERE chat_id=? AND borrower_id IN (?,?) AND status='overdue' LIMIT 1",
                (chat_id, lender_id, borrower_id),
            )
            if await cursor.fetchone() is not None:
                await callback.answer("Заявку нельзя одобрить из-за просроченного долга.", show_alert=True)
                return
            cursor = await conn.execute(
                "SELECT transfers_blocked FROM finance_user_state_v112 WHERE chat_id=? AND user_id=?",
                (chat_id, lender_id),
            )
            blocked = await cursor.fetchone()
            if blocked and int(blocked["transfers_blocked"]):
                await callback.answer("Тебе заблокированы финансовые операции.", show_alert=True)
                return
            role_name, limit = finance._role_limit(core, int(borrower["points"]) if borrower else 0)
            cursor = await conn.execute(
                """
                SELECT COALESCE(SUM(total_due-repaid),0) total
                FROM finance_loans_v112
                WHERE chat_id=? AND borrower_id=? AND status IN ('active','overdue','offered')
                """,
                (chat_id, borrower_id),
            )
            existing = _safe_int((await cursor.fetchone())["total"])
            if existing + int(row["total_due"]) > limit:
                await callback.answer(
                    f"Превышен лимит долга роли «{role_name}»: {_fmt(limit)}.",
                    show_alert=True,
                )
                return

            loan_id = secrets.token_urlsafe(9)
            due_at = now + int(row["term_days"]) * 86400
            await conn.execute(
                "UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?",
                (amount, now, chat_id, lender_id),
            )
            await conn.execute(
                "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                (amount, now, chat_id, borrower_id),
            )
            await conn.execute(
                """
                INSERT INTO finance_loans_v112(
                    loan_id,chat_id,lender_id,borrower_id,principal,interest_percent,
                    term_days,total_due,repaid,status,created_at,offer_expires_at,
                    accepted_at,due_at,late_fee_applied,was_overdue
                ) VALUES(?,?,?,?,?,?,?,?,0,'active',?,?,?,?,0,0)
                """,
                (
                    loan_id,
                    chat_id,
                    lender_id,
                    borrower_id,
                    amount,
                    int(row["interest_percent"]),
                    int(row["term_days"]),
                    int(row["total_due"]),
                    int(row["created_at"]),
                    now,
                    now,
                    due_at,
                ),
            )
            await conn.execute(
                """
                UPDATE finance_loan_requests_v118
                SET status='approved',lender_id=?,loan_id=?,completed_at=?
                WHERE request_id=? AND status='pending'
                """,
                (lender_id, loan_id, now, request_id),
            )
            await conn.execute(
                "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                (chat_id, lender_id, -amount, "transfer_loan_request_issued_v118", now),
            )
            await conn.execute(
                "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                (chat_id, borrower_id, amount, "transfer_loan_request_received_v118", now),
            )
            await conn.commit()

        lender_name = html.escape(await finance._player_name(core, chat_id, lender_id))
        borrower_name = html.escape(await finance._player_name(core, chat_id, borrower_id))
        text = (
            "✅ <b>ЗАЯВКА ОДОБРЕНА</b>\n\n"
            f"Кредитор: <a href=\"tg://user?id={lender_id}\">{lender_name}</a>\n"
            f"Заёмщик: <a href=\"tg://user?id={borrower_id}\">{borrower_name}</a>\n\n"
            f"Передано: <b>{_fmt(int(initial['amount']))}</b> влияния\n"
            f"Вернуть: <b>{_fmt(int(initial['total_due']))}</b>\n"
            f"Срок: <b>{int(initial['term_days'])} дн.</b>\n\n"
            f"Договор: <code>#{finance._loan_token(loan_id)}</code>"
        )
        if callback.message:
            await callback.message.edit_text(text)
        await callback.answer("Заявка одобрена. Влияние передано!", show_alert=True)

    @core.router.callback_query(F.data.startswith("fin118:reject:"))
    async def reject_request_v118(callback: CallbackQuery) -> None:
        if not callback.from_user:
            return
        request_id = str(callback.data or "").split(":", 2)[-1]
        conn = core.db._require_connection()
        async with core.db.lock:
            cursor = await conn.execute(
                "SELECT * FROM finance_loan_requests_v118 WHERE request_id=?",
                (request_id,),
            )
            row = await cursor.fetchone()
            if row is None or str(row["status"]) != "pending":
                await callback.answer("Заявка уже обработана.", show_alert=True)
                return
            if int(row["target_lender_id"]) != int(callback.from_user.id):
                await callback.answer("Отклонить может только выбранный кредитор.", show_alert=True)
                return
            await conn.execute(
                "UPDATE finance_loan_requests_v118 SET status='rejected',completed_at=? WHERE request_id=?",
                (_now(), request_id),
            )
            await conn.commit()
        borrower_name = html.escape(
            await finance._player_name(core, int(row["chat_id"]), int(row["borrower_id"]))
        )
        if callback.message:
            await callback.message.edit_text(
                "❌ <b>ЗАЯВКА ОТКЛОНЕНА</b>\n\n"
                f"Заявка {borrower_name} на <b>{_fmt(int(row['amount']))}</b> влияния отклонена."
            )
        await callback.answer("Заявка отклонена.")

    @core.router.callback_query(F.data.startswith("fin118:cancel:"))
    async def cancel_request_v118(callback: CallbackQuery) -> None:
        if not callback.from_user:
            return
        request_id = str(callback.data or "").split(":", 2)[-1]
        conn = core.db._require_connection()
        async with core.db.lock:
            cursor = await conn.execute(
                "SELECT * FROM finance_loan_requests_v118 WHERE request_id=?",
                (request_id,),
            )
            row = await cursor.fetchone()
            if row is None or str(row["status"]) != "pending":
                await callback.answer("Заявка уже обработана.", show_alert=True)
                return
            if int(row["borrower_id"]) != int(callback.from_user.id):
                await callback.answer("Отозвать заявку может только заявитель.", show_alert=True)
                return
            await conn.execute(
                "UPDATE finance_loan_requests_v118 SET status='cancelled',completed_at=? WHERE request_id=?",
                (_now(), request_id),
            )
            await conn.commit()
        if callback.message:
            await callback.message.edit_text("🗑 <b>ЗАЯВКА ОТОЗВАНА</b>\n\nЗаявитель отменил запрос на заём.")
        await callback.answer("Заявка отозвана.")

    original_start_server = core.start_webapp_server

    async def start_server_with_request_routes(bot: Any):
        original_app_runner = core.web.AppRunner

        def app_runner_factory(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)

            async def finance_v118_index(_: Any):
                return core.web.FileResponse(
                    APP_DIR / "index.html",
                    headers={
                        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                        "Pragma": "no-cache",
                        "Expires": "0",
                        "X-Finance-Center": VERSION,
                    },
                )

            for path in ("/finance-v118", "/finance-v118/", "/finance-v118/index.html"):
                if ("GET", path) not in keys and ("*", path) not in keys:
                    app.router.add_get(path, finance_v118_index)
                    keys.add(("GET", path))
            for path in ("/finance-v114/api/request", "/finance/api/request", "/finance-v118/api/request"):
                if ("GET", path) not in keys and ("*", path) not in keys:
                    app.router.add_get(path, request_api)
                    keys.add(("GET", path))
                if ("POST", path) not in keys and ("*", path) not in keys:
                    app.router.add_post(path, request_api)
                    keys.add(("POST", path))
            return original_app_runner(app, *args, **kwargs)

        core.web.AppRunner = app_runner_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.AppRunner = original_app_runner

    core.start_webapp_server = start_server_with_request_routes

    handlers = core.router.callback_query.handlers
    priority_names = {
        "approve_request_v118",
        "reject_request_v118",
        "cancel_request_v118",
    }
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") in priority_names
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
