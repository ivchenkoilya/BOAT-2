from __future__ import annotations

import html
import math
import secrets
import time
from pathlib import Path
from typing import Any

import finance_investments_v127_core as invest_core
import finance_miniapp_v114 as finance_app
import finance_system_v112 as finance
import government_institutions_v128 as institutions
import government_v127 as gov


VERSION = "Reality 133 · Переводы до миллиона"
TRANSFER_LIMIT = 1_000_000
TRANSFER_DAILY_LIMIT = 1_000_000
INDEX_PATH = Path(invest_core.APP_DIR) / "index.html"


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _fmt(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


async def _payload(request: Any) -> dict[str, Any]:
    try:
        value = await request.json()
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


async def _transfer(core: Any, request: Any, data: dict[str, Any]) -> Any:
    user, start_param = core._webapp_auth(request)
    if user is None:
        return core.web.json_response(
            {"ok": False, "reason": start_param or "Нет авторизации Telegram."},
            status=401,
        )

    try:
        chat_id = finance_app._parse_chat_id(start_param, data, request)
        sender_id = int(user.id)
        recipient_id = _as_int(data.get("recipient_id"))
        amount = _as_int(data.get("amount"))
        if recipient_id == sender_id:
            raise ValueError("Нельзя переводить влияние самому себе.")
        if amount < finance.TRANSFER_MIN or amount > TRANSFER_LIMIT:
            raise ValueError(
                f"Сумма перевода должна быть от {finance.TRANSFER_MIN} до {_fmt(TRANSFER_LIMIT)}."
            )

        await finance._mark_overdue(core, chat_id=chat_id, user_id=sender_id)
        await gov._ensure_state(core, chat_id)
        policy = await institutions._policy(core, chat_id)
        fee = max(0, math.ceil(amount * int(policy.get("transfer_fee_bps", 0)) / 10_000))
        conn = core.db._require_connection()
        now = int(time.time())

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

            required = amount + fee
            if int(sender["points"]) < required:
                raise ValueError(
                    f"Недостаточно влияния. Нужно {_fmt(required)} с комиссией, "
                    f"баланс: {_fmt(int(sender['points']))}."
                )

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
            wait = finance.TRANSFER_COOLDOWN - (
                now - _as_int(state["last_transfer_at"] if state else 0)
            )
            if wait > 0:
                raise ValueError(f"Следующий перевод доступен через {wait} сек.")

            cursor = await conn.execute(
                "SELECT COALESCE(SUM(amount),0) total FROM finance_transfers_v112 "
                "WHERE chat_id=? AND sender_id=? AND status='completed' AND completed_at>=?",
                (chat_id, sender_id, finance._day_start()),
            )
            used = _as_int((await cursor.fetchone())["total"])
            if used + amount > TRANSFER_DAILY_LIMIT:
                raise ValueError(
                    f"Дневной лимит {_fmt(TRANSFER_DAILY_LIMIT)}. "
                    f"Сегодня уже отправлено {_fmt(used)}."
                )

            transfer_id = secrets.token_urlsafe(9)
            await conn.execute(
                "UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?",
                (required, now, chat_id, sender_id),
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
                (chat_id, sender_id, -amount, "transfer_sent_v133", now),
            )
            await conn.execute(
                "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                (chat_id, recipient_id, amount, "transfer_received_v133", now),
            )
            if fee:
                await conn.execute(
                    "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                    (chat_id, sender_id, -fee, "central_bank_transfer_fee_v133", now),
                )
                await conn.execute(
                    "UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?",
                    (fee, now, chat_id),
                )
            await conn.execute(
                """
                INSERT INTO finance_user_state_v112(chat_id,user_id,last_transfer_at)
                VALUES(?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET
                last_transfer_at=excluded.last_transfer_at
                """,
                (chat_id, sender_id, now),
            )
            await conn.commit()

            sender_name = html.escape(str(sender["full_name"] or f"ID {sender_id}"))
            recipient_name = html.escape(str(recipient["full_name"] or f"ID {recipient_id}"))
            new_balance = int(sender["points"]) - required

        if fee:
            await gov._treasury_log(
                core,
                chat_id,
                fee,
                "Комиссия Центрального банка",
                "transfer_fee_v133",
                transfer_id,
                sender_id,
            )

        bot = request.app.get("bot") or finance._RUNTIME_BOT.get("bot")
        if bot is not None:
            try:
                fee_line = f"\nКомиссия ЦБ: <b>{_fmt(fee)}</b>." if fee else ""
                await bot.send_message(
                    chat_id,
                    "💸 <b>ПЕРЕВОД ВЛИЯНИЯ</b>\n\n"
                    f'<a href="tg://user?id={sender_id}">{sender_name}</a> передал '
                    f'<a href="tg://user?id={recipient_id}">{recipient_name}</a> '
                    f"<b>{_fmt(amount)}</b> влияния.{fee_line}\n\n"
                    "Перевод не считается заработком и не даёт очки Древа.",
                )
            except Exception:
                pass

        return core.web.json_response(
            {
                "ok": True,
                "message": f"Переведено {_fmt(amount)} влияния.",
                "balance": new_balance,
                "fee": fee,
            }
        )
    except PermissionError as error:
        return core.web.json_response({"ok": False, "reason": str(error)}, status=403)
    except ValueError as error:
        return core.web.json_response({"ok": False, "reason": str(error)}, status=400)
    except Exception:
        core.logging.exception("Ошибка перевода Reality 133")
        return core.web.json_response(
            {"ok": False, "reason": "Перевод не выполнен. Попробуй ещё раз."},
            status=500,
        )


def _finance_index() -> str:
    source = INDEX_PATH.read_text(encoding="utf-8")
    source = source.replace("REALITY 128", "REALITY 133")
    source = source.replace(
        '<input id="transferAmount" type="number" min="10" max="5000" step="10" value="500" inputmode="numeric">',
        '<input id="transferAmount" type="number" min="10" max="1000000" step="100" value="1000" inputmode="numeric">',
    )
    source = source.replace(
        '<div class="chips" data-chip-target="transferAmount"><button data-value="100" type="button">100</button><button class="active" data-value="500" type="button">500</button><button data-value="1000" type="button">1000</button><button data-value="5000" type="button">5000</button></div>',
        '<div class="chips" data-chip-target="transferAmount"><button data-value="10000" type="button">10 000</button><button class="active" data-value="100000" type="button">100 000</button><button data-value="500000" type="button">500 000</button><button data-value="1000000" type="button">1 000 000</button></div>',
    )
    source = source.replace(
        '<b id="transferPreviewAmount">500</b>',
        '<b id="transferPreviewAmount">1 000</b>',
    )
    return source


def install_finance_transfer_limit_v133(core: Any) -> None:
    if getattr(core, "_finance_transfer_limit_v133_installed", False):
        return
    core._finance_transfer_limit_v133_installed = True
    core.FINANCE_SYSTEM_VERSION = VERSION
    finance.TRANSFER_MAX = TRANSFER_LIMIT
    finance.TRANSFER_DAILY_LIMIT = TRANSFER_DAILY_LIMIT

    @core.web.middleware
    async def transfer_limit_middleware(request: Any, handler: Any):
        path = str(request.path or "")
        if request.method.upper() == "GET" and path in {
            "/finance-v127",
            "/finance-v127/",
            "/finance-v127/index.html",
        }:
            return core.web.Response(
                text=_finance_index(),
                content_type="text/html",
                charset="utf-8",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Finance-Center": "reality-133",
                },
            )

        if request.method.upper() == "POST" and path in {
            "/finance-v114/api/action",
            "/finance/api/action",
        }:
            data = await _payload(request)
            if str(data.get("action") or "") == "transfer":
                return await _transfer(core, request, data)

        return await handler(request)

    previous_application = core.web.Application

    def application_with_transfer_limit(*args: Any, **kwargs: Any):
        application = previous_application(*args, **kwargs)
        application.middlewares.insert(0, transfer_limit_middleware)
        return application

    core.web.Application = application_with_transfer_limit
