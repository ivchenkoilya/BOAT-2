from __future__ import annotations

from typing import Any

import finance_investments_v127 as finance_app
import finance_investments_v127_core as investment_core
import finance_investments_v127_market as investment_market
import finance_investments_v127_ops as investment_ops

from finance_fund_link_v167_data import (
    VERSION, STRUCTURE_TITLES, FUND_EFFECT_SECONDS,
    _apply_fund_effect, _deposit_values_with_funds, _ensure_schema, _fund_snapshot,
)

def install_finance_fund_link_v167(core: Any) -> None:
    if getattr(core, "_finance_fund_link_v167_installed", False):
        return
    core._finance_fund_link_v167_installed = True
    core.FINANCE_SYSTEM_VERSION = VERSION

    original_connect = core.Database.connect

    async def connect_with_fund_link(self: Any) -> None:
        await original_connect(self)
        core._finance_fund_link_schema_v167_ready = False
        await _ensure_schema(core)

    core.Database.connect = connect_with_fund_link

    original_advance = investment_market._advance_market

    async def advance_market_with_funds(core_arg: Any, chat_id: int) -> None:
        await original_advance(core_arg, chat_id)
        await _apply_fund_effect(core_arg, chat_id)

    original_create_deposit = investment_ops._create_deposit

    async def create_deposit_with_fund_rate(
        core_arg: Any,
        chat_id: int,
        user_id: int,
        data: dict[str, Any],
    ) -> str:
        snapshot = await _fund_snapshot(core_arg, chat_id)
        message = await original_create_deposit(core_arg, chat_id, user_id, data)
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT deposit_id FROM finance_deposits_v127
            WHERE chat_id=? AND user_id=? AND status='active'
            ORDER BY started_at DESC,deposit_id DESC LIMIT 1
            """,
            (int(chat_id), int(user_id)),
        )
        row = await cursor.fetchone()
        if row is not None:
            await conn.execute(
                """
                UPDATE finance_deposits_v127
                SET yield_multiplier_bp=?,fund_index_at_open=?
                WHERE deposit_id=?
                """,
                (
                    int(snapshot["deposit_multiplier_bp"]),
                    int(snapshot["fund_index"]),
                    str(row["deposit_id"]),
                ),
            )
            await conn.commit()
        percent = (int(snapshot["deposit_multiplier_bp"]) - 10_000) / 100
        return (
            f"{message} Ставка зафиксирована по индексу фондов "
            f"{snapshot['fund_index']}/100 ({percent:+.0f}% к базовой доходности)."
        )

    original_payload = investment_market._investment_payload

    async def investment_payload_with_funds(
        core_arg: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        payload = await original_payload(core_arg, chat_id, user_id)
        snapshot = await _fund_snapshot(core_arg, chat_id)
        multiplier = int(snapshot["deposit_multiplier_bp"]) / 10_000
        for plan in payload.get("plans", []):
            base_yield = float(
                investment_core.DEPOSIT_PLANS.get(str(plan.get("key")), {}).get(
                    "yield_percent", plan.get("yield_percent", 0)
                )
            )
            base_daily = float(
                investment_core.DEPOSIT_PLANS.get(str(plan.get("key")), {}).get(
                    "daily_percent", plan.get("daily_percent", 0)
                )
            )
            plan["base_yield_percent"] = base_yield
            plan["base_daily_percent"] = base_daily
            plan["yield_percent"] = round(base_yield * multiplier, 2)
            plan["daily_percent"] = round(base_daily * multiplier, 3)
            plan["fund_multiplier_bp"] = int(snapshot["deposit_multiplier_bp"])
            plan["fund_index"] = int(snapshot["fund_index"])

        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT deposit_id,yield_multiplier_bp,fund_index_at_open
            FROM finance_deposits_v127
            WHERE chat_id=? AND user_id=? AND status='active'
            """,
            (int(chat_id), int(user_id)),
        )
        deposit_rates = {
            str(row["deposit_id"]): {
                "yield_multiplier_bp": int(row["yield_multiplier_bp"] or 10_000),
                "fund_index_at_open": int(row["fund_index_at_open"] or 0),
            }
            for row in await cursor.fetchall()
        }
        for deposit in payload.get("deposits", []):
            rate = deposit_rates.get(str(deposit.get("deposit_id")), {})
            deposit.update(rate)
            deposit["yield_multiplier_percent"] = round(
                (int(rate.get("yield_multiplier_bp", 10_000)) - 10_000) / 100,
                2,
            )

        for stock in payload.get("stocks", []):
            symbol = str(stock.get("symbol") or "")
            support = snapshot["stock_support"].get(symbol, {})
            stock["fund_support"] = support
            stock["fund_effect_bp"] = int(support.get("effect_bp", 0))
            stock["fund_effect_percent"] = round(int(support.get("effect_bp", 0)) / 100, 2)

        payload["version"] = VERSION
        payload["fund_economy_v167"] = {
            **snapshot,
            "structure_titles": STRUCTURE_TITLES,
            "effect_interval_seconds": FUND_EFFECT_SECONDS,
            "deposit_rate_note": (
                "Ставка фиксируется при открытии вклада. Она зависит от капитала "
                "государственных фондов, активных вкладов и биржевого капитала беседы."
            ),
            "stock_rate_note": (
                "Раз в час профильные фонды создают дополнительный импульс акциям. "
                "Пополнения фондов за последние 24 часа усиливают эффект."
            ),
        }
        return payload

    investment_core._deposit_values = _deposit_values_with_funds
    investment_market._deposit_values = _deposit_values_with_funds
    investment_ops._deposit_values = _deposit_values_with_funds

    investment_market._advance_market = advance_market_with_funds
    investment_ops._advance_market = advance_market_with_funds
    finance_app._advance_market = advance_market_with_funds

    investment_ops._create_deposit = create_deposit_with_fund_rate
    finance_app._create_deposit = create_deposit_with_fund_rate

    investment_market._investment_payload = investment_payload_with_funds
    finance_app._investment_payload = investment_payload_with_funds
