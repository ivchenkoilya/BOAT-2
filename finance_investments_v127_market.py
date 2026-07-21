from __future__ import annotations

from typing import Any

from finance_investments_v127_core import (
    DEPOSIT_PLANS, EVENTS_DOWN, EVENTS_UP, MARKET_HISTORY_SECONDS, MARKET_TICK_SECONDS,
    MAX_ACTIVE_DEPOSITS, MAX_DEPOSIT_TOTAL, MAX_TRADE_VALUE, STOCKS, TRADE_FEE_PERCENT,
    VERSION, _chat_id, _deposit_values, _ensure_schema, _hash_numbers, _now,
)

async def _initialize_market(core: Any, chat_id: int) -> None:
    conn = core.db._require_connection()
    now = _now()
    current_bucket = now // MARKET_TICK_SECONDS
    async with core.db.lock:
        for symbol, spec in STOCKS.items():
            cursor = await conn.execute(
                "SELECT 1 FROM finance_market_v127 WHERE chat_id=? AND symbol=?",
                (chat_id, symbol),
            )
            if await cursor.fetchone() is not None:
                continue
            price = int(spec["base_price"])
            start_bucket = current_bucket - 288
            history_rows: list[tuple[int, str, int, int]] = []
            high = price
            low = price
            event_text = ""
            event_at = 0
            for bucket in range(start_bucket, current_bucket + 1):
                rnd, event_rnd, selector = _hash_numbers(chat_id, symbol, bucket)
                step_bp = float(spec["drift_bp"]) + (rnd * 2 - 1) * float(spec["volatility_bp"])
                if event_rnd < 0.004:
                    direction = 1 if selector % 2 == 0 else -1
                    step_bp += direction * (280 + selector % 520)
                    event_text = (EVENTS_UP if direction > 0 else EVENTS_DOWN)[selector % 4]
                    event_at = bucket * MARKET_TICK_SECONDS
                price = max(5, round(price * (1 + step_bp / 10_000)))
                high = max(high, price)
                low = min(low, price)
                history_rows.append((chat_id, symbol, bucket, price))
            await conn.executemany(
                "INSERT OR IGNORE INTO finance_stock_history_v127(chat_id,symbol,bucket,price) VALUES(?,?,?,?)",
                history_rows,
            )
            await conn.execute(
                """
                INSERT INTO finance_market_v127(
                    chat_id,symbol,price,previous_price,open_price,high_price,low_price,
                    volume,updated_at,created_at,last_event,last_event_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    chat_id,
                    symbol,
                    price,
                    history_rows[-2][3] if len(history_rows) > 1 else price,
                    history_rows[0][3],
                    high,
                    low,
                    0,
                    current_bucket * MARKET_TICK_SECONDS,
                    start_bucket * MARKET_TICK_SECONDS,
                    event_text,
                    event_at,
                ),
            )
        await conn.commit()


async def _advance_market(core: Any, chat_id: int) -> None:
    await _initialize_market(core, chat_id)
    conn = core.db._require_connection()
    now = _now()
    current_bucket = now // MARKET_TICK_SECONDS
    async with core.db.lock:
        for symbol, spec in STOCKS.items():
            cursor = await conn.execute(
                "SELECT * FROM finance_market_v127 WHERE chat_id=? AND symbol=?",
                (chat_id, symbol),
            )
            row = await cursor.fetchone()
            if row is None:
                continue
            last_bucket = int(row["updated_at"]) // MARKET_TICK_SECONDS
            if last_bucket >= current_bucket:
                continue
            first_bucket = max(last_bucket + 1, current_bucket - 576)
            price = int(row["price"])
            previous = price
            high = int(row["high_price"])
            low = int(row["low_price"])
            last_event = str(row["last_event"] or "")
            last_event_at = int(row["last_event_at"] or 0)
            history_rows: list[tuple[int, str, int, int]] = []
            for bucket in range(first_bucket, current_bucket + 1):
                previous = price
                rnd, event_rnd, selector = _hash_numbers(chat_id, symbol, bucket)
                step_bp = float(spec["drift_bp"]) + (rnd * 2 - 1) * float(spec["volatility_bp"])
                if event_rnd < 0.004:
                    direction = 1 if selector % 2 == 0 else -1
                    step_bp += direction * (280 + selector % 520)
                    last_event = (EVENTS_UP if direction > 0 else EVENTS_DOWN)[selector % 4]
                    last_event_at = bucket * MARKET_TICK_SECONDS
                price = max(5, round(price * (1 + step_bp / 10_000)))
                high = max(high, price)
                low = min(low, price)
                history_rows.append((chat_id, symbol, bucket, price))
            if history_rows:
                await conn.executemany(
                    "INSERT OR REPLACE INTO finance_stock_history_v127(chat_id,symbol,bucket,price) VALUES(?,?,?,?)",
                    history_rows,
                )
            await conn.execute(
                """
                UPDATE finance_market_v127
                SET price=?,previous_price=?,high_price=?,low_price=?,updated_at=?,last_event=?,last_event_at=?
                WHERE chat_id=? AND symbol=?
                """,
                (
                    price,
                    previous,
                    high,
                    low,
                    current_bucket * MARKET_TICK_SECONDS,
                    last_event,
                    last_event_at,
                    chat_id,
                    symbol,
                ),
            )
        cutoff_bucket = (now - MARKET_HISTORY_SECONDS) // MARKET_TICK_SECONDS
        await conn.execute(
            "DELETE FROM finance_stock_history_v127 WHERE chat_id=? AND bucket<?",
            (chat_id, cutoff_bucket),
        )
        await conn.commit()


async def _auth(core: Any, request: Any) -> tuple[Any, int, dict[str, Any], Any]:
    user, start_param = core._webapp_auth(request)
    if user is None:
        raise PermissionError(start_param or "Нет авторизации Telegram.")
    data: dict[str, Any] = {}
    if request.method == "POST":
        try:
            value = await request.json()
            if isinstance(value, dict):
                data = value
        except Exception:
            data = {}
    chat_id = _chat_id(start_param, request, data)
    player = await core.db.get_player(chat_id, int(user.id))
    if player is None:
        raise PermissionError("Сначала используй бота в нужной групповой беседе.")
    return user, chat_id, data, player


async def _investment_payload(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    await _ensure_schema(core)
    await _advance_market(core, chat_id)
    conn = core.db._require_connection()
    now = _now()

    cursor = await conn.execute(
        "SELECT * FROM finance_deposits_v127 WHERE chat_id=? AND user_id=? AND status='active' ORDER BY started_at DESC",
        (chat_id, user_id),
    )
    deposits: list[dict[str, Any]] = []
    deposit_total = 0
    for row in await cursor.fetchall():
        payout, interest, matured, can_withdraw = _deposit_values(row, now)
        deposit_total += payout
        plan = DEPOSIT_PLANS[str(row["plan_key"])]
        deposits.append(
            {
                "deposit_id": str(row["deposit_id"]),
                "plan_key": str(row["plan_key"]),
                "title": str(plan["title"]),
                "principal": int(row["principal"]),
                "payout": payout,
                "interest": interest,
                "started_at": int(row["started_at"]),
                "matures_at": int(row["matures_at"]),
                "matured": matured,
                "can_withdraw": can_withdraw,
                "early_note": str(plan["early_note"]),
            }
        )

    cursor = await conn.execute(
        "SELECT * FROM finance_stock_positions_v127 WHERE chat_id=? AND user_id=? ORDER BY updated_at DESC",
        (chat_id, user_id),
    )
    positions = {str(row["symbol"]): row for row in await cursor.fetchall()}

    cursor = await conn.execute(
        "SELECT * FROM finance_market_v127 WHERE chat_id=? ORDER BY symbol",
        (chat_id,),
    )
    market_rows = {str(row["symbol"]): row for row in await cursor.fetchall()}
    stocks: list[dict[str, Any]] = []
    portfolio_value = 0
    portfolio_cost = 0
    for symbol, spec in STOCKS.items():
        row = market_rows[symbol]
        price = int(row["price"])
        day_bucket = (now - 24 * 60 * 60) // MARKET_TICK_SECONDS
        cursor = await conn.execute(
            """
            SELECT price FROM finance_stock_history_v127
            WHERE chat_id=? AND symbol=? AND bucket<=?
            ORDER BY bucket DESC LIMIT 1
            """,
            (chat_id, symbol, day_bucket),
        )
        baseline_row = await cursor.fetchone()
        baseline_price = max(1, int(baseline_row["price"]) if baseline_row else int(row["open_price"]))
        change_percent = round((price - baseline_price) * 100 / baseline_price, 2)
        position = positions.get(symbol)
        quantity = int(position["quantity"]) if position else 0
        total_cost = int(position["total_cost"]) if position else 0
        position_value = quantity * price
        portfolio_value += position_value
        portfolio_cost += total_cost

        history: list[dict[str, int]] = []
        stocks.append(
            {
                "symbol": symbol,
                "name": str(spec["name"]),
                "icon": str(spec["icon"]),
                "description": str(spec["description"]),
                "risk": str(spec["risk"]),
                "price": price,
                "previous_price": int(row["previous_price"]),
                "change_percent": change_percent,
                "high": int(row["high_price"]),
                "low": int(row["low_price"]),
                "volume": int(row["volume"]),
                "updated_at": int(row["updated_at"]),
                "last_event": str(row["last_event"] or ""),
                "last_event_at": int(row["last_event_at"] or 0),
                "history": history,
                "position": {
                    "quantity": quantity,
                    "total_cost": total_cost,
                    "average_price": round(total_cost / quantity, 2) if quantity else 0,
                    "value": position_value,
                    "profit": position_value - total_cost,
                    "realized_profit": int(position["realized_profit"]) if position else 0,
                },
            }
        )

    cursor = await conn.execute(
        """
        SELECT * FROM finance_stock_trades_v127
        WHERE chat_id=? AND user_id=? ORDER BY created_at DESC LIMIT 20
        """,
        (chat_id, user_id),
    )
    trades = [
        {
            "trade_id": str(row["trade_id"]),
            "symbol": str(row["symbol"]),
            "side": str(row["side"]),
            "quantity": int(row["quantity"]),
            "price": int(row["price"]),
            "gross": int(row["gross"]),
            "fee": int(row["fee"]),
            "created_at": int(row["created_at"]),
        }
        for row in await cursor.fetchall()
    ]

    return {
        "ok": True,
        "version": VERSION,
        "server_time": now,
        "market_tick_seconds": MARKET_TICK_SECONDS,
        "fee_percent": TRADE_FEE_PERCENT,
        "limits": {
            "max_deposit_total": MAX_DEPOSIT_TOTAL,
            "max_active_deposits": MAX_ACTIVE_DEPOSITS,
            "max_trade_value": MAX_TRADE_VALUE,
        },
        "plans": [
            {
                "key": key,
                "title": str(plan["title"]),
                "term_days": int(plan["term_days"]),
                "yield_percent": float(plan["yield_percent"]),
                "daily_percent": float(plan.get("daily_percent", 0)),
                "early": str(plan["early"]),
                "early_note": str(plan["early_note"]),
            }
            for key, plan in DEPOSIT_PLANS.items()
        ],
        "deposits": deposits,
        "stocks": stocks,
        "trades": trades,
        "totals": {
            "deposits": deposit_total,
            "portfolio": portfolio_value,
            "portfolio_cost": portfolio_cost,
            "portfolio_profit": portfolio_value - portfolio_cost,
        },
    }
