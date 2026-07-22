from __future__ import annotations

import math
from typing import Any

import finance_investments_v127_core as investment_core

VERSION = "Reality 167 · Экономика государственных фондов"
FUND_EFFECT_SECONDS = 3_600
DAY_SECONDS = 86_400

STRUCTURE_TITLES = {
    "presidential_admin": "Администрация президента",
    "duma": "Государственная дума",
    "finance_ministry": "Министерство финансов",
    "oversight": "Государственный надзор",
    "election_commission": "Избирательная комиссия",
    "event_fund": "Фонд государственных событий",
    "social_fund": "Социальный фонд",
    "reserve": "Резервный фонд",
}

STOCK_FUND_WEIGHTS = {
    "EGO": {"presidential_admin": .30, "event_fund": .25, "social_fund": .15, "duma": .10, "reserve": .20},
    "HERO": {"reserve": .35, "finance_ministry": .25, "social_fund": .20, "presidential_admin": .10, "event_fund": .10},
    "NPC": {"social_fund": .35, "duma": .20, "election_commission": .15, "oversight": .15, "reserve": .15},
    "CORV": {"finance_ministry": .30, "reserve": .25, "event_fund": .20, "presidential_admin": .10, "social_fund": .15},
    "CENTER": {"reserve": .25, "event_fund": .25, "presidential_admin": .25, "finance_ministry": .15, "social_fund": .10},
}

def _clamp(low: int, high: int, value: float) -> int:
    return max(int(low), min(int(high), int(round(value))))

def _row_value(row: Any, key: str, default: int = 0) -> int:
    try:
        keys = set(row.keys())
        if key in keys and row[key] is not None:
            return int(row[key])
    except Exception:
        pass
    return int(default)

async def _table_exists(conn: Any, name: str) -> bool:
    cursor = await conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (str(name),),
    )
    return await cursor.fetchone() is not None

async def _ensure_schema(core: Any) -> None:
    if getattr(core, "_finance_fund_link_schema_v167_ready", False):
        return
    await investment_core._ensure_schema(core)
    conn = core.db._require_connection()
    async with core.db.lock:
        cursor = await conn.execute("PRAGMA table_info(finance_deposits_v127)")
        columns = {str(row["name"]) for row in await cursor.fetchall()}
        if "yield_multiplier_bp" not in columns:
            await conn.execute(
                "ALTER TABLE finance_deposits_v127 ADD COLUMN yield_multiplier_bp INTEGER NOT NULL DEFAULT 10000"
            )
        if "fund_index_at_open" not in columns:
            await conn.execute(
                "ALTER TABLE finance_deposits_v127 ADD COLUMN fund_index_at_open INTEGER NOT NULL DEFAULT 0"
            )
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS finance_fund_effects_v167(
                chat_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                effect_bucket INTEGER NOT NULL,
                effect_bp INTEGER NOT NULL,
                government_funds INTEGER NOT NULL,
                private_funds INTEGER NOT NULL,
                government_flow_24h INTEGER NOT NULL,
                private_flow_24h INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                PRIMARY KEY(chat_id,symbol,effect_bucket)
            );
            CREATE INDEX IF NOT EXISTS idx_finance_fund_effects_v167
                ON finance_fund_effects_v167(chat_id,effect_bucket DESC);
            """
        )
        await conn.commit()
    core._finance_fund_link_schema_v167_ready = True

async def _fund_snapshot(core: Any, chat_id: int) -> dict[str, Any]:
    await _ensure_schema(core)
    conn = core.db._require_connection()
    now = investment_core._now()
    since = now - DAY_SECONDS
    balances = {key: 0 for key in STRUCTURE_TITLES}
    flows = {key: 0 for key in STRUCTURE_TITLES}

    if await _table_exists(conn, "government_structure_funds_v164"):
        cursor = await conn.execute(
            """
            SELECT structure_key,balance
            FROM government_structure_funds_v164
            WHERE chat_id=?
            """,
            (int(chat_id),),
        )
        for row in await cursor.fetchall():
            key = str(row["structure_key"])
            if key in balances:
                balances[key] = max(0, int(row["balance"] or 0))

    if await _table_exists(conn, "government_treasury_operations_v164"):
        cursor = await conn.execute(
            """
            SELECT target_key,COALESCE(SUM(amount),0) amount
            FROM government_treasury_operations_v164
            WHERE chat_id=? AND target_type='structure' AND created_at>=?
            GROUP BY target_key
            """,
            (int(chat_id), since),
        )
        for row in await cursor.fetchall():
            key = str(row["target_key"])
            if key in flows:
                flows[key] = int(row["amount"] or 0)

    cursor = await conn.execute(
        """
        SELECT COALESCE(SUM(principal),0) total,
               COALESCE(SUM(CASE WHEN started_at>=? THEN principal ELSE 0 END),0) flow
        FROM finance_deposits_v127
        WHERE chat_id=? AND status='active'
        """,
        (since, int(chat_id)),
    )
    deposit_row = await cursor.fetchone()
    active_deposits = int(deposit_row["total"] if deposit_row else 0)
    deposit_flow = int(deposit_row["flow"] if deposit_row else 0)

    cursor = await conn.execute(
        """
        SELECT COALESCE(SUM(CASE WHEN side='buy' THEN gross ELSE -gross END),0) net_flow
        FROM finance_stock_trades_v127
        WHERE chat_id=? AND created_at>=?
        """,
        (int(chat_id), since),
    )
    trade_row = await cursor.fetchone()
    stock_flow = int(trade_row["net_flow"] if trade_row else 0)

    cursor = await conn.execute(
        """
        SELECT COALESCE(SUM(quantity*m.price),0) total
        FROM finance_stock_positions_v127 p
        LEFT JOIN finance_market_v127 m
          ON m.chat_id=p.chat_id AND m.symbol=p.symbol
        WHERE p.chat_id=?
        """,
        (int(chat_id),),
    )
    position_row = await cursor.fetchone()
    stock_capital = int(position_row["total"] if position_row else 0)

    government_total = sum(balances.values())
    government_flow = sum(flows.values())
    private_total = max(0, active_deposits + stock_capital)
    private_flow = deposit_flow + stock_flow
    total_capital = government_total + private_total

    reserve_cover = balances["reserve"] + balances["finance_ministry"]
    coverage = reserve_cover / max(1, active_deposits)
    capital_score = min(55.0, math.log1p(total_capital) / math.log1p(1_000_000) * 55.0)
    flow_score = _clamp(-10, 25, (government_flow + private_flow) / 10_000 * 4.0)
    coverage_score = min(20.0, coverage * 12.0)
    fund_index = _clamp(0, 100, capital_score + flow_score + coverage_score)
    deposit_multiplier_bp = _clamp(7_500, 13_500, 8_000 + fund_index * 55)

    stock_effects: dict[str, int] = {}
    stock_support: dict[str, dict[str, Any]] = {}
    for symbol, weights in STOCK_FUND_WEIGHTS.items():
        weighted_balance = sum(balances.get(key, 0) * weight for key, weight in weights.items())
        weighted_flow = sum(flows.get(key, 0) * weight for key, weight in weights.items())
        capital_component = (
            math.log1p(max(0.0, weighted_balance)) / math.log1p(100_000) - 0.45
        ) * 26.0
        flow_component = _clamp(-8, 18, weighted_flow / 10_000 * 6.0)
        private_component = (
            math.log1p(max(0, private_total)) / math.log1p(250_000) - 0.35
        ) * 8.0
        effect_bp = _clamp(-18, 35, capital_component + flow_component + private_component)
        stock_effects[symbol] = effect_bp
        leaders = sorted(
            (
                {
                    "key": key,
                    "title": STRUCTURE_TITLES.get(key, key),
                    "balance": balances.get(key, 0),
                    "flow_24h": flows.get(key, 0),
                    "weight": weight,
                }
                for key, weight in weights.items()
            ),
            key=lambda item: item["balance"] * item["weight"],
            reverse=True,
        )
        stock_support[symbol] = {
            "weighted_balance": round(weighted_balance),
            "weighted_flow_24h": round(weighted_flow),
            "effect_bp": effect_bp,
            "effect_percent": round(effect_bp / 100, 2),
            "leading_funds": leaders[:3],
        }

    return {
        "fund_index": fund_index,
        "deposit_multiplier_bp": deposit_multiplier_bp,
        "deposit_multiplier": round(deposit_multiplier_bp / 10_000, 4),
        "government_total": government_total,
        "government_flow_24h": government_flow,
        "private_total": private_total,
        "private_flow_24h": private_flow,
        "active_deposits": active_deposits,
        "stock_capital": stock_capital,
        "balances": balances,
        "flows_24h": flows,
        "stock_effects": stock_effects,
        "stock_support": stock_support,
        "updated_at": now,
    }

def _deposit_values_with_funds(row: Any, now: int) -> tuple[int, int, bool, bool]:
    plan = investment_core.DEPOSIT_PLANS[str(row["plan_key"])]
    principal = int(row["principal"])
    started_at = int(row["started_at"])
    matures_at = int(row["matures_at"])
    matured = now >= matures_at
    multiplier_bp = _row_value(row, "yield_multiplier_bp", 10_000)
    multiplier = max(0.5, min(1.5, multiplier_bp / 10_000))
    if str(row["plan_key"]) == "flex":
        elapsed = min(max(0, now - started_at), int(plan["term_days"]) * DAY_SECONDS)
        daily_percent = float(plan["daily_percent"]) * multiplier
        interest = math.floor(principal * daily_percent / 100 * elapsed / DAY_SECONDS)
        payout = principal + interest
        can_withdraw = True
    else:
        effective_yield = float(plan["yield_percent"]) * multiplier
        payout = math.floor(principal * (100 + effective_yield) / 100) if matured else principal
        can_withdraw = matured or str(plan["early"]) != "locked"
    return payout, max(0, payout - principal), matured, can_withdraw

async def _apply_fund_effect(core: Any, chat_id: int) -> dict[str, Any]:
    snapshot = await _fund_snapshot(core, chat_id)
    conn = core.db._require_connection()
    now = investment_core._now()
    effect_bucket = now // FUND_EFFECT_SECONDS
    minute_bucket = now // investment_core.MARKET_TICK_SECONDS

    async with core.db.lock:
        for symbol, effect_bp in snapshot["stock_effects"].items():
            cursor = await conn.execute(
                """
                SELECT 1 FROM finance_fund_effects_v167
                WHERE chat_id=? AND symbol=? AND effect_bucket=?
                """,
                (int(chat_id), symbol, effect_bucket),
            )
            if await cursor.fetchone() is not None:
                continue
            cursor = await conn.execute(
                "SELECT price FROM finance_market_v127 WHERE chat_id=? AND symbol=?",
                (int(chat_id), symbol),
            )
            market = await cursor.fetchone()
            if market is None:
                continue
            price = int(market["price"])
            adjusted = max(5, round(price * (1 + int(effect_bp) / 10_000)))
            if adjusted == price and abs(int(effect_bp)) >= 8:
                adjusted = max(5, price + (1 if int(effect_bp) > 0 else -1))
            direction = "поддержали" if int(effect_bp) >= 0 else "ослабили"
            title = f"Государственные фонды {direction} сектор {symbol}"
            summary = (
                f"Фондовый импульс: {int(effect_bp) / 100:+.2f}%. "
                f"В госфондах {snapshot['government_total']:,}, "
                f"в частном финансовом фонде {snapshot['private_total']:,}."
            ).replace(",", " ")
            source_key = f"fund-v167:{symbol}:{effect_bucket}"
            await conn.execute(
                """
                UPDATE finance_market_v127
                SET previous_price=price,price=?,high_price=MAX(high_price,?),
                    low_price=MIN(low_price,?),last_event=?,last_event_at=?
                WHERE chat_id=? AND symbol=?
                """,
                (adjusted, adjusted, adjusted, title, now, int(chat_id), symbol),
            )
            await conn.execute(
                """
                INSERT INTO finance_stock_history_v127(chat_id,symbol,bucket,price,volume)
                VALUES(?,?,?,?,0)
                ON CONFLICT(chat_id,symbol,bucket) DO UPDATE SET price=excluded.price
                """,
                (int(chat_id), symbol, minute_bucket, adjusted),
            )
            await conn.execute(
                """
                INSERT OR IGNORE INTO finance_market_news_v128(
                    news_id,chat_id,symbol,source_key,source_type,category,title,summary,
                    body,effect_bp,event_at,source_at,created_at,applied
                ) VALUES(?,?,?,?, 'government_funds','Государственные фонды',?,?,?,
                         ?,?,?,?,1)
                """,
                (
                    f"fund-{chat_id}-{symbol}-{effect_bucket}",
                    int(chat_id),
                    symbol,
                    source_key,
                    title,
                    summary,
                    (
                        "Курс учитывает баланс профильных государственных фондов, "
                        "приток денег в них за 24 часа, активные вклады и капитал игроков на бирже."
                    ),
                    int(effect_bp),
                    now,
                    now,
                    now,
                ),
            )
            await conn.execute(
                """
                INSERT INTO finance_fund_effects_v167(
                    chat_id,symbol,effect_bucket,effect_bp,government_funds,private_funds,
                    government_flow_24h,private_flow_24h,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    int(chat_id),
                    symbol,
                    effect_bucket,
                    int(effect_bp),
                    int(snapshot["government_total"]),
                    int(snapshot["private_total"]),
                    int(snapshot["government_flow_24h"]),
                    int(snapshot["private_flow_24h"]),
                    now,
                ),
            )
        await conn.commit()
    return snapshot
