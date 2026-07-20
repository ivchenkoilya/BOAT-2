from __future__ import annotations

import asyncio
import html
import math
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiohttp import web
from aiogram import F
from aiogram.filters import Command
from aiogram.types import BotCommand, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message


VERSION = "Reality 112 · Переводы и займы"
TRANSFER_MIN = 10
TRANSFER_MAX = 5_000
TRANSFER_DAILY_LIMIT = 10_000
TRANSFER_COOLDOWN = 60
TRANSFER_REQUEST_TTL = 10 * 60
LOAN_MIN = 50
LOAN_MAX = 10_000
LOAN_INTEREST_MAX = 20
LOAN_TERM_MIN_DAYS = 1
LOAN_TERM_MAX_DAYS = 14
LOAN_OFFER_TTL = 15 * 60
LATE_FEE_RATE = 0.05
OVERDUE_WITHHOLD_RATE = 0.30
OVERDUE_CHECK_INTERVAL = 60
BASE_DIR = Path(__file__).resolve().parent
ADMIN_SCRIPT = BASE_DIR / "adminapp_v112" / "finance-admin.js"
_RUNTIME_BOT: dict[str, Any] = {"bot": None}
_NOTICE_AMOUNTS: dict[tuple[int, int], int] = {}
_NOTICE_TASKS: dict[tuple[int, int], asyncio.Task[Any]] = {}
_OVERDUE_LOOP_STARTED = False
PROTECTED_EARNING_WORDS = (
    "transfer_", "admin", "restore", "refund", "compensation",
    "hero_day", "reality_event_", "void",
)


def _now() -> int:
    return int(time.time())


def _day_start() -> int:
    value = datetime.now(timezone.utc)
    return int(datetime(value.year, value.month, value.day, tzinfo=timezone.utc).timestamp())


def _fmt(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _before_points(value: Any) -> int:
    return int(value.points) if hasattr(value, "points") else int(value)


def _remaining(row: Any) -> int:
    return max(0, int(row["total_due"]) - int(row["repaid"]))


def _loan_token(loan_id: str) -> str:
    return str(loan_id)[:8]


def _role_limit(core: Any, points: int) -> tuple[str, int]:
    value = int(points)
    if value >= int(core.HERO_MIN_POINTS):
        return "Главный герой", 10_000
    if value >= int(core.SECONDARY_MIN_POINTS):
        return "Второстепенная роль", 5_000
    if value >= int(core.EXTRAS_MIN_POINTS):
        return "Массовка", 2_000
    if value >= int(core.DUST_MIN_POINTS):
        return "Пыль", 1_000
    return "Декорация", 500


def _transfer_markup(transfer_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"fin112:tconfirm:{transfer_id}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data=f"fin112:tcancel:{transfer_id}"),
    ]])


def _loan_markup(loan_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Принять заём", callback_data=f"fin112:laccept:{loan_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"fin112:lreject:{loan_id}"),
    ]])


def _finance_menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 Мои долги", callback_data="fin112:debts"),
            InlineKeyboardButton(text="🏦 Мне должны", callback_data="fin112:owed"),
        ],
        [
            InlineKeyboardButton(text="📊 Репутация", callback_data="fin112:credit"),
            InlineKeyboardButton(text="ℹ️ Правила", callback_data="fin112:rules"),
        ],
    ])


async def _target_player(core: Any, message: Message, token: str | None) -> Any | None:
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        if not target_user.is_bot:
            return await core.db.upsert_player(int(message.chat.id), target_user)
    query = str(token or "").strip()
    return await core.db.find_player(int(message.chat.id), query) if query else None


async def _player_name(core: Any, chat_id: int, user_id: int) -> str:
    player = await core.db.get_player(chat_id, user_id)
    return player.full_name if player else f"ID {user_id}"


async def _has_overdue(core: Any, chat_id: int, user_id: int) -> bool:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT 1 FROM finance_loans_v112 WHERE chat_id=? AND borrower_id=? AND status='overdue' LIMIT 1",
        (chat_id, user_id),
    )
    return await cursor.fetchone() is not None


async def _is_blocked(core: Any, chat_id: int, user_id: int) -> bool:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT transfers_blocked FROM finance_user_state_v112 WHERE chat_id=? AND user_id=?",
        (chat_id, user_id),
    )
    row = await cursor.fetchone()
    return bool(row and int(row["transfers_blocked"]))


async def _mark_overdue(core: Any, *, chat_id: int | None = None, user_id: int | None = None) -> list[Any]:
    conn = core.db._require_connection()
    now = _now()
    where = ["status='active'", "due_at IS NOT NULL", "due_at<=?"]
    args: list[Any] = [now]
    if chat_id is not None:
        where.append("chat_id=?")
        args.append(int(chat_id))
    if user_id is not None:
        where.append("borrower_id=?")
        args.append(int(user_id))
    async with core.db.lock:
        cursor = await conn.execute(
            f"SELECT * FROM finance_loans_v112 WHERE {' AND '.join(where)} ORDER BY due_at ASC",
            tuple(args),
        )
        rows = list(await cursor.fetchall())
        for row in rows:
            fee = 0 if int(row["late_fee_applied"]) else max(1, math.ceil(int(row["principal"]) * LATE_FEE_RATE))
            await conn.execute(
                """
                UPDATE finance_loans_v112
                SET status='overdue',total_due=total_due+?,late_fee_applied=1,was_overdue=1
                WHERE loan_id=? AND status='active'
                """,
                (fee, str(row["loan_id"])),
            )
        await conn.commit()
    return rows


async def _notify_overdue(core: Any, bot: Any, row: Any) -> None:
    chat_id = int(row["chat_id"])
    borrower = html.escape(await _player_name(core, chat_id, int(row["borrower_id"])))
    lender = html.escape(await _player_name(core, chat_id, int(row["lender_id"])))
    fee = 0 if int(row["late_fee_applied"]) else max(1, math.ceil(int(row["principal"]) * LATE_FEE_RATE))
    try:
        await bot.send_message(
            chat_id,
            "⚠️ <b>ЗАЁМ ПРОСРОЧЕН</b>\n\n"
            f"Заёмщик: <b>{borrower}</b>\nКредитор: <b>{lender}</b>\n"
            f"Остаток со штрафом: <b>{_fmt(_remaining(row) + fee)}</b>\n"
            f"Разовый штраф: <b>+{_fmt(fee)}</b>\n\n"
            "Теперь 30% положительного заработка автоматически направляется кредитору. "
            "Новые займы и исходящие переводы заблокированы до погашения.",
        )
    except Exception:
        pass


async def _overdue_loop(core: Any, bot: Any) -> None:
    while True:
        try:
            rows = await _mark_overdue(core)
            for row in rows:
                await _notify_overdue(core, bot, row)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(OVERDUE_CHECK_INTERVAL)


async def _notice_after_delay(core: Any, bot: Any, chat_id: int, user_id: int) -> None:
    key = (chat_id, user_id)
    try:
        await asyncio.sleep(6)
        amount = _NOTICE_AMOUNTS.pop(key, 0)
        if amount > 0:
            name = html.escape(await _player_name(core, chat_id, user_id))
            await bot.send_message(
                chat_id,
                "💳 <b>АВТОПОГАШЕНИЕ ДОЛГА</b>\n\n"
                f"{name}: из последних начислений удержано <b>{_fmt(amount)}</b> влияния.\n"
                "Остаток можно посмотреть командой /debts.",
            )
    except Exception:
        pass
    finally:
        _NOTICE_TASKS.pop(key, None)


def _queue_notice(core: Any, bot: Any, chat_id: int, user_id: int, amount: int) -> None:
    key = (int(chat_id), int(user_id))
    _NOTICE_AMOUNTS[key] = _NOTICE_AMOUNTS.get(key, 0) + int(amount)
    task = _NOTICE_TASKS.get(key)
    if task is None or task.done():
        _NOTICE_TASKS[key] = core.spawn_background_task(_notice_after_delay(core, bot, *key))


def _eligible_earning(reason: str) -> bool:
    value = str(reason or "").casefold()
    return not any(word in value for word in PROTECTED_EARNING_WORDS)


async def _withhold_overdue(core: Any, chat_id: int, user_id: int, earned: int) -> int:
    if earned <= 0:
        return 0
    await _mark_overdue(core, chat_id=chat_id, user_id=user_id)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT * FROM finance_loans_v112
        WHERE chat_id=? AND borrower_id=? AND status='overdue'
        ORDER BY due_at ASC,created_at ASC
        """,
        (chat_id, user_id),
    )
    loans = list(await cursor.fetchall())
    total_remaining = sum(_remaining(row) for row in loans)
    if total_remaining <= 0:
        return 0
    requested = min(total_remaining, int(earned), max(1, math.floor(int(earned) * OVERDUE_WITHHOLD_RATE)))
    if requested <= 0:
        return 0
    now = _now()
    paid_total = 0
    async with core.db.lock:
        cursor = await conn.execute("SELECT points FROM players WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        borrower = await cursor.fetchone()
        budget = min(requested, max(0, int(borrower["points"])) if borrower else 0)
        for row in loans:
            if budget <= 0:
                break
            pay = min(_remaining(row), budget)
            if pay <= 0:
                continue
            loan_id = str(row["loan_id"])
            lender_id = int(row["lender_id"])
            new_repaid = int(row["repaid"]) + pay
            new_status = "repaid" if new_repaid >= int(row["total_due"]) else "overdue"
            await conn.execute("UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?", (pay, now, chat_id, user_id))
            await conn.execute("UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?", (pay, now, chat_id, lender_id))
            await conn.execute(
                "UPDATE finance_loans_v112 SET repaid=?,status=?,completed_at=CASE WHEN ?='repaid' THEN ? ELSE completed_at END WHERE loan_id=?",
                (new_repaid, new_status, new_status, now, loan_id),
            )
            await conn.execute(
                "INSERT INTO finance_payments_v112(loan_id,chat_id,payer_id,receiver_id,amount,payment_type,created_at) VALUES(?,?,?,?,?,'automatic',?)",
                (loan_id, chat_id, user_id, lender_id, pay, now),
            )
            await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)", (chat_id, user_id, -pay, "transfer_loan_default_payment_out_v112", now))
            await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)", (chat_id, lender_id, pay, "transfer_loan_default_payment_in_v112", now))
            paid_total += pay
            budget -= pay
        await conn.commit()
    return paid_total


async def _credit_stats(core: Any, chat_id: int, user_id: int) -> dict[str, int]:
    await _mark_overdue(core, chat_id=chat_id, user_id=user_id)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT
          SUM(CASE WHEN borrower_id=? AND status='repaid' AND was_overdue=0 THEN 1 ELSE 0 END) on_time,
          SUM(CASE WHEN borrower_id=? AND was_overdue=1 THEN 1 ELSE 0 END) overdue_history,
          SUM(CASE WHEN borrower_id=? AND status='active' THEN 1 ELSE 0 END) active,
          SUM(CASE WHEN borrower_id=? AND status='overdue' THEN 1 ELSE 0 END) overdue,
          SUM(CASE WHEN lender_id=? AND status IN ('active','overdue') THEN 1 ELSE 0 END) issued
        FROM finance_loans_v112 WHERE chat_id=?
        """,
        (user_id, user_id, user_id, user_id, user_id, chat_id),
    )
    row = await cursor.fetchone()
    return {key: _safe_int(row[key] if row else 0) for key in ("on_time", "overdue_history", "active", "overdue", "issued")}


def _credit_text(stats: dict[str, int]) -> tuple[int, str, str]:
    total = stats["on_time"] + stats["overdue_history"]
    reliability = 100 if total <= 0 else max(0, min(100, round(stats["on_time"] / total * 100)))
    if stats["overdue"] > 0 or reliability < 40:
        return reliability, "🔴 Должник реальности", "Высокий риск"
    if reliability < 65:
        return reliability, "🟠 Рискованный", "Есть серьёзные просрочки"
    if reliability < 85:
        return reliability, "🟡 Нестабильный", "Иногда нарушает сроки"
    return reliability, "🟢 Надёжный", "Хорошая кредитная история"


async def _debts_text(core: Any, chat_id: int, user_id: int, *, as_lender: bool = False) -> str:
    await _mark_overdue(core, chat_id=chat_id)
    conn = core.db._require_connection()
    field = "lender_id" if as_lender else "borrower_id"
    cursor = await conn.execute(
        f"""
        SELECT l.*,COALESCE(b.full_name,'Участник') borrower_name,COALESCE(c.full_name,'Участник') lender_name
        FROM finance_loans_v112 l
        LEFT JOIN players b ON b.chat_id=l.chat_id AND b.user_id=l.borrower_id
        LEFT JOIN players c ON c.chat_id=l.chat_id AND c.user_id=l.lender_id
        WHERE l.chat_id=? AND l.{field}=? AND l.status IN ('active','overdue')
        ORDER BY CASE l.status WHEN 'overdue' THEN 0 ELSE 1 END,l.due_at ASC
        """,
        (chat_id, user_id),
    )
    rows = list(await cursor.fetchall())
    title = "🏦 <b>МНЕ ДОЛЖНЫ</b>" if as_lender else "💳 <b>МОИ ДОЛГИ</b>"
    if not rows:
        return title + "\n\nАктивных договоров нет."
    lines = [title]
    now = _now()
    for row in rows[:10]:
        other = row["borrower_name"] if as_lender else row["lender_name"]
        if str(row["status"]) == "overdue":
            time_text = "🔴 ПРОСРОЧЕН"
        else:
            seconds = max(0, int(row["due_at"]) - now)
            time_text = f"🟢 {seconds // 86400} д. {(seconds % 86400) // 3600} ч."
        lines.append(
            f"\n<b>#{_loan_token(str(row['loan_id']))}</b> · {html.escape(str(other))}\n"
            f"Осталось: <b>{_fmt(_remaining(row))}</b> из {_fmt(int(row['total_due']))}\n"
            f"Статус: <b>{time_text}</b>"
        )
    if not as_lender:
        lines.append("\nПогашение: <code>/repay ID сумма</code> или <code>/repay ID all</code>.")
    return "\n".join(lines)


async def _find_loan(core: Any, chat_id: int, borrower_id: int, token: str) -> Any | None:
    conn = core.db._require_connection()
    clean = str(token or "").strip().lower().lstrip("#")
    cursor = await conn.execute(
        """
        SELECT * FROM finance_loans_v112
        WHERE chat_id=? AND borrower_id=? AND status IN ('active','overdue') AND lower(loan_id) LIKE ?
        ORDER BY created_at ASC LIMIT 2
        """,
        (chat_id, borrower_id, f"{clean}%"),
    )
    rows = list(await cursor.fetchall())
    return rows[0] if len(rows) == 1 else None


async def _perform_repayment(core: Any, chat_id: int, borrower_id: int, loan_id: str, requested: int | str) -> tuple[bool, str]:
    await _mark_overdue(core, chat_id=chat_id, user_id=borrower_id)
    conn = core.db._require_connection()
    now = _now()
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT * FROM finance_loans_v112 WHERE loan_id=? AND chat_id=? AND borrower_id=? AND status IN ('active','overdue')",
            (loan_id, chat_id, borrower_id),
        )
        loan = await cursor.fetchone()
        if loan is None:
            return False, "Договор не найден или уже закрыт."
        remaining = _remaining(loan)
        amount = remaining if isinstance(requested, str) and requested.casefold() in {"all", "всё", "все"} else _safe_int(requested)
        if amount <= 0:
            return False, "Сумма погашения должна быть положительной."
        amount = min(amount, remaining)
        cursor = await conn.execute("SELECT points FROM players WHERE chat_id=? AND user_id=?", (chat_id, borrower_id))
        player = await cursor.fetchone()
        balance = int(player["points"]) if player else 0
        if balance < amount:
            return False, f"Недостаточно влияния. Баланс: {_fmt(balance)}."
        lender_id = int(loan["lender_id"])
        new_repaid = int(loan["repaid"]) + amount
        status = "repaid" if new_repaid >= int(loan["total_due"]) else str(loan["status"])
        await conn.execute("UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?", (amount, now, chat_id, borrower_id))
        await conn.execute("UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?", (amount, now, chat_id, lender_id))
        await conn.execute(
            "UPDATE finance_loans_v112 SET repaid=?,status=?,completed_at=CASE WHEN ?='repaid' THEN ? ELSE completed_at END WHERE loan_id=?",
            (new_repaid, status, status, now, loan_id),
        )
        await conn.execute("INSERT INTO finance_payments_v112(loan_id,chat_id,payer_id,receiver_id,amount,payment_type,created_at) VALUES(?,?,?,?,?,'manual',?)", (loan_id, chat_id, borrower_id, lender_id, amount, now))
        await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)", (chat_id, borrower_id, -amount, "transfer_loan_repayment_out_v112", now))
        await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)", (chat_id, lender_id, amount, "transfer_loan_repayment_in_v112", now))
        await conn.commit()
    lender_name = html.escape(await _player_name(core, chat_id, lender_id))
    left = max(0, remaining - amount)
    if left <= 0:
        return True, f"✅ <b>ДОГОВОР ЗАКРЫТ</b>\n\nПереведено кредитору {lender_name}: <b>{_fmt(amount)}</b>.\nДолг полностью погашен."
    return True, f"💳 <b>ЧАСТИЧНОЕ ПОГАШЕНИЕ</b>\n\nПереведено кредитору {lender_name}: <b>{_fmt(amount)}</b>.\nОсталось вернуть: <b>{_fmt(left)}</b>."


def install_finance_system_v112(core: Any) -> None:
    global _OVERDUE_LOOP_STARTED
    if getattr(core, "_finance_system_v112_installed", False):
        return
    core._finance_system_v112_installed = True
    core.FINANCE_SYSTEM_VERSION = VERSION
    original_connect = core.Database.connect

    async def connect_with_finance(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS finance_transfers_v112(
                    transfer_id TEXT PRIMARY KEY,chat_id INTEGER NOT NULL,sender_id INTEGER NOT NULL,
                    recipient_id INTEGER NOT NULL,amount INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'pending',
                    created_at INTEGER NOT NULL,expires_at INTEGER NOT NULL,completed_at INTEGER,cancelled_at INTEGER);
                CREATE INDEX IF NOT EXISTS idx_finance_transfers_sender ON finance_transfers_v112(chat_id,sender_id,status,created_at);
                CREATE TABLE IF NOT EXISTS finance_loans_v112(
                    loan_id TEXT PRIMARY KEY,chat_id INTEGER NOT NULL,lender_id INTEGER NOT NULL,borrower_id INTEGER NOT NULL,
                    principal INTEGER NOT NULL,interest_percent INTEGER NOT NULL,term_days INTEGER NOT NULL,total_due INTEGER NOT NULL,
                    repaid INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'offered',created_at INTEGER NOT NULL,
                    offer_expires_at INTEGER NOT NULL,accepted_at INTEGER,due_at INTEGER,completed_at INTEGER,
                    late_fee_applied INTEGER NOT NULL DEFAULT 0,was_overdue INTEGER NOT NULL DEFAULT 0);
                CREATE INDEX IF NOT EXISTS idx_finance_loans_borrower ON finance_loans_v112(chat_id,borrower_id,status,due_at);
                CREATE INDEX IF NOT EXISTS idx_finance_loans_lender ON finance_loans_v112(chat_id,lender_id,status,due_at);
                CREATE TABLE IF NOT EXISTS finance_payments_v112(
                    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,loan_id TEXT NOT NULL,chat_id INTEGER NOT NULL,
                    payer_id INTEGER NOT NULL,receiver_id INTEGER NOT NULL,amount INTEGER NOT NULL,payment_type TEXT NOT NULL,created_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS finance_user_state_v112(
                    chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,last_transfer_at INTEGER NOT NULL DEFAULT 0,
                    transfers_blocked INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(chat_id,user_id));
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_finance
    original_balance = core.Database.add_points_with_balance

    async def add_points_with_debt_collection(self: Any, chat_id: int, user_id: int, delta: int, reason: str, *args: Any, **kwargs: Any):
        result = await original_balance(self, chat_id, user_id, delta, reason, *args, **kwargs)
        try:
            before, after = result
            actual = int(after.points) - _before_points(before)
        except Exception:
            return result
        if int(chat_id) < 0 and actual > 0 and _eligible_earning(reason):
            withheld = await _withhold_overdue(core, int(chat_id), int(user_id), actual)
            if withheld > 0:
                bot = _RUNTIME_BOT["bot"]
                if bot is not None:
                    _queue_notice(core, bot, int(chat_id), int(user_id), withheld)
                fresh = await self.get_player(int(chat_id), int(user_id))
                if fresh is not None:
                    return before, fresh
        return result

    core.Database.add_points_with_balance = add_points_with_debt_collection

    @core.router.message(Command("finance", "money", "bank"))
    async def cmd_finance_v112(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        await core.db.upsert_player(int(message.chat.id), message.from_user)
        await message.answer(
            "💸 <b>ПЕРЕВОДЫ И ДОЛГИ</b>\n\n"
            "🎁 <code>/transfer @user 500</code> — передать влияние.\n"
            "🤝 <code>/loan @user 1000 10 3</code> — 1000 под 10% на 3 дня.\n"
            "💳 <code>/repay</code> — погасить долг.\n"
            "📜 <code>/debts</code> — договоры и остатки.\n"
            "📊 <code>/credit</code> — кредитная репутация.\n\n"
            "Переводы и займы не дают карьерное влияние и очки Древа.",
            reply_markup=_finance_menu_markup(),
        )

    @core.router.message(Command("transfer", "pay", "send"))
    async def cmd_transfer_v112(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        chat_id = int(message.chat.id)
        sender = await core.db.upsert_player(chat_id, message.from_user)
        parts = (message.text or "").split()
        if message.reply_to_message:
            amount_token, target_token = (parts[1] if len(parts) >= 2 else ""), None
        else:
            target_token = parts[1] if len(parts) >= 2 else None
            amount_token = parts[2] if len(parts) >= 3 else ""
        recipient = await _target_player(core, message, target_token)
        amount = _safe_int(amount_token)
        if recipient is None or amount <= 0:
            await message.answer("Использование: <code>/transfer @username 500</code> или ответом: <code>/transfer 500</code>.")
            return
        if int(recipient.user_id) == int(sender.user_id):
            await message.answer("Нельзя переводить влияние самому себе.")
            return
        if amount < TRANSFER_MIN or amount > TRANSFER_MAX:
            await message.answer(f"Сумма одного перевода: от <b>{TRANSFER_MIN}</b> до <b>{_fmt(TRANSFER_MAX)}</b>.")
            return
        await _mark_overdue(core, chat_id=chat_id, user_id=int(sender.user_id))
        if await _has_overdue(core, chat_id, int(sender.user_id)):
            await message.answer("🔴 Сначала погаси просроченный долг. Исходящие переводы заблокированы.")
            return
        if await _is_blocked(core, chat_id, int(sender.user_id)):
            await message.answer("🚫 Администратор заблокировал тебе исходящие переводы.")
            return
        conn = core.db._require_connection()
        cursor = await conn.execute("SELECT COALESCE(SUM(amount),0) total FROM finance_transfers_v112 WHERE chat_id=? AND sender_id=? AND status='completed' AND completed_at>=?", (chat_id, sender.user_id, _day_start()))
        used = _safe_int((await cursor.fetchone())["total"])
        if used + amount > TRANSFER_DAILY_LIMIT:
            await message.answer(f"Дневной лимит — <b>{_fmt(TRANSFER_DAILY_LIMIT)}</b>. Сегодня уже отправлено <b>{_fmt(used)}</b>.")
            return
        cursor = await conn.execute("SELECT last_transfer_at FROM finance_user_state_v112 WHERE chat_id=? AND user_id=?", (chat_id, sender.user_id))
        state = await cursor.fetchone()
        wait = TRANSFER_COOLDOWN - (_now() - _safe_int(state["last_transfer_at"] if state else 0))
        if wait > 0:
            await message.answer(f"Следующий перевод можно подтвердить через <b>{wait} сек.</b>")
            return
        if int(sender.points) < amount:
            await message.answer(f"Недостаточно влияния. Твой баланс: <b>{_fmt(sender.points)}</b>.")
            return
        transfer_id = secrets.token_urlsafe(9)
        now = _now()
        async with core.db.lock:
            await conn.execute("INSERT INTO finance_transfers_v112(transfer_id,chat_id,sender_id,recipient_id,amount,status,created_at,expires_at) VALUES(?,?,?,?,?,'pending',?,?)", (transfer_id, chat_id, sender.user_id, recipient.user_id, amount, now, now + TRANSFER_REQUEST_TTL))
            await conn.commit()
        await message.answer(
            "💸 <b>ПЕРЕВОД ВЛИЯНИЯ</b>\n\n"
            f"Отправитель: {core.player_link(sender)}\nПолучатель: {core.player_link(recipient)}\n"
            f"Сумма: <b>{_fmt(amount)}</b>\n\nПосле перевода останется <b>{_fmt(sender.points - amount)}</b>.\n"
            "Перевод не считается заработком и не прокачивает Древо.",
            reply_markup=_transfer_markup(transfer_id),
        )

    @core.router.callback_query(F.data.startswith("fin112:tconfirm:"))
    async def confirm_transfer_v112(callback: CallbackQuery) -> None:
        if not callback.from_user:
            return
        transfer_id = str(callback.data or "").split(":", 2)[-1]
        conn = core.db._require_connection()
        now = _now()
        async with core.db.lock:
            cursor = await conn.execute("SELECT * FROM finance_transfers_v112 WHERE transfer_id=?", (transfer_id,))
            row = await cursor.fetchone()
            if row is None or str(row["status"]) != "pending":
                await callback.answer("Перевод уже обработан.", show_alert=True); return
            if int(row["sender_id"]) != int(callback.from_user.id):
                await callback.answer("Подтвердить может только отправитель.", show_alert=True); return
            if int(row["expires_at"]) < now:
                await conn.execute("UPDATE finance_transfers_v112 SET status='expired',cancelled_at=? WHERE transfer_id=?", (now, transfer_id)); await conn.commit()
                await callback.answer("Время подтверждения истекло.", show_alert=True); return
            chat_id, sender_id, recipient_id, amount = int(row["chat_id"]), int(row["sender_id"]), int(row["recipient_id"]), int(row["amount"])
            cursor = await conn.execute("SELECT COALESCE(SUM(amount),0) total FROM finance_transfers_v112 WHERE chat_id=? AND sender_id=? AND status='completed' AND completed_at>=?", (chat_id, sender_id, _day_start()))
            used = _safe_int((await cursor.fetchone())["total"])
            cursor = await conn.execute("SELECT points FROM players WHERE chat_id=? AND user_id=?", (chat_id, sender_id)); sender_row = await cursor.fetchone()
            balance = _safe_int(sender_row["points"] if sender_row else 0)
            cursor = await conn.execute("SELECT transfers_blocked,last_transfer_at FROM finance_user_state_v112 WHERE chat_id=? AND user_id=?", (chat_id, sender_id)); state = await cursor.fetchone()
            cursor = await conn.execute("SELECT 1 FROM finance_loans_v112 WHERE chat_id=? AND borrower_id=? AND status='overdue' LIMIT 1", (chat_id, sender_id)); overdue = await cursor.fetchone() is not None
            blocked = bool(state and int(state["transfers_blocked"])); cooldown = TRANSFER_COOLDOWN - (now - _safe_int(state["last_transfer_at"] if state else 0))
            if blocked or overdue or cooldown > 0 or used + amount > TRANSFER_DAILY_LIMIT or balance < amount:
                await callback.answer("Перевод нельзя выполнить: проверь баланс, лимит или долги.", show_alert=True); return
            await conn.execute("UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?", (amount, now, chat_id, sender_id))
            await conn.execute("UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?", (amount, now, chat_id, recipient_id))
            await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)", (chat_id, sender_id, -amount, "transfer_sent_v112", now))
            await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)", (chat_id, recipient_id, amount, "transfer_received_v112", now))
            await conn.execute("UPDATE finance_transfers_v112 SET status='completed',completed_at=? WHERE transfer_id=?", (now, transfer_id))
            await conn.execute("INSERT INTO finance_user_state_v112(chat_id,user_id,last_transfer_at) VALUES(?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET last_transfer_at=excluded.last_transfer_at", (chat_id, sender_id, now))
            await conn.commit()
        sender_name = html.escape(await _player_name(core, chat_id, sender_id)); recipient_name = html.escape(await _player_name(core, chat_id, recipient_id))
        text = f"✅ <b>ПЕРЕВОД ВЫПОЛНЕН</b>\n\n{sender_name} передал {recipient_name} <b>{_fmt(amount)}</b> влияния.\nОперация не учитывается в карьерном прогрессе и событиях."
        if callback.message: await callback.message.edit_text(text)
        await callback.answer("Перевод выполнен!")

    @core.router.callback_query(F.data.startswith("fin112:tcancel:"))
    async def cancel_transfer_v112(callback: CallbackQuery) -> None:
        if not callback.from_user: return
        transfer_id = str(callback.data or "").split(":", 2)[-1]; conn = core.db._require_connection()
        async with core.db.lock:
            cursor = await conn.execute("SELECT sender_id,status FROM finance_transfers_v112 WHERE transfer_id=?", (transfer_id,)); row = await cursor.fetchone()
            if row is None or str(row["status"]) != "pending": await callback.answer("Запрос уже обработан.", show_alert=True); return
            if int(row["sender_id"]) != int(callback.from_user.id): await callback.answer("Отменить может только отправитель.", show_alert=True); return
            await conn.execute("UPDATE finance_transfers_v112 SET status='cancelled',cancelled_at=? WHERE transfer_id=?", (_now(), transfer_id)); await conn.commit()
        if callback.message: await callback.message.edit_text("❌ Перевод отменён.")
        await callback.answer()

    @core.router.message(Command("loan", "lend"))
    async def cmd_loan_v112(message: Message) -> None:
        if not message.from_user or not core.is_group(message): return
        chat_id = int(message.chat.id); lender = await core.db.upsert_player(chat_id, message.from_user); parts = (message.text or "").split()
        if message.reply_to_message: target_token, values = None, parts[1:]
        else: target_token, values = (parts[1] if len(parts) > 1 else None), parts[2:]
        borrower = await _target_player(core, message, target_token)
        if borrower is None or len(values) < 3:
            await message.answer("Использование: <code>/loan @username 1000 10 3</code> или ответом: <code>/loan 1000 10 3</code>."); return
        amount, percent, days = _safe_int(values[0]), _safe_int(values[1], -1), _safe_int(str(values[2]).lower().rstrip("dд"), -1)
        if int(borrower.user_id) == int(lender.user_id): await message.answer("Нельзя выдать заём самому себе."); return
        if amount < LOAN_MIN or amount > LOAN_MAX: await message.answer(f"Сумма займа: от <b>{LOAN_MIN}</b> до <b>{_fmt(LOAN_MAX)}</b>."); return
        if percent < 0 or percent > LOAN_INTEREST_MAX: await message.answer(f"Процент должен быть от 0 до {LOAN_INTEREST_MAX}%."); return
        if days < LOAN_TERM_MIN_DAYS or days > LOAN_TERM_MAX_DAYS: await message.answer(f"Срок: от {LOAN_TERM_MIN_DAYS} до {LOAN_TERM_MAX_DAYS} дней."); return
        await _mark_overdue(core, chat_id=chat_id, user_id=int(lender.user_id)); await _mark_overdue(core, chat_id=chat_id, user_id=int(borrower.user_id))
        if await _has_overdue(core, chat_id, int(lender.user_id)): await message.answer("С просроченным долгом нельзя выдавать новые займы."); return
        if await _has_overdue(core, chat_id, int(borrower.user_id)): await message.answer("У выбранного участника есть просроченный долг."); return
        if await _is_blocked(core, chat_id, int(lender.user_id)): await message.answer("Администратор заблокировал тебе финансовые операции."); return
        if int(lender.points) < amount: await message.answer(f"Недостаточно влияния. Баланс: <b>{_fmt(lender.points)}</b>."); return
        role_name, limit = _role_limit(core, int(borrower.points)); conn = core.db._require_connection()
        cursor = await conn.execute("SELECT COALESCE(SUM(total_due-repaid),0) total FROM finance_loans_v112 WHERE chat_id=? AND borrower_id=? AND status IN ('active','overdue','offered')", (chat_id, borrower.user_id)); outstanding = _safe_int((await cursor.fetchone())["total"])
        total_due = math.ceil(amount * (100 + percent) / 100)
        if outstanding + total_due > limit:
            await message.answer(f"Лимит займа для роли <b>{role_name}</b> — <b>{_fmt(limit)}</b>. Уже занято или предложено: <b>{_fmt(outstanding)}</b>."); return
        loan_id = secrets.token_urlsafe(9); now = _now()
        async with core.db.lock:
            await conn.execute("INSERT INTO finance_loans_v112(loan_id,chat_id,lender_id,borrower_id,principal,interest_percent,term_days,total_due,status,created_at,offer_expires_at) VALUES(?,?,?,?,?,?,?,?,'offered',?,?)", (loan_id, chat_id, lender.user_id, borrower.user_id, amount, percent, days, total_due, now, now + LOAN_OFFER_TTL)); await conn.commit()
        reliability, label, _ = _credit_text(await _credit_stats(core, chat_id, int(borrower.user_id)))
        await message.answer(
            "🤝 <b>ДОГОВОР ВЛИЯНИЯ</b>\n\n"
            f"Кредитор: {core.player_link(lender)}\nЗаёмщик: {core.player_link(borrower)}\n"
            f"Сумма: <b>{_fmt(amount)}</b>\nПроцент: <b>{percent}%</b>\nВернуть: <b>{_fmt(total_due)}</b>\n"
            f"Срок: <b>{days} дн.</b>\nРепутация: <b>{label} · {reliability}%</b>\n\nПосле принятия отменить договор нельзя.",
            reply_markup=_loan_markup(loan_id),
        )

    @core.router.callback_query(F.data.startswith("fin112:laccept:"))
    async def accept_loan_v112(callback: CallbackQuery) -> None:
        if not callback.from_user: return
        loan_id = str(callback.data or "").split(":", 2)[-1]; conn = core.db._require_connection(); now = _now()
        async with core.db.lock:
            cursor = await conn.execute("SELECT * FROM finance_loans_v112 WHERE loan_id=?", (loan_id,)); loan = await cursor.fetchone()
            if loan is None or str(loan["status"]) != "offered": await callback.answer("Предложение уже обработано.", show_alert=True); return
            if int(loan["borrower_id"]) != int(callback.from_user.id): await callback.answer("Принять может только заёмщик.", show_alert=True); return
            if int(loan["offer_expires_at"]) < now:
                await conn.execute("UPDATE finance_loans_v112 SET status='expired',completed_at=? WHERE loan_id=?", (now, loan_id)); await conn.commit(); await callback.answer("Срок предложения истёк.", show_alert=True); return
            chat_id, lender_id, borrower_id, principal = int(loan["chat_id"]), int(loan["lender_id"]), int(loan["borrower_id"]), int(loan["principal"])
            cursor = await conn.execute("SELECT points FROM players WHERE chat_id=? AND user_id=?", (chat_id, lender_id)); lender_row = await cursor.fetchone()
            if lender_row is None or int(lender_row["points"]) < principal: await callback.answer("У кредитора уже недостаточно влияния.", show_alert=True); return
            cursor = await conn.execute("SELECT points FROM players WHERE chat_id=? AND user_id=?", (chat_id, borrower_id)); borrower_row = await cursor.fetchone(); role_name, limit = _role_limit(core, int(borrower_row["points"]) if borrower_row else 0)
            cursor = await conn.execute("SELECT COALESCE(SUM(total_due-repaid),0) total FROM finance_loans_v112 WHERE chat_id=? AND borrower_id=? AND status IN ('active','overdue')", (chat_id, borrower_id)); existing = _safe_int((await cursor.fetchone())["total"])
            cursor = await conn.execute("SELECT 1 FROM finance_loans_v112 WHERE chat_id=? AND borrower_id=? AND status='overdue' LIMIT 1", (chat_id, borrower_id)); overdue = await cursor.fetchone() is not None
            if overdue or existing + int(loan["total_due"]) > limit: await callback.answer(f"Заём больше нельзя принять. Лимит роли {role_name}: {_fmt(limit)}.", show_alert=True); return
            await conn.execute("UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?", (principal, now, chat_id, lender_id)); await conn.execute("UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?", (principal, now, chat_id, borrower_id))
            await conn.execute("UPDATE finance_loans_v112 SET status='active',accepted_at=?,due_at=? WHERE loan_id=?", (now, now + int(loan["term_days"]) * 86400, loan_id))
            await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)", (chat_id, lender_id, -principal, "transfer_loan_issued_v112", now)); await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)", (chat_id, borrower_id, principal, "transfer_loan_received_v112", now)); await conn.commit()
        lender_name = html.escape(await _player_name(core, chat_id, lender_id)); borrower_name = html.escape(await _player_name(core, chat_id, borrower_id))
        text = f"✅ <b>ЗАЁМ ПРИНЯТ</b>\n\n{lender_name} передал {borrower_name} <b>{_fmt(principal)}</b>.\nВернуть <b>{_fmt(int(loan['total_due']))}</b> за <b>{int(loan['term_days'])} дн.</b>\n\nДоговор: <code>#{_loan_token(loan_id)}</code>"
        if callback.message: await callback.message.edit_text(text)
        await callback.answer("Заём принят!")

    @core.router.callback_query(F.data.startswith("fin112:lreject:"))
    async def reject_loan_v112(callback: CallbackQuery) -> None:
        if not callback.from_user: return
        loan_id = str(callback.data or "").split(":", 2)[-1]; conn = core.db._require_connection()
        async with core.db.lock:
            cursor = await conn.execute("SELECT * FROM finance_loans_v112 WHERE loan_id=?", (loan_id,)); loan = await cursor.fetchone()
            if loan is None or str(loan["status"]) != "offered": await callback.answer("Предложение уже обработано.", show_alert=True); return
            if int(callback.from_user.id) not in {int(loan["borrower_id"]), int(loan["lender_id"])}: await callback.answer("Нет доступа к договору.", show_alert=True); return
            await conn.execute("UPDATE finance_loans_v112 SET status='rejected',completed_at=? WHERE loan_id=?", (_now(), loan_id)); await conn.commit()
        if callback.message: await callback.message.edit_text("❌ Предложение займа отклонено.")
        await callback.answer()

    @core.router.message(Command("repay"))
    async def cmd_repay_v112(message: Message) -> None:
        if not message.from_user or not core.is_group(message): return
        chat_id, user_id = int(message.chat.id), int(message.from_user.id); await core.db.upsert_player(chat_id, message.from_user); parts = (message.text or "").split()
        if len(parts) == 1: await message.answer(await _debts_text(core, chat_id, user_id)); return
        conn = core.db._require_connection()
        if len(parts) == 2:
            cursor = await conn.execute("SELECT * FROM finance_loans_v112 WHERE chat_id=? AND borrower_id=? AND status IN ('active','overdue') ORDER BY due_at ASC", (chat_id, user_id)); rows = list(await cursor.fetchall())
            if len(rows) != 1: await message.answer("Укажи договор: <code>/repay ID сумма</code>. Список: /debts."); return
            loan, amount_token = rows[0], parts[1]
        else:
            loan, amount_token = await _find_loan(core, chat_id, user_id, parts[1]), parts[2]
            if loan is None: await message.answer("Договор не найден или ID неоднозначен. Посмотри /debts."); return
        _, text = await _perform_repayment(core, chat_id, user_id, str(loan["loan_id"]), amount_token); await message.answer(text)

    @core.router.message(Command("debts", "loans"))
    async def cmd_debts_v112(message: Message) -> None:
        if not message.from_user or not core.is_group(message): return
        chat_id, user_id = int(message.chat.id), int(message.from_user.id); await core.db.upsert_player(chat_id, message.from_user)
        await message.answer((await _debts_text(core, chat_id, user_id)) + "\n\n" + (await _debts_text(core, chat_id, user_id, as_lender=True)))

    @core.router.message(Command("credit", "reputation"))
    async def cmd_credit_v112(message: Message) -> None:
        if not message.from_user or not core.is_group(message): return
        chat_id = int(message.chat.id); split = (message.text or "").split(maxsplit=1); target = await _target_player(core, message, split[1] if len(split) == 2 else None)
        if target is None: target = await core.db.upsert_player(chat_id, message.from_user)
        stats = await _credit_stats(core, chat_id, int(target.user_id)); reliability, label, note = _credit_text(stats)
        await message.answer(
            "📊 <b>КРЕДИТНАЯ РЕПУТАЦИЯ</b>\n\n"
            f"Участник: {core.player_link(target)}\nСтатус: <b>{label}</b>\nНадёжность: <b>{reliability}%</b>\n{html.escape(note)}\n\n"
            f"Погашено вовремя: <b>{stats['on_time']}</b>\nДоговоров с просрочкой: <b>{stats['overdue_history']}</b>\n"
            f"Активных долгов: <b>{stats['active']}</b>\nПросроченных сейчас: <b>{stats['overdue']}</b>\nВыданных займов: <b>{stats['issued']}</b>"
        )

    @core.router.callback_query(F.data.in_({"fin112:debts", "fin112:owed", "fin112:credit", "fin112:rules"}))
    async def finance_menu_callback_v112(callback: CallbackQuery) -> None:
        if not callback.from_user or not callback.message: return
        chat_id, user_id, action = int(callback.message.chat.id), int(callback.from_user.id), str(callback.data or "")
        if action == "fin112:debts": text = await _debts_text(core, chat_id, user_id)
        elif action == "fin112:owed": text = await _debts_text(core, chat_id, user_id, as_lender=True)
        elif action == "fin112:credit":
            stats = await _credit_stats(core, chat_id, user_id); reliability, label, note = _credit_text(stats)
            text = f"📊 <b>КРЕДИТНАЯ РЕПУТАЦИЯ</b>\n\nСтатус: <b>{label}</b>\nНадёжность: <b>{reliability}%</b>\n{html.escape(note)}\n\nПогашено вовремя: <b>{stats['on_time']}</b>\nПросрочек: <b>{stats['overdue_history']}</b>"
        else:
            text = f"ℹ️ <b>ПРАВИЛА ФИНАНСОВ</b>\n\nПеревод: {TRANSFER_MIN}–{_fmt(TRANSFER_MAX)}, дневной лимит {_fmt(TRANSFER_DAILY_LIMIT)}.\nЗаймы: {LOAN_MIN}–{_fmt(LOAN_MAX)}, 0–{LOAN_INTEREST_MAX}%, {LOAN_TERM_MIN_DAYS}–{LOAN_TERM_MAX_DAYS} дней.\nПри просрочке один раз добавляется 5%, затем удерживается 30% заработка.\nПереводы и займы не дают очки Древа и не считаются вкладом события."
        await callback.answer(); await callback.message.answer(text)

    @core.router.message(Command("loans_admin"))
    async def cmd_loans_admin_v112(message: Message) -> None:
        if not message.from_user or int(message.from_user.id) != int(core.DEVELOPER_ID) or not core.is_group(message): return
        chat_id = int(message.chat.id); await _mark_overdue(core, chat_id=chat_id); conn = core.db._require_connection()
        cursor = await conn.execute("""
            SELECT l.*,COALESCE(b.full_name,'Участник') borrower_name,COALESCE(c.full_name,'Участник') lender_name
            FROM finance_loans_v112 l LEFT JOIN players b ON b.chat_id=l.chat_id AND b.user_id=l.borrower_id
            LEFT JOIN players c ON c.chat_id=l.chat_id AND c.user_id=l.lender_id
            WHERE l.chat_id=? AND l.status IN ('active','overdue') ORDER BY CASE l.status WHEN 'overdue' THEN 0 ELSE 1 END,l.due_at ASC LIMIT 20
        """, (chat_id,)); rows = list(await cursor.fetchall())
        if not rows: await message.answer("Активных займов в этой беседе нет."); return
        lines = ["🛠 <b>АДМИН · ЗАЙМЫ</b>"]
        for row in rows:
            lines.append(f"\n#{_loan_token(str(row['loan_id']))} · {html.escape(str(row['lender_name']))} → {html.escape(str(row['borrower_name']))}\nОстаток: <b>{_fmt(_remaining(row))}</b> · {'🔴 просрочен' if row['status']=='overdue' else '🟢 активен'}")
        lines.append("\n<code>/loan_forgive ID</code> — простить долг.\n<code>/finance_block @user</code> — блок/разблокировка переводов.")
        await message.answer("\n".join(lines))

    @core.router.message(Command("loan_forgive"))
    async def cmd_loan_forgive_v112(message: Message) -> None:
        if not message.from_user or int(message.from_user.id) != int(core.DEVELOPER_ID): return
        parts = (message.text or "").split()
        if len(parts) < 2: await message.answer("Использование: <code>/loan_forgive ID</code>"); return
        chat_id, token, conn = int(message.chat.id), parts[1].lower().lstrip("#"), core.db._require_connection()
        async with core.db.lock:
            cursor = await conn.execute("SELECT * FROM finance_loans_v112 WHERE chat_id=? AND lower(loan_id) LIKE ? AND status IN ('active','overdue') LIMIT 2", (chat_id, f"{token}%")); rows = list(await cursor.fetchall())
            if len(rows) != 1: await message.answer("Договор не найден или ID неоднозначен."); return
            row = rows[0]; await conn.execute("UPDATE finance_loans_v112 SET status='forgiven',completed_at=? WHERE loan_id=?", (_now(), str(row["loan_id"]))); await conn.commit()
        await message.answer(f"🕊 Долг <b>#{_loan_token(str(row['loan_id']))}</b> прощён. Списано: <b>{_fmt(_remaining(row))}</b>.")

    @core.router.message(Command("finance_block"))
    async def cmd_finance_block_v112(message: Message) -> None:
        if not message.from_user or int(message.from_user.id) != int(core.DEVELOPER_ID): return
        chat_id = int(message.chat.id); parts = (message.text or "").split(maxsplit=1); target = await _target_player(core, message, parts[1] if len(parts) == 2 else None)
        if target is None: await message.answer("Ответь на сообщение или укажи username."); return
        conn = core.db._require_connection()
        async with core.db.lock:
            cursor = await conn.execute("SELECT transfers_blocked FROM finance_user_state_v112 WHERE chat_id=? AND user_id=?", (chat_id, target.user_id)); row = await cursor.fetchone(); enabled = not bool(row and int(row["transfers_blocked"]))
            await conn.execute("INSERT INTO finance_user_state_v112(chat_id,user_id,transfers_blocked) VALUES(?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET transfers_blocked=excluded.transfers_blocked", (chat_id, target.user_id, 1 if enabled else 0)); await conn.commit()
        await message.answer(f"{'🚫' if enabled else '✅'} Финансовые переводы для {core.player_link(target)} {'заблокированы' if enabled else 'разблокированы'}.")

    def _admin_auth(request: web.Request) -> tuple[Any | None, web.Response | None]:
        user, reason = core._webapp_auth(request)
        if user is None: return None, core.web.json_response({"ok": False, "reason": reason or "Нет авторизации."}, status=401)
        if int(user.id) != int(core.DEVELOPER_ID): return None, core.web.json_response({"ok": False, "reason": "Доступ только владельцу."}, status=403)
        return user, None

    async def finance_admin_state(request: web.Request) -> web.Response:
        _, problem = _admin_auth(request)
        if problem is not None: return problem
        chat_id = _safe_int(request.query.get("chat_id"))
        if not chat_id: return core.web.json_response({"ok": False, "reason": "Не выбрана беседа."}, status=400)
        await _mark_overdue(core, chat_id=chat_id); conn = core.db._require_connection()
        cursor = await conn.execute("""
            SELECT l.*,COALESCE(b.full_name,'Участник') borrower_name,COALESCE(c.full_name,'Участник') lender_name
            FROM finance_loans_v112 l LEFT JOIN players b ON b.chat_id=l.chat_id AND b.user_id=l.borrower_id
            LEFT JOIN players c ON c.chat_id=l.chat_id AND c.user_id=l.lender_id
            WHERE l.chat_id=? AND l.status IN ('active','overdue') ORDER BY CASE l.status WHEN 'overdue' THEN 0 ELSE 1 END,l.due_at ASC LIMIT 50
        """, (chat_id,)); loans = [dict(row) for row in await cursor.fetchall()]
        cursor = await conn.execute("""
            SELECT t.*,COALESCE(s.full_name,'Участник') sender_name,COALESCE(r.full_name,'Участник') recipient_name
            FROM finance_transfers_v112 t LEFT JOIN players s ON s.chat_id=t.chat_id AND s.user_id=t.sender_id
            LEFT JOIN players r ON r.chat_id=t.chat_id AND r.user_id=t.recipient_id
            WHERE t.chat_id=? AND t.status='completed' ORDER BY t.completed_at DESC LIMIT 30
        """, (chat_id,)); transfers = [dict(row) for row in await cursor.fetchall()]
        return core.web.json_response({
            "ok": True,"version": VERSION,
            "summary": {"active": sum(row["status"] == "active" for row in loans),"overdue": sum(row["status"] == "overdue" for row in loans),"debt_total": sum(_remaining(row) for row in loans),"transfers_today": sum(int(row["amount"]) for row in transfers if _safe_int(row.get("completed_at")) >= _day_start())},
            "loans": [{**row,"remaining": _remaining(row),"token": _loan_token(str(row["loan_id"]))} for row in loans],"transfers": transfers,
        })

    async def finance_admin_action(request: web.Request) -> web.Response:
        _, problem = _admin_auth(request)
        if problem is not None: return problem
        try: data = await request.json()
        except Exception: data = {}
        action, chat_id, loan_id = str(data.get("action") or ""), _safe_int(data.get("chat_id")), str(data.get("loan_id") or "")
        if action == "forgive" and chat_id and loan_id:
            conn = core.db._require_connection()
            async with core.db.lock:
                await conn.execute("UPDATE finance_loans_v112 SET status='forgiven',completed_at=? WHERE chat_id=? AND loan_id=? AND status IN ('active','overdue')", (_now(), chat_id, loan_id)); await conn.commit()
            return core.web.json_response({"ok": True, "message": "Долг прощён."})
        return core.web.json_response({"ok": False, "reason": "Неизвестное действие."}, status=400)

    async def finance_admin_script(_: web.Request) -> web.StreamResponse:
        return core.web.FileResponse(ADMIN_SCRIPT, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "X-Admin-Center": VERSION})

    original_start_server = core.start_webapp_server
    async def start_server_with_finance(bot: Any):
        global _OVERDUE_LOOP_STARTED
        _RUNTIME_BOT["bot"] = bot; previous_application = core.web.Application
        def application_factory(*args: Any, **kwargs: Any):
            app = previous_application(*args, **kwargs); app.router.add_get("/admin-v112/finance-admin.js", finance_admin_script); app.router.add_get("/finance-v112/api/state", finance_admin_state); app.router.add_post("/finance-v112/api/action", finance_admin_action); return app
        core.web.Application = application_factory
        try: runner = await original_start_server(bot)
        finally: core.web.Application = previous_application
        if not _OVERDUE_LOOP_STARTED:
            _OVERDUE_LOOP_STARTED = True; core.spawn_background_task(_overdue_loop(core, bot))
        return runner
    core.start_webapp_server = start_server_with_finance

    original_group_commands = core.group_bot_commands
    def group_commands_with_finance() -> list[BotCommand]:
        commands = list(original_group_commands()); existing = {command.command for command in commands}
        additions = [
            BotCommand(command="finance", description="Переводы, займы и долги"),BotCommand(command="transfer", description="Передать влияние участнику"),
            BotCommand(command="loan", description="Предложить заём под процент"),BotCommand(command="repay", description="Погасить долг"),
            BotCommand(command="debts", description="Мои долги и выданные займы"),BotCommand(command="credit", description="Кредитная репутация"),
        ]
        return commands + [command for command in additions if command.command not in existing]
    core.group_bot_commands = group_commands_with_finance

    names = {"cmd_finance_v112","cmd_transfer_v112","cmd_loan_v112","cmd_repay_v112","cmd_debts_v112","cmd_credit_v112","cmd_loans_admin_v112","cmd_loan_forgive_v112","cmd_finance_block_v112"}
    handlers = core.router.message.handlers
    preferred = [handler for handler in handlers if getattr(handler.callback, "__name__", "") in names]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
