from __future__ import annotations

import hashlib
import math
import secrets
import time
from pathlib import Path
from typing import Any



VERSION = "Reality 127 · Вклады и биржа"
APP_DIR = Path(__file__).resolve().parent / "financeapp_v127"
MARKET_TICK_SECONDS = 5 * 60
MARKET_HISTORY_SECONDS = 30 * 24 * 60 * 60
TRADE_FEE_PERCENT = 1
MAX_ACTIVE_DEPOSITS = 5
MAX_DEPOSIT_TOTAL = 50_000
MAX_TRADE_VALUE = 50_000

DEPOSIT_PLANS: dict[str, dict[str, Any]] = {
    "flex": {
        "title": "Гибкий",
        "term_days": 30,
        "yield_percent": 9.0,
        "daily_percent": 0.3,
        "early": "allowed",
        "early_note": "Можно снять в любой момент. Процент начисляется за фактическое время, максимум 30 дней.",
    },
    "safe7": {
        "title": "Надёжный",
        "term_days": 7,
        "yield_percent": 4.0,
        "early": "interest_lost",
        "early_note": "При досрочном снятии возвращается только сумма вклада.",
    },
    "premium14": {
        "title": "Премиальный",
        "term_days": 14,
        "yield_percent": 10.0,
        "early": "penalty_3",
        "early_note": "При досрочном снятии удерживается 3% от суммы вклада.",
    },
    "capital30": {
        "title": "Главный капитал",
        "term_days": 30,
        "yield_percent": 25.0,
        "early": "locked",
        "early_note": "Досрочное снятие недоступно.",
    },
}

STOCKS: dict[str, dict[str, Any]] = {
    "EGO": {
        "name": "EGO Corp",
        "icon": "👑",
        "base_price": 120,
        "volatility_bp": 25,
        "drift_bp": 1,
        "risk": "Низкий",
        "description": "Стабильная корпорация влияния и репутации.",
    },
    "HERO": {
        "name": "Hero Energy",
        "icon": "⚡",
        "base_price": 86,
        "volatility_bp": 42,
        "drift_bp": 2,
        "risk": "Средний",
        "description": "Энергетика Главных героев. Умеренный риск.",
    },
    "NPC": {
        "name": "NPC Industries",
        "icon": "🎭",
        "base_price": 34,
        "volatility_bp": 58,
        "drift_bp": 0,
        "risk": "Высокий",
        "description": "Дешёвая акция массовки с резкими движениями.",
    },
    "CORV": {
        "name": "Corvus Technologies",
        "icon": "🐦‍⬛",
        "base_price": 210,
        "volatility_bp": 74,
        "drift_bp": 3,
        "risk": "Высокий",
        "description": "Игровые технологии и рискованные разработки.",
    },
    "CENTER": {
        "name": "Центр Вселенной",
        "icon": "🌌",
        "base_price": 305,
        "volatility_bp": 95,
        "drift_bp": -1,
        "risk": "Экстремальный",
        "description": "Самая непредсказуемая акция рынка.",
    },
}

EVENTS_UP = (
    "Компания объявила рекордный сезон",
    "Инвесторы поддержали новую стратегию",
    "Проект выиграл битву за внимание",
    "Спрос на акции резко вырос",
)
EVENTS_DOWN = (
    "Рынок усомнился в громком обещании",
    "Компания потеряла часть аудитории",
    "Неудачное событие ударило по репутации",
    "Крупный инвестор сократил позицию",
)


def _now() -> int:
    return int(time.time())


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _fmt(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _chat_id(start_param: str | None, request: Any, data: dict[str, Any]) -> int:
    raw = str(start_param or data.get("chat_id") or request.query.get("chat_id") or "").strip()
    if raw.startswith("finance_"):
        raw = raw[8:]
    try:
        chat_id = int(raw)
    except (TypeError, ValueError):
        raise ValueError("Не найдена беседа для инвестиционной операции.")
    if chat_id >= 0:
        raise ValueError("Вклады и акции работают только внутри групповой беседы.")
    return chat_id


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


def _hash_numbers(chat_id: int, symbol: str, bucket: int) -> tuple[float, float, int]:
    digest = hashlib.sha256(f"{chat_id}:{symbol}:{bucket}:reality127".encode()).digest()
    first = int.from_bytes(digest[:8], "big") / (2**64 - 1)
    second = int.from_bytes(digest[8:16], "big") / (2**64 - 1)
    selector = int.from_bytes(digest[16:20], "big")
    return first, second, selector


def _deposit_values(row: Any, now: int) -> tuple[int, int, bool, bool]:
    plan = DEPOSIT_PLANS[str(row["plan_key"])]
    principal = int(row["principal"])
    started_at = int(row["started_at"])
    matures_at = int(row["matures_at"])
    matured = now >= matures_at
    if str(row["plan_key"]) == "flex":
        elapsed = min(max(0, now - started_at), int(plan["term_days"]) * 86400)
        interest = math.floor(principal * float(plan["daily_percent"]) / 100 * elapsed / 86400)
        payout = principal + interest
        can_withdraw = True
    else:
        payout = math.floor(principal * (100 + float(plan["yield_percent"])) / 100) if matured else principal
        can_withdraw = matured or str(plan["early"]) != "locked"
    return payout, max(0, payout - principal), matured, can_withdraw


async def _ensure_schema(core: Any) -> None:
    if getattr(core, "_finance_investments_schema_v127_ready", False):
        return
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS finance_deposits_v127(
                deposit_id TEXT PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                plan_key TEXT NOT NULL,
                principal INTEGER NOT NULL,
                started_at INTEGER NOT NULL,
                matures_at INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                payout INTEGER,
                completed_at INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_finance_deposits_user_v127
            ON finance_deposits_v127(chat_id,user_id,status,started_at);

            CREATE TABLE IF NOT EXISTS finance_market_v127(
                chat_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                price INTEGER NOT NULL,
                previous_price INTEGER NOT NULL,
                open_price INTEGER NOT NULL,
                high_price INTEGER NOT NULL,
                low_price INTEGER NOT NULL,
                volume INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                last_event TEXT NOT NULL DEFAULT '',
                last_event_at INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(chat_id,symbol)
            );
            CREATE TABLE IF NOT EXISTS finance_stock_history_v127(
                chat_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                bucket INTEGER NOT NULL,
                price INTEGER NOT NULL,
                PRIMARY KEY(chat_id,symbol,bucket)
            );
            CREATE INDEX IF NOT EXISTS idx_finance_stock_history_v127
            ON finance_stock_history_v127(chat_id,symbol,bucket);

            CREATE TABLE IF NOT EXISTS finance_stock_positions_v127(
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                total_cost INTEGER NOT NULL,
                realized_profit INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY(chat_id,user_id,symbol)
            );
            CREATE TABLE IF NOT EXISTS finance_stock_trades_v127(
                trade_id TEXT PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price INTEGER NOT NULL,
                gross INTEGER NOT NULL,
                fee INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_finance_stock_trades_user_v127
            ON finance_stock_trades_v127(chat_id,user_id,created_at);
            """
        )
        await conn.commit()
    core._finance_investments_schema_v127_ready = True
