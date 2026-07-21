from __future__ import annotations

import time
from typing import Any

import admin_government_market_v132 as admin_market
import finance_investments_v127 as investments_app
import finance_investments_v127_core as invest_core
import finance_investments_v127_market as invest_market
import finance_investments_v127_ops as invest_ops


VERSION = "Reality 132 · Заморозка курса"


async def _ensure_lock_column(core: Any) -> None:
    await admin_market._ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute("PRAGMA table_info(finance_stock_admin_v132)")
    columns = {str(row["name"]) for row in await cursor.fetchall()}
    if "price_locked" not in columns:
        async with core.db.lock:
            await conn.execute(
                "ALTER TABLE finance_stock_admin_v132 "
                "ADD COLUMN price_locked INTEGER NOT NULL DEFAULT 0"
            )
            await conn.commit()


async def _set_lock(core: Any, chat_id: int, symbol: str, locked: bool) -> None:
    await _ensure_lock_column(core)
    conn = core.db._require_connection()
    await conn.execute(
        """
        INSERT INTO finance_stock_admin_v132(
            chat_id,symbol,trading_paused,price_locked,updated_at
        ) VALUES(?,?,0,?,?) ON CONFLICT(chat_id,symbol) DO UPDATE SET
            price_locked=excluded.price_locked,updated_at=excluded.updated_at
        """,
        (int(chat_id), str(symbol).upper(), 1 if locked else 0, int(time.time())),
    )
    await conn.commit()


def install_admin_market_lock_hotfix_v132(core: Any) -> None:
    if getattr(core, "_admin_market_lock_hotfix_v132_installed", False):
        return
    core._admin_market_lock_hotfix_v132_installed = True

    previous_connect = core.Database.connect

    async def connect_with_lock_column(self: Any) -> None:
        await previous_connect(self)
        await _ensure_lock_column(core)

    core.Database.connect = connect_with_lock_column

    original_advance = invest_market._advance_market

    async def advance_with_locked_prices(core_value: Any, chat_id: int) -> None:
        await _ensure_lock_column(core_value)
        await invest_core._ensure_schema(core_value)
        await invest_market._initialize_market(core_value, int(chat_id))
        conn = core_value.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT a.symbol,m.price
            FROM finance_stock_admin_v132 a
            JOIN finance_market_v127 m
              ON m.chat_id=a.chat_id AND m.symbol=a.symbol
            WHERE a.chat_id=? AND a.price_locked=1
            """,
            (int(chat_id),),
        )
        locked = {
            str(row["symbol"]): int(row["price"])
            for row in await cursor.fetchall()
        }
        await original_advance(core_value, int(chat_id))
        if not locked:
            return
        now = int(time.time())
        bucket = now // invest_core.MARKET_TICK_SECONDS
        async with core_value.db.lock:
            for symbol, price in locked.items():
                await conn.execute(
                    """
                    UPDATE finance_market_v127
                    SET price=?,previous_price=?,updated_at=?
                    WHERE chat_id=? AND symbol=?
                    """,
                    (price, price, now, int(chat_id), symbol),
                )
                await conn.execute(
                    """
                    INSERT INTO finance_stock_history_v127(
                        chat_id,symbol,bucket,price,volume
                    ) VALUES(?,?,?,?,0)
                    ON CONFLICT(chat_id,symbol,bucket) DO UPDATE SET
                        price=excluded.price
                    """,
                    (int(chat_id), symbol, bucket, price),
                )
            await conn.commit()

    invest_market._advance_market = advance_with_locked_prices
    investments_app._advance_market = advance_with_locked_prices
    invest_ops._advance_market = advance_with_locked_prices

    original_market_state = admin_market._market_state

    async def market_state_with_locks(core_value: Any, chat_id: int):
        items = await original_market_state(core_value, int(chat_id))
        await _ensure_lock_column(core_value)
        conn = core_value.db._require_connection()
        cursor = await conn.execute(
            "SELECT symbol,price_locked FROM finance_stock_admin_v132 WHERE chat_id=?",
            (int(chat_id),),
        )
        locks = {
            str(row["symbol"]): bool(int(row["price_locked"] or 0))
            for row in await cursor.fetchall()
        }
        for item in items:
            item["price_locked"] = bool(locks.get(str(item["symbol"]), False))
        return items

    admin_market._market_state = market_state_with_locks

    @core.web.middleware
    async def stock_lock_actions(request: Any, handler: Any):
        if (
            request.method.upper() != "POST"
            or str(request.path or "") != "/admin-v132/api/action"
        ):
            return await handler(request)
        try:
            data = await request.json()
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
        action = str(data.get("action") or "")
        symbol = str(data.get("symbol") or "").upper()
        chat_id = admin_market._as_int(data.get("chat_id"))
        if action == "stock_lock":
            try:
                admin_market._auth(core, request)
                if chat_id >= 0 or symbol not in invest_core.STOCKS:
                    raise ValueError("Акция или беседа не найдена.")
                locked = bool(data.get("locked"))
                await _set_lock(core, chat_id, symbol, locked)
                text = f"Курс {symbol} {'заморожен' if locked else 'разблокирован'}."
                return core.web.json_response({"ok": True, "message": text})
            except PermissionError as exc:
                return core.web.json_response(
                    {"ok": False, "reason": str(exc)}, status=403
                )
            except Exception as exc:
                return core.web.json_response(
                    {"ok": False, "reason": str(exc)}, status=400
                )
        if action == "stock_event" and chat_id < 0 and symbol in invest_core.STOCKS:
            await _set_lock(core, chat_id, symbol, False)
        response = await handler(request)
        if (
            action in {"stock_set_price", "stock_reset"}
            and chat_id < 0
            and symbol in invest_core.STOCKS
            and int(getattr(response, "status", 500)) < 400
        ):
            await _set_lock(core, chat_id, symbol, True)
        return response

    previous_application = core.web.Application

    def application_with_stock_locks(*args: Any, **kwargs: Any):
        application = previous_application(*args, **kwargs)
        application.middlewares.insert(0, stock_lock_actions)
        return application

    core.web.Application = application_with_stock_locks