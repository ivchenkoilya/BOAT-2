from __future__ import annotations

import html
import math
import secrets
import time
from pathlib import Path
from typing import Any

from aiohttp import web
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import finance_system_v112 as finance


VERSION = "Reality 114 · Финансовый центр"
APP_DIR = Path(__file__).resolve().parent / "financeapp_v114"
FINANCE_PREFIX = "finance_"


def _now() -> int:
    return int(time.time())


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _fmt(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _parse_chat_id(start_param: str | None, data: dict[str, Any], request: web.Request) -> int:
    raw = str(start_param or "")
    if raw.startswith(FINANCE_PREFIX):
        raw = raw[len(FINANCE_PREFIX):]
    else:
        raw = str(data.get("chat_id") or request.query.get("chat_id") or "")
    try:
        chat_id = int(raw)
    except (TypeError, ValueError):
        raise ValueError("Не найдена беседа для финансовой операции.")
    if chat_id >= 0:
        raise ValueError("Финансовый центр работает только внутри групповой беседы.")
    return chat_id


def _deal_payload(row: Any, *, borrower_view: bool) -> dict[str, Any]:
    remaining = max(0, int(row["total_due"]) - int(row["repaid"]))
    now = _now()
    status = str(row["status"])
    if status == "overdue":
        time_text = "Просрочен"
    else:
        seconds = max(0, int(row["due_at"] or now) - now)
        time_text = f"{seconds // 86400} д. {(seconds % 86400) // 3600} ч."
    other_name = row["lender_name"] if borrower_view else row["borrower_name"]
    return {
        "loan_id": str(row["loan_id"]),
        "token": finance._loan_token(str(row["loan_id"])),
        "other_name": str(other_name or "Участник"),
        "principal": int(row["principal"]),
        "interest": int(row["interest_percent"]),
        "total_due": int(row["total_due"]),
        "repaid": int(row["repaid"]),
        "remaining": remaining,
        "status": status,
        "time_text": time_text,
    }


def install_finance_miniapp_v114(core: Any) -> None:
    if getattr(core, "_finance_miniapp_v114_installed", False):
        return
    core._finance_miniapp_v114_installed = True
    core.FINANCE_SYSTEM_VERSION = VERSION

    async def payload(request: web.Request) -> dict[str, Any]:
        try:
            value = await request.json()
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    async def auth(request: web.Request) -> tuple[Any, int, dict[str, Any], Any]:
        user, start_param = core._webapp_auth(request)
        if user is None:
            raise PermissionError(start_param or "Нет авторизации Telegram.")
        data = await payload(request)
        chat_id = _parse_chat_id(start_param, data, request)
        player = await core.db.get_player(chat_id, int(user.id))
        if player is None:
            raise PermissionError("Сначала используй бота в нужной групповой беседе.")
        return user, chat_id, data, player

    def error_response(error: Exception) -> web.Response:
        status = 403 if isinstance(error, PermissionError) else 400
        return core.web.json_response({"ok": False, "reason": str(error)}, status=status)

    async def state_api(request: web.Request) -> web.Response:
        try:
            user, chat_id, _, player = await auth(request)
            await finance._mark_overdue(core, chat_id=chat_id, user_id=int(user.id))
            conn = core.db._require_connection()
            cursor = await conn.execute(
                """
                SELECT user_id,username,full_name,points
                FROM players
                WHERE chat_id=? AND user_id<>?
                ORDER BY message_count DESC,points DESC,updated_at DESC
                LIMIT 100
                """,
                (chat_id, int(user.id)),
            )
            participants = [
                {
                    "user_id": int(row["user_id"]),
                    "username": str(row["username"] or ""),
                    "name": str(row["full_name"] or f"ID {row['user_id']}"),
                    "points": int(row["points"]),
                }
                for row in await cursor.fetchall()
            ]
            cursor = await conn.execute(
                """
                SELECT l.*,COALESCE(b.full_name,'Участник') borrower_name,
                       COALESCE(c.full_name,'Участник') lender_name
                FROM finance_loans_v112 l
                LEFT JOIN players b ON b.chat_id=l.chat_id AND b.user_id=l.borrower_id
                LEFT JOIN players c ON c.chat_id=l.chat_id AND c.user_id=l.lender_id
                WHERE l.chat_id=? AND l.borrower_id=? AND l.status IN ('active','overdue')
                ORDER BY CASE l.status WHEN 'overdue' THEN 0 ELSE 1 END,l.due_at ASC
                """,
                (chat_id, int(user.id)),
            )
            debts = [_deal_payload(row, borrower_view=True) for row in await cursor.fetchall()]
            cursor = await conn.execute(
                """
                SELECT l.*,COALESCE(b.full_name,'Участник') borrower_name,
                       COALESCE(c.full_name,'Участник') lender_name
                FROM finance_loans_v112 l
                LEFT JOIN players b ON b.chat_id=l.chat_id AND b.user_id=l.borrower_id
                LEFT JOIN players c ON c.chat_id=l.chat_id AND c.user_id=l.lender_id
                WHERE l.chat_id=? AND l.lender_id=? AND l.status IN ('active','overdue')
                ORDER BY CASE l.status WHEN 'overdue' THEN 0 ELSE 1 END,l.due_at ASC
                """,
                (chat_id, int(user.id)),
            )
            owed = [_deal_payload(row, borrower_view=False) for row in await cursor.fetchall()]
            stats = await finance._credit_stats(core, chat_id, int(user.id))
            reliability, label, note = finance._credit_text(stats)
            return core.web.json_response(
                {
                    "ok": True,
                    "version": VERSION,
                    "chat_id": chat_id,
                    "player": {
                        "user_id": int(user.id),
                        "name": str(player.full_name),
                        "username": str(player.username or ""),
                        "points": int(player.points),
                    },
                    "participants": participants,
                    "debts": debts,
                    "owed": owed,
                    "totals": {
                        "debt": sum(item["remaining"] for item in debts),
                        "owed": sum(item["remaining"] for item in owed),
                    },
                    "credit": {
                        "reliability": reliability,
                        "label": label,
                        "note": note,
                        **stats,
                    },
                    "limits": {
                        "transfer_min": finance.TRANSFER_MIN,
                        "transfer_max": finance.TRANSFER_MAX,
                        "transfer_daily": finance.TRANSFER_DAILY_LIMIT,
                        "loan_min": finance.LOAN_MIN,
                        "loan_max": finance.LOAN_MAX,
                        "interest_max": finance.LOAN_INTEREST_MAX,
                        "days_min": finance.LOAN_TERM_MIN_DAYS,
                        "days_max": finance.LOAN_TERM_MAX_DAYS,
                    },
                }
            )
        except (PermissionError, ValueError) as error:
            return error_response(error)

    async def transfer_action(user: Any, chat_id: int, data: dict[str, Any]) -> tuple[str, int]:
        sender_id = int(user.id)
        recipient_id = _safe_int(data.get("recipient_id"))
        amount = _safe_int(data.get("amount"))
        if recipient_id == sender_id:
            raise ValueError("Нельзя переводить влияние самому себе.")
        if amount < finance.TRANSFER_MIN or amount > finance.TRANSFER_MAX:
            raise ValueError(
                f"Сумма перевода должна быть от {finance.TRANSFER_MIN} до {_fmt(finance.TRANSFER_MAX)}."
            )
        await finance._mark_overdue(core, chat_id=chat_id, user_id=sender_id)
        conn = core.db._require_connection()
        now = _now()
        async with core.db.lock:
            cursor = await conn.execute(
                "SELECT * FROM players WHERE chat_id=? AND user_id=?",
                (chat_id, sender_id),
            )
            sender = await cursor.fetchone()
            cursor = await conn.execute(
                "SELECT * FROM players WHERE chat_id=? AND user_id=?",
                (chat_id, recipient_id),
            )
            recipient = await cursor.fetchone()
            if sender is None or recipient is None:
                raise ValueError("Участник не найден в этой беседе.")
            if int(sender["points"]) < amount:
                raise ValueError(f"Недостаточно влияния. Баланс: {_fmt(int(sender['points']))}.")
            cursor = await conn.execute(
                "SELECT 1 FROM finance_loans_v112 WHERE chat_id=? AND borrower_id=? AND status='overdue' LIMIT 1",
                (chat_id, sender_id),
            )
            if await cursor.fetchone() is not None:
                raise ValueError("Сначала погаси просроченный долг.")
            cursor = await conn.execute(
                "SELECT transfers_blocked,last_transfer_at FROM finance_user_state_v112 WHERE chat_id=? AND user_id=?",
                (chat_id, sender_id),
            )
            state = await cursor.fetchone()
            if state and int(state["transfers_blocked"]):
                raise ValueError("Администратор заблокировал исходящие переводы.")
            wait = finance.TRANSFER_COOLDOWN - (now - _safe_int(state["last_transfer_at"] if state else 0))
            if wait > 0:
                raise ValueError(f"Следующий перевод доступен через {wait} сек.")
            cursor = await conn.execute(
                "SELECT COALESCE(SUM(amount),0) total FROM finance_transfers_v112 WHERE chat_id=? AND sender_id=? AND status='completed' AND completed_at>=?",
                (chat_id, sender_id, finance._day_start()),
            )
            used = _safe_int((await cursor.fetchone())["total"])
            if used + amount > finance.TRANSFER_DAILY_LIMIT:
                raise ValueError(
                    f"Дневной лимит {_fmt(finance.TRANSFER_DAILY_LIMIT)}. Сегодня уже отправлено {_fmt(used)}."
                )
            transfer_id = secrets.token_urlsafe(9)
            await conn.execute(
                "UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?",
                (amount, now, chat_id, sender_id),
            )
            await conn.execute(
                "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                (amount, now, chat_id, recipient_id),
            )
            await conn.execute(
                """
                INSERT INTO finance_transfers_v112(
                    transfer_id,chat_id,sender_id,recipient_id,amount,status,
                    created_at,expires_at,completed_at
                ) VALUES(?,?,?,?,?,'completed',?,?,?)
                """,
                (transfer_id, chat_id, sender_id, recipient_id, amount, now, now, now),
            )
            await conn.execute(
                "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                (chat_id, sender_id, -amount, "transfer_sent_v114", now),
            )
            await conn.execute(
                "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                (chat_id, recipient_id, amount, "transfer_received_v114", now),
            )
            await conn.execute(
                """
                INSERT INTO finance_user_state_v112(chat_id,user_id,last_transfer_at)
                VALUES(?,?,?)
                ON CONFLICT(chat_id,user_id) DO UPDATE SET last_transfer_at=excluded.last_transfer_at
                """,
                (chat_id, sender_id, now),
            )
            await conn.commit()
            sender_name = html.escape(str(sender["full_name"] or f"ID {sender_id}"))
            recipient_name = html.escape(str(recipient["full_name"] or f"ID {recipient_id}"))
            new_balance = int(sender["points"]) - amount
        bot = finance._RUNTIME_BOT.get("bot")
        if bot is not None:
            try:
                await bot.send_message(
                    chat_id,
                    "💸 <b>ПЕРЕВОД ВЛИЯНИЯ</b>\n\n"
                    f"<a href=\"tg://user?id={sender_id}\">{sender_name}</a> передал "
                    f"<a href=\"tg://user?id={recipient_id}\">{recipient_name}</a> "
                    f"<b>{_fmt(amount)}</b> влияния.\n\n"
                    "Перевод не считается заработком и не даёт очки Древа.",
                )
            except Exception:
                pass
        return f"Переведено {_fmt(amount)} влияния.", new_balance

    async def loan_action(user: Any, chat_id: int, data: dict[str, Any]) -> str:
        lender_id = int(user.id)
        borrower_id = _safe_int(data.get("borrower_id"))
        amount = _safe_int(data.get("amount"))
        percent = _safe_int(data.get("interest"), -1)
        days = _safe_int(data.get("days"), -1)
        if borrower_id == lender_id:
            raise ValueError("Нельзя выдать заём самому себе.")
        if amount < finance.LOAN_MIN or amount > finance.LOAN_MAX:
            raise ValueError(f"Сумма займа: {finance.LOAN_MIN}–{_fmt(finance.LOAN_MAX)}.")
        if percent < 0 or percent > finance.LOAN_INTEREST_MAX:
            raise ValueError(f"Процент должен быть от 0 до {finance.LOAN_INTEREST_MAX}%.")
        if days < finance.LOAN_TERM_MIN_DAYS or days > finance.LOAN_TERM_MAX_DAYS:
            raise ValueError(
                f"Срок должен быть от {finance.LOAN_TERM_MIN_DAYS} до {finance.LOAN_TERM_MAX_DAYS} дней."
            )
        await finance._mark_overdue(core, chat_id=chat_id, user_id=lender_id)
        await finance._mark_overdue(core, chat_id=chat_id, user_id=borrower_id)
        conn = core.db._require_connection()
        now = _now()
        async with core.db.lock:
            cursor = await conn.execute(
                "SELECT * FROM players WHERE chat_id=? AND user_id=?",
                (chat_id, lender_id),
            )
            lender = await cursor.fetchone()
            cursor = await conn.execute(
                "SELECT * FROM players WHERE chat_id=? AND user_id=?",
                (chat_id, borrower_id),
            )
            borrower = await cursor.fetchone()
            if lender is None or borrower is None:
                raise ValueError("Участник не найден в этой беседе.")
            if int(lender["points"]) < amount:
                raise ValueError(f"Недостаточно влияния. Баланс: {_fmt(int(lender['points']))}.")
            cursor = await conn.execute(
                "SELECT 1 FROM finance_loans_v112 WHERE chat_id=? AND borrower_id IN (?,?) AND status='overdue' LIMIT 1",
                (chat_id, lender_id, borrower_id),
            )
            if await cursor.fetchone() is not None:
                raise ValueError("Нельзя создать новый заём при просроченном долге одной из сторон.")
            cursor = await conn.execute(
                "SELECT transfers_blocked FROM finance_user_state_v112 WHERE chat_id=? AND user_id=?",
                (chat_id, lender_id),
            )
            blocked = await cursor.fetchone()
            if blocked and int(blocked["transfers_blocked"]):
                raise ValueError("Администратор заблокировал финансовые операции.")
            role_name, limit = finance._role_limit(core, int(borrower["points"]))
            cursor = await conn.execute(
                "SELECT COALESCE(SUM(total_due-repaid),0) total FROM finance_loans_v112 WHERE chat_id=? AND borrower_id=? AND status IN ('active','overdue','offered')",
                (chat_id, borrower_id),
            )
            outstanding = _safe_int((await cursor.fetchone())["total"])
            total_due = math.ceil(amount * (100 + percent) / 100)
            if outstanding + total_due > limit:
                raise ValueError(
                    f"Лимит долга для роли «{role_name}» — {_fmt(limit)}. Уже занято или предложено: {_fmt(outstanding)}."
                )
            loan_id = secrets.token_urlsafe(9)
            await conn.execute(
                """
                INSERT INTO finance_loans_v112(
                    loan_id,chat_id,lender_id,borrower_id,principal,
                    interest_percent,term_days,total_due,status,created_at,offer_expires_at
                ) VALUES(?,?,?,?,?,?,?,?,'offered',?,?)
                """,
                (
                    loan_id,
                    chat_id,
                    lender_id,
                    borrower_id,
                    amount,
                    percent,
                    days,
                    total_due,
                    now,
                    now + finance.LOAN_OFFER_TTL,
                ),
            )
            await conn.commit()
            lender_name = html.escape(str(lender["full_name"] or f"ID {lender_id}"))
            borrower_name = html.escape(str(borrower["full_name"] or f"ID {borrower_id}"))
        bot = finance._RUNTIME_BOT.get("bot")
        if bot is None:
            async with core.db.lock:
                await conn.execute(
                    "UPDATE finance_loans_v112 SET status='expired',completed_at=? WHERE loan_id=?",
                    (_now(), loan_id),
                )
                await conn.commit()
            raise ValueError("Бот ещё не готов публиковать договоры. Попробуй через несколько секунд.")
        stats = await finance._credit_stats(core, chat_id, borrower_id)
        reliability, label, _ = finance._credit_text(stats)
        try:
            await bot.send_message(
                chat_id,
                "🤝 <b>НОВЫЙ ДОГОВОР ВЛИЯНИЯ</b>\n\n"
                f"Кредитор: <a href=\"tg://user?id={lender_id}\">{lender_name}</a>\n"
                f"Заёмщик: <a href=\"tg://user?id={borrower_id}\">{borrower_name}</a>\n\n"
                f"Получит: <b>{_fmt(amount)}</b> влияния\n"
                f"Процент: <b>{percent}%</b>\n"
                f"Вернуть: <b>{_fmt(total_due)}</b>\n"
                f"Срок: <b>{days} дн.</b>\n"
                f"Репутация заёмщика: <b>{label} · {reliability}%</b>\n\n"
                "После принятия договор вступает в силу и отменить его нельзя.",
                reply_markup=finance._loan_markup(loan_id),
            )
        except Exception:
            async with core.db.lock:
                await conn.execute(
                    "UPDATE finance_loans_v112 SET status='expired',completed_at=? WHERE loan_id=?",
                    (_now(), loan_id),
                )
                await conn.commit()
            raise ValueError("Telegram не разрешил опубликовать договор в этой беседе.")
        return "Договор опубликован в чате. Заёмщик должен нажать «Принять заём»."

    async def repay_action(user: Any, chat_id: int, data: dict[str, Any]) -> str:
        loan_id = str(data.get("loan_id") or "")
        raw_amount = data.get("amount")
        amount: int | str = "all" if str(raw_amount).casefold() == "all" else _safe_int(raw_amount)
        ok, text = await finance._perform_repayment(core, chat_id, int(user.id), loan_id, amount)
        if not ok:
            raise ValueError(text)
        bot = finance._RUNTIME_BOT.get("bot")
        if bot is not None:
            try:
                await bot.send_message(chat_id, text)
            except Exception:
                pass
        return "Платёж проведён и опубликован в чате."

    async def action_api(request: web.Request) -> web.Response:
        try:
            user, chat_id, data, _ = await auth(request)
            action = str(data.get("action") or "")
            if action == "transfer":
                message, balance = await transfer_action(user, chat_id, data)
                return core.web.json_response({"ok": True, "message": message, "balance": balance})
            if action == "loan":
                return core.web.json_response(
                    {"ok": True, "message": await loan_action(user, chat_id, data)}
                )
            if action == "repay":
                return core.web.json_response(
                    {"ok": True, "message": await repay_action(user, chat_id, data)}
                )
            raise ValueError("Неизвестная финансовая операция.")
        except (PermissionError, ValueError) as error:
            return error_response(error)
        except Exception:
            return core.web.json_response(
                {"ok": False, "reason": "Не удалось выполнить операцию. Попробуй ещё раз."},
                status=500,
            )

    def file_response(path: Path) -> web.FileResponse:
        return core.web.FileResponse(
            path,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Finance-Center": VERSION,
            },
        )

    async def finance_index(_: web.Request) -> web.StreamResponse:
        return file_response(APP_DIR / "index.html")

    original_start_server = core.start_webapp_server

    async def start_server_with_finance_app(bot: Any):
        previous_application = core.web.Application

        def application_factory(*args: Any, **kwargs: Any):
            app = previous_application(*args, **kwargs)
            app.router.add_get("/finance-v114", finance_index)
            app.router.add_get("/finance-v114/", finance_index)
            app.router.add_get("/finance-v114/index.html", finance_index)
            app.router.add_get("/finance-v114/api/state", state_api)
            app.router.add_post("/finance-v114/api/action", action_api)
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = previous_application

    core.start_webapp_server = start_server_with_finance_app

    def finance_link(chat_id: int) -> str:
        if not core.WEBAPP_PUBLIC_URL:
            return ""
        return (
            f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/finance-v114/"
            f"?chat_id={int(chat_id)}&build=114-{_now()}"
        )

    @core.router.message(Command("finance", "money", "bank"))
    async def cmd_finance_app_v114(message: Message) -> None:
        if not await core.require_group_command(message, "Финансовый центр"):
            return
        if not message.from_user:
            return
        await core.db.upsert_player(int(message.chat.id), message.from_user)
        link = finance_link(int(message.chat.id))
        if not link:
            await message.answer("⚠️ Адрес Mini App не настроен. Укажи WEBAPP_PUBLIC_URL.")
            return
        await message.answer(
            "💸 <b>ФИНАНСОВЫЙ ЦЕНТР</b>\n\n"
            "Передавай влияние, создавай договоры займа и погашай долги кнопками. "
            "Все принятые договоры и платежи автоматически публикуются в этой беседе.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="💸 ОТКРЫТЬ ФИНАНСОВЫЙ ЦЕНТР", url=link)]
                ]
            ),
        )

    handlers = core.router.message.handlers
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_finance_app_v114"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
