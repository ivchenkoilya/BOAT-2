from __future__ import annotations

import math
from typing import Any

from finance_investments_v127_core import (
    DEPOSIT_PLANS, MARKET_HISTORY_SECONDS, MARKET_TICK_SECONDS,
    MAX_ACTIVE_DEPOSITS, MAX_DEPOSIT_TOTAL, MAX_TRADE_VALUE, STOCKS, TRADE_FEE_PERCENT,
    VERSION, _chat_id, _deposit_values, _ensure_schema, _hash_numbers, _now,
)
from finance_market_news_v128 import (
    _insert_news, latest_news, news_for_range, random_company_news, sync_government_news,
)


def _stochastic_price(price: int, step_bp: float, random_value: float) -> int:
    raw = max(5.0, float(price) * (1.0 + float(step_bp) / 10_000.0))
    lower = math.floor(raw)
    return max(5, lower + (1 if random_value < raw - lower else 0))


def _store_bucket(bucket: int, current_bucket: int) -> bool:
    age = current_bucket - bucket
    if age <= 24 * 60:
        return True
    if age <= 7 * 24 * 60:
        return bucket % 5 == 0
    return bucket % 15 == 0


async def _seed_history_locked(
    conn: Any,
    chat_id: int,
    symbol: str,
    spec: dict[str, Any],
    current_price: int,
    current_bucket: int,
) -> tuple[int, int, int, int]:
    start_bucket = current_bucket - MARKET_HISTORY_SECONDS // MARKET_TICK_SECONDS
    raw_price = 1000.0
    raw_samples: list[tuple[int, float, int]] = []
    for bucket in range(start_bucket, current_bucket + 1):
        rnd, volume_rnd, selector = _hash_numbers(chat_id, symbol, bucket)
        step_bp = float(spec["drift_bp"]) + (rnd * 2 - 1) * float(spec["volatility_bp"])
        raw_price = max(100.0, raw_price * (1 + step_bp / 10_000))
        if _store_bucket(bucket, current_bucket):
            volume = max(1, round((15 + selector % 85) * (1 + abs(step_bp) / 18)))
            raw_samples.append((bucket, raw_price, volume))
    scale = max(0.005, float(current_price) / max(1.0, raw_samples[-1][1]))
    rows: list[tuple[int, str, int, int, int]] = []
    for bucket, raw, volume in raw_samples:
        rows.append((chat_id, symbol, bucket, max(5, round(raw * scale)), volume))
    await conn.execute(
        "DELETE FROM finance_stock_history_v127 WHERE chat_id=? AND symbol=?",
        (chat_id, symbol),
    )
    await conn.executemany(
        "INSERT INTO finance_stock_history_v127(chat_id,symbol,bucket,price,volume) VALUES(?,?,?,?,?)",
        rows,
    )
    prices = [row[3] for row in rows]
    previous = rows[-2][3] if len(rows) > 1 else current_price
    return rows[0][3], max(prices), min(prices), previous


async def _initialize_market(core: Any, chat_id: int) -> None:
    conn = core.db._require_connection()
    now = _now()
    current_bucket = now // MARKET_TICK_SECONDS
    async with core.db.lock:
        for symbol, spec in STOCKS.items():
            cursor = await conn.execute(
                "SELECT * FROM finance_market_v127 WHERE chat_id=? AND symbol=?",
                (chat_id, symbol),
            )
            market = await cursor.fetchone()
            if market is None:
                price = int(spec["base_price"])
                await conn.execute(
                    """
                    INSERT INTO finance_market_v127(
                        chat_id,symbol,price,previous_price,open_price,high_price,low_price,
                        volume,updated_at,created_at,last_event,last_event_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        chat_id, symbol, price, price, price, price, price, 0,
                        current_bucket * MARKET_TICK_SECONDS,
                        (current_bucket - MARKET_HISTORY_SECONDS // MARKET_TICK_SECONDS) * MARKET_TICK_SECONDS,
                        "", 0,
                    ),
                )
                market_price = price
            else:
                market_price = int(market["price"])

            cursor = await conn.execute(
                "SELECT MAX(bucket) maximum,COUNT(*) amount FROM finance_stock_history_v127 WHERE chat_id=? AND symbol=?",
                (chat_id, symbol),
            )
            history = await cursor.fetchone()
            maximum = int(history["maximum"] or 0)
            amount = int(history["amount"] or 0)
            old_bucket_format = maximum and maximum < current_bucket - MARKET_HISTORY_SECONDS // MARKET_TICK_SECONDS - 120
            if amount < 10 or old_bucket_format:
                open_price, high, low, previous = await _seed_history_locked(
                    conn, chat_id, symbol, spec, market_price, current_bucket
                )
                await conn.execute(
                    """
                    UPDATE finance_market_v127
                    SET previous_price=?,open_price=?,high_price=?,low_price=?,updated_at=?
                    WHERE chat_id=? AND symbol=?
                    """,
                    (previous, open_price, high, low, current_bucket * MARKET_TICK_SECONDS, chat_id, symbol),
                )
        await conn.commit()


async def _advance_market(core: Any, chat_id: int) -> None:
    await _ensure_schema(core)
    await sync_government_news(core, chat_id)
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
            first_bucket = max(last_bucket + 1, current_bucket - 7 * 24 * 60)
            price = int(row["price"])
            previous = price
            high = int(row["high_price"])
            low = int(row["low_price"])
            last_event = str(row["last_event"] or "")
            last_event_at = int(row["last_event_at"] or 0)
            news_rows = await news_for_range(
                conn, chat_id, symbol,
                first_bucket * MARKET_TICK_SECONDS,
                current_bucket * MARKET_TICK_SECONDS,
            )
            news_by_bucket: dict[int, list[dict[str, Any]]] = {}
            for item in news_rows:
                news_by_bucket.setdefault(int(item["event_at"]) // MARKET_TICK_SECONDS, []).append(item)

            history_rows: list[tuple[int, str, int, int, int]] = []
            total_volume = 0
            for bucket in range(first_bucket, current_bucket + 1):
                previous = price
                rnd, event_rnd, selector = _hash_numbers(chat_id, symbol, bucket)
                step_bp = float(spec["drift_bp"]) + (rnd * 2 - 1) * float(spec["volatility_bp"])
                bucket_news = list(news_by_bucket.get(bucket, []))

                if event_rnd < 0.0012:
                    direction = 1 if selector % 2 == 0 else -1
                    random_effect = direction * (140 + selector % 360)
                    title, summary, body = random_company_news(symbol, selector, direction)
                    await _insert_news(
                        conn,
                        chat_id=chat_id,
                        symbol=symbol,
                        source_key=f"company:{symbol}:{bucket}",
                        source_type="company_news",
                        category="Новости компании",
                        title=title,
                        summary=summary,
                        body=body,
                        effect_bp=random_effect,
                        event_at=bucket * MARKET_TICK_SECONDS,
                        source_at=bucket * MARKET_TICK_SECONDS,
                    )
                    random_item = {
                        "title": title,
                        "effect_bp": random_effect,
                        "event_at": bucket * MARKET_TICK_SECONDS,
                    }
                    bucket_news.append(random_item)

                if bucket_news:
                    step_bp += sum(int(item["effect_bp"]) for item in bucket_news)
                    latest = bucket_news[-1]
                    last_event = str(latest["title"])
                    last_event_at = int(latest["event_at"])

                price = _stochastic_price(price, step_bp, event_rnd)
                high = max(high, price)
                low = min(low, price)
                movement = abs(price - previous)
                minute_volume = max(
                    1,
                    round((12 + selector % 90) * (1 + abs(step_bp) / 20) + movement * price * 1.5),
                )
                total_volume += minute_volume
                history_rows.append((chat_id, symbol, bucket, price, minute_volume))

            if history_rows:
                await conn.executemany(
                    """
                    INSERT INTO finance_stock_history_v127(chat_id,symbol,bucket,price,volume)
                    VALUES(?,?,?,?,?)
                    ON CONFLICT(chat_id,symbol,bucket) DO UPDATE SET
                    price=excluded.price,volume=MAX(finance_stock_history_v127.volume,excluded.volume)
                    """,
                    history_rows,
                )
            await conn.execute(
                """
                UPDATE finance_market_v127
                SET price=?,previous_price=?,high_price=?,low_price=?,volume=volume+?,
                    updated_at=?,last_event=?,last_event_at=?
                WHERE chat_id=? AND symbol=?
                """,
                (
                    price, previous, high, low, total_volume,
                    current_bucket * MARKET_TICK_SECONDS,
                    last_event, last_event_at, chat_id, symbol,
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


def _news_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "news_id": str(row["news_id"]),
        "symbol": str(row["symbol"]),
        "source_type": str(row["source_type"]),
        "category": str(row["category"]),
        "title": str(row["title"]),
        "summary": str(row["summary"]),
        "body": str(row["body"]),
        "effect_bp": int(row["effect_bp"]),
        "effect_percent": round(int(row["effect_bp"]) / 100, 2),
        "event_at": int(row["event_at"]),
        "source_at": int(row["source_at"]),
    }


async def _investment_payload(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
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
        withdraw_payout = payout
        if not matured:
            if str(plan["early"]) == "interest_lost":
                withdraw_payout = int(row["principal"])
            elif str(plan["early"]) == "penalty_3":
                withdraw_payout = max(0, int(int(row["principal"]) * 0.97))
            elif str(plan["early"]) == "locked":
                withdraw_payout = 0
        deposits.append(
            {
                "deposit_id": str(row["deposit_id"]),
                "plan_key": str(row["plan_key"]),
                "title": str(plan["title"]),
                "principal": int(row["principal"]),
                "payout": payout,
                "withdraw_payout": withdraw_payout,
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
    all_news_rows = await latest_news(conn, chat_id, limit=30)
    news_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for item in all_news_rows:
        news_by_symbol.setdefault(str(item["symbol"]), []).append(_news_dict(item))

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
        symbol_news = news_by_symbol.get(symbol, [])

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
                "latest_news": symbol_news[0] if symbol_news else None,
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
        "news": [_news_dict(item) for item in all_news_rows],
        "trades": trades,
        "totals": {
            "deposits": deposit_total,
            "portfolio": portfolio_value,
            "portfolio_cost": portfolio_cost,
            "portfolio_profit": portfolio_value - portfolio_cost,
        },
    }
