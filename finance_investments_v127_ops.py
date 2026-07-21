from __future__ import annotations

import math
import secrets
from typing import Any

import finance_system_v112 as finance

from finance_investments_v127_core import (
    DEPOSIT_PLANS, MARKET_TICK_SECONDS, MAX_ACTIVE_DEPOSITS, MAX_DEPOSIT_TOTAL,
    MAX_TRADE_VALUE, STOCKS, TRADE_FEE_PERCENT, _deposit_values, _fmt, _now, _safe_int,
)
from finance_investments_v127_market import _advance_market


async def _create_deposit(core: Any, chat_id: int, user_id: int, data: dict[str, Any]) -> str:
    plan_key = str(data.get("plan_key") or "")
    amount = _safe_int(data.get("amount"))
    if plan_key not in DEPOSIT_PLANS:
        raise ValueError("Выбери доступный вклад.")
    if amount < 100:
        raise ValueError("Минимальная сумма вклада — 100 влияния.")
    if amount > MAX_DEPOSIT_TOTAL:
        raise ValueError(f"Максимальная сумма вклада — {_fmt(MAX_DEPOSIT_TOTAL)}.")
    if await finance._has_overdue(core, chat_id, user_id):
        raise ValueError("Сначала погаси просроченный долг.")
    if await finance._is_blocked(core, chat_id, user_id):
        raise ValueError("Тебе заблокированы финансовые операции.")
    conn = core.db._require_connection()
    now = _now()
    plan = DEPOSIT_PLANS[plan_key]
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT points FROM players WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        player = await cursor.fetchone()
        if player is None or int(player["points"]) < amount:
            balance = int(player["points"]) if player else 0
            raise ValueError(f"Недостаточно влияния. Баланс: {_fmt(balance)}.")
        cursor = await conn.execute(
            "SELECT COUNT(*) count,COALESCE(SUM(principal),0) total FROM finance_deposits_v127 WHERE chat_id=? AND user_id=? AND status='active'",
            (chat_id, user_id),
        )
        active = await cursor.fetchone()
        if int(active["count"]) >= MAX_ACTIVE_DEPOSITS:
            raise ValueError(f"Одновременно можно держать не больше {MAX_ACTIVE_DEPOSITS} вкладов.")
        if int(active["total"]) + amount > MAX_DEPOSIT_TOTAL:
            raise ValueError(
                f"Общая сумма активных вкладов не может превышать {_fmt(MAX_DEPOSIT_TOTAL)}."
            )
        deposit_id = secrets.token_urlsafe(9)
        matures_at = now + int(plan["term_days"]) * 86400
        await conn.execute(
            "UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?",
            (amount, now, chat_id, user_id),
        )
        await conn.execute(
            """
            INSERT INTO finance_deposits_v127(
                deposit_id,chat_id,user_id,plan_key,principal,started_at,matures_at,status
            ) VALUES(?,?,?,?,?,?,?,'active')
            """,
            (deposit_id, chat_id, user_id, plan_key, amount, now, matures_at),
        )
        await conn.execute(
            "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
            (chat_id, user_id, -amount, "investment_deposit_open_v127", now),
        )
        await conn.commit()
    return f"Открыт вклад «{plan['title']}» на {_fmt(amount)} влияния."


async def _withdraw_deposit(core: Any, chat_id: int, user_id: int, data: dict[str, Any]) -> str:
    deposit_id = str(data.get("deposit_id") or "")
    conn = core.db._require_connection()
    now = _now()
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT * FROM finance_deposits_v127 WHERE deposit_id=? AND chat_id=? AND user_id=?",
            (deposit_id, chat_id, user_id),
        )
        row = await cursor.fetchone()
        if row is None or str(row["status"]) != "active":
            raise ValueError("Вклад уже закрыт или не найден.")
        plan_key = str(row["plan_key"])
        plan = DEPOSIT_PLANS[plan_key]
        principal = int(row["principal"])
        payout, _, matured, can_withdraw = _deposit_values(row, now)
        if not can_withdraw:
            seconds = max(0, int(row["matures_at"]) - now)
            raise ValueError(f"Этот вклад нельзя снять досрочно. Осталось {math.ceil(seconds / 86400)} дн.")
        if not matured:
            if str(plan["early"]) == "interest_lost":
                payout = principal
            elif str(plan["early"]) == "penalty_3":
                payout = max(0, math.floor(principal * 0.97))
        await conn.execute(
            "UPDATE finance_deposits_v127 SET status='closed',payout=?,completed_at=? WHERE deposit_id=?",
            (payout, now, deposit_id),
        )
        await conn.execute(
            "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
            (payout, now, chat_id, user_id),
        )
        await conn.execute(
            "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
            (chat_id, user_id, payout, "investment_deposit_close_v127", now),
        )
        await conn.commit()
    result = payout - principal
    return f"Вклад закрыт. Получено {_fmt(payout)} влияния ({result:+d})."


async def _trade(core: Any, chat_id: int, user_id: int, data: dict[str, Any], side: str) -> str:
    symbol = str(data.get("symbol") or "").upper()
    quantity = _safe_int(data.get("quantity"))
    if symbol not in STOCKS:
        raise ValueError("Акция не найдена.")
    if quantity < 1 or quantity > 1000:
        raise ValueError("Количество акций должно быть от 1 до 1000.")
    if await finance._has_overdue(core, chat_id, user_id):
        raise ValueError("Сначала погаси просроченный долг.")
    if await finance._is_blocked(core, chat_id, user_id):
        raise ValueError("Тебе заблокированы финансовые операции.")
    await _advance_market(core, chat_id)
    conn = core.db._require_connection()
    now = _now()
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT price FROM finance_market_v127 WHERE chat_id=? AND symbol=?",
            (chat_id, symbol),
        )
        market = await cursor.fetchone()
        if market is None:
            raise ValueError("Курс временно недоступен.")
        price = int(market["price"])
        gross = price * quantity
        if gross > MAX_TRADE_VALUE:
            raise ValueError(f"Одна сделка не может превышать {_fmt(MAX_TRADE_VALUE)} влияния.")
        fee = max(1, math.ceil(gross * TRADE_FEE_PERCENT / 100))
        cursor = await conn.execute(
            "SELECT * FROM finance_stock_positions_v127 WHERE chat_id=? AND user_id=? AND symbol=?",
            (chat_id, user_id, symbol),
        )
        position = await cursor.fetchone()
        trade_id = secrets.token_urlsafe(9)
        if side == "buy":
            total = gross + fee
            cursor = await conn.execute(
                "SELECT points FROM players WHERE chat_id=? AND user_id=?",
                (chat_id, user_id),
            )
            player = await cursor.fetchone()
            balance = int(player["points"]) if player else 0
            if balance < total:
                raise ValueError(f"Нужно {_fmt(total)} влияния с комиссией. Баланс: {_fmt(balance)}.")
            await conn.execute(
                "UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?",
                (total, now, chat_id, user_id),
            )
            if position is None:
                await conn.execute(
                    """
                    INSERT INTO finance_stock_positions_v127(
                        chat_id,user_id,symbol,quantity,total_cost,realized_profit,updated_at
                    ) VALUES(?,?,?,?,?,0,?)
                    """,
                    (chat_id, user_id, symbol, quantity, total, now),
                )
            else:
                await conn.execute(
                    """
                    UPDATE finance_stock_positions_v127
                    SET quantity=quantity+?,total_cost=total_cost+?,updated_at=?
                    WHERE chat_id=? AND user_id=? AND symbol=?
                    """,
                    (quantity, total, now, chat_id, user_id, symbol),
                )
            delta = -total
            direction = 1
            message = f"Куплено {quantity} акц. {symbol} по {_fmt(price)}. Комиссия: {_fmt(fee)}."
        else:
            if position is None or int(position["quantity"]) < quantity:
                owned = int(position["quantity"]) if position else 0
                raise ValueError(f"Недостаточно акций. В портфеле: {owned}.")
            owned = int(position["quantity"])
            total_cost = int(position["total_cost"])
            cost_basis = round(total_cost * quantity / owned)
            net = max(0, gross - fee)
            realized = net - cost_basis
            remaining_quantity = owned - quantity
            remaining_cost = max(0, total_cost - cost_basis)
            await conn.execute(
                "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                (net, now, chat_id, user_id),
            )
            if remaining_quantity == 0:
                await conn.execute(
                    "DELETE FROM finance_stock_positions_v127 WHERE chat_id=? AND user_id=? AND symbol=?",
                    (chat_id, user_id, symbol),
                )
            else:
                await conn.execute(
                    """
                    UPDATE finance_stock_positions_v127
                    SET quantity=?,total_cost=?,realized_profit=realized_profit+?,updated_at=?
                    WHERE chat_id=? AND user_id=? AND symbol=?
                    """,
                    (remaining_quantity, remaining_cost, realized, now, chat_id, user_id, symbol),
                )
            delta = net
            direction = -1
            message = (
                f"Продано {quantity} акц. {symbol} по {_fmt(price)}. "
                f"Получено {_fmt(net)}, результат сделки {realized:+d}."
            )
        await conn.execute(
            """
            INSERT INTO finance_stock_trades_v127(
                trade_id,chat_id,user_id,symbol,side,quantity,price,gross,fee,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (trade_id, chat_id, user_id, symbol, side, quantity, price, gross, fee, now),
        )
        impact_bp = max(2, min(40, round(gross * 40 / MAX_TRADE_VALUE)))
        raw_price = max(5.0, price * (1 + direction * impact_bp / 10_000))
        adjusted_price = max(5, round(raw_price))
        bucket = now // MARKET_TICK_SECONDS
        await conn.execute(
            """
            UPDATE finance_market_v127
            SET previous_price=price,price=?,high_price=MAX(high_price,?),low_price=MIN(low_price,?),
                volume=volume+?
            WHERE chat_id=? AND symbol=?
            """,
            (adjusted_price, adjusted_price, adjusted_price, gross, chat_id, symbol),
        )
        await conn.execute(
            """
            INSERT INTO finance_stock_history_v127(chat_id,symbol,bucket,price,volume)
            VALUES(?,?,?,?,?)
            ON CONFLICT(chat_id,symbol,bucket) DO UPDATE SET
            price=excluded.price,volume=finance_stock_history_v127.volume+excluded.volume
            """,
            (chat_id, symbol, bucket, adjusted_price, gross),
        )
        await conn.execute(
            "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
            (chat_id, user_id, delta, f"investment_stock_{side}_v127", now),
        )
        await conn.commit()
    return message
