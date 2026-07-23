from __future__ import annotations

import html
import json
import math
import secrets
from typing import Any

import finance_investments_v127_core as investment_core
import finance_investments_v127_market as investment_market
import government_institutions_v128 as institutions
import government_oversight_deputy_v167_data as oversight_data
import government_treasury_management_v164 as treasury
import government_v127 as gov

VERSION = "Reality 176 · Госпрограммы и имущество чиновников"
DAY = 86_400
WEEK = 7 * DAY

PROGRAMS: dict[str, dict[str, Any]] = {
    "anti_crisis": {
        "emoji": "🛡",
        "title": "Антикризисный пакет",
        "fund_key": "reserve",
        "duration": 12 * 3600,
        "cooldown": 12 * 3600,
        "roles": {"president", "finance", "central_bank", "security"},
        "cost_mode": "reserve_10pct",
        "min_cost": 5_000,
        "max_cost": 100_000,
        "effect": "Смягчает отрицательное минутное движение акций на 40%, но не гарантирует рост.",
    },
    "festival": {
        "emoji": "🎪",
        "title": "Государственный фестиваль",
        "fund_key": "event_fund",
        "duration": DAY,
        "cooldown": DAY,
        "roles": {"president", "press", "security"},
        "cost_mode": "manual",
        "min_cost": 10_000,
        "max_cost": 1_000_000,
        "effect": "Запускает общее событие и распределяет 80% бюджета между пятью активными участниками.",
    },
    "social_help": {
        "emoji": "🤝",
        "title": "Социальная помощь",
        "fund_key": "social_fund",
        "duration": 0,
        "cooldown": 12 * 3600,
        "roles": {"president", "finance", "ombudsman"},
        "cost_mode": "manual",
        "min_cost": 3_000,
        "max_cost": 1_000_000,
        "effect": "Распределяет бюджет между 3–5 участниками с наименьшим обычным влиянием.",
    },
    "oversight_operation": {
        "emoji": "🚨",
        "title": "Операция Надзора",
        "fund_key": "oversight",
        "duration": DAY,
        "cooldown": DAY,
        "roles": {"oversight", "oversight_deputy"},
        "cost_mode": "manual",
        "min_cost": 3_000,
        "max_cost": 250_000,
        "effect": "Даёт руководству Надзора одну дополнительную проверку и расширенный отчёт.",
    },
    "market_intervention": {
        "emoji": "💰",
        "title": "Финансовая интервенция",
        "fund_key": "finance_ministry",
        "duration": 0,
        "cooldown": 12 * 3600,
        "roles": {"president", "finance", "central_bank"},
        "cost_mode": "manual",
        "min_cost": 5_000,
        "max_cost": 250_000,
        "effect": "Создаёт ограниченный разовый импульс выбранной акции без гарантии дальнейшего роста.",
    },
    "election_campaign": {
        "emoji": "🗳",
        "title": "Государственная избирательная кампания",
        "fund_key": "election_commission",
        "duration": DAY,
        "cooldown": DAY,
        "roles": {"president", "chair", "cec"},
        "cost_mode": "manual",
        "min_cost": 5_000,
        "max_cost": 250_000,
        "effect": "Повышает видимость активных выборов и выдаёт награду за участие, не меняя голоса.",
    },
}

PROPERTY_ITEMS: dict[str, dict[str, Any]] = {
    "business_sedan": {"emoji": "🚘", "title": "Бизнес-седан", "price": 50_000, "level": 1, "maintenance_bp": 100},
    "sports_car": {"emoji": "🏎", "title": "Спорткар", "price": 150_000, "level": 1, "maintenance_bp": 100},
    "armored_suv": {"emoji": "🚙", "title": "Бронированный внедорожник", "price": 300_000, "level": 2, "maintenance_bp": 100},
    "elite_apartment": {"emoji": "🏢", "title": "Элитная квартира", "price": 500_000, "level": 1, "maintenance_bp": 150},
    "yacht": {"emoji": "🛥", "title": "Яхта", "price": 1_000_000, "level": 2, "maintenance_bp": 200},
    "mansion": {"emoji": "🏰", "title": "Особняк", "price": 1_500_000, "level": 2, "maintenance_bp": 150},
    "helicopter": {"emoji": "🚁", "title": "Вертолёт", "price": 2_000_000, "level": 3, "maintenance_bp": 200},
    "private_jet": {"emoji": "✈️", "title": "Частный самолёт", "price": 5_000_000, "level": 4, "maintenance_bp": 300},
    "mega_yacht": {"emoji": "🛳", "title": "Мегаяхта", "price": 10_000_000, "level": 4, "maintenance_bp": 300},
    "palace": {"emoji": "🏛", "title": "Дворец", "price": 25_000_000, "level": 4, "maintenance_bp": 300},
}

OFFICE_LEVELS = {
    "deputy": 1,
    "chair": 2,
    "finance": 2,
    "central_bank": 2,
    "auditor": 2,
    "cec": 2,
    "ombudsman": 2,
    "press": 2,
    "oversight_deputy": 2,
    "oversight": 3,
    "security": 3,
    "prosecutor": 3,
    "supreme_court": 3,
    "president": 4,
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS government_programs_v176(
    run_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, program_key TEXT NOT NULL,
    fund_key TEXT NOT NULL, cost INTEGER NOT NULL, actor_id INTEGER NOT NULL,
    status TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}',
    started_at INTEGER NOT NULL, ends_at INTEGER NOT NULL DEFAULT 0,
    cooldown_until INTEGER NOT NULL, resolved_at INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_government_programs_v176_chat
    ON government_programs_v176(chat_id,program_key,started_at DESC);
CREATE TABLE IF NOT EXISTS government_program_effects_v176(
    effect_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, effect_key TEXT NOT NULL,
    source_run_id TEXT NOT NULL, value INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL DEFAULT '{}', starts_at INTEGER NOT NULL,
    ends_at INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1,
    UNIQUE(chat_id,effect_key,source_run_id)
);
CREATE INDEX IF NOT EXISTS idx_government_program_effects_v176_active
    ON government_program_effects_v176(chat_id,effect_key,active,ends_at);
CREATE TABLE IF NOT EXISTS government_property_v176(
    property_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, owner_id INTEGER NOT NULL,
    item_key TEXT NOT NULL, purchase_price INTEGER NOT NULL, luxury_tax INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'owned', purchased_at INTEGER NOT NULL,
    next_maintenance_at INTEGER NOT NULL, debt INTEGER NOT NULL DEFAULT 0,
    seizure_until INTEGER NOT NULL DEFAULT 0, source_auction_id TEXT NOT NULL DEFAULT '',
    confiscated_by INTEGER NOT NULL DEFAULT 0, confiscated_at INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL, UNIQUE(chat_id,owner_id,item_key)
);
CREATE INDEX IF NOT EXISTS idx_government_property_v176_owner
    ON government_property_v176(chat_id,owner_id,status);
CREATE TABLE IF NOT EXISTS government_property_maintenance_v176(
    charge_id TEXT PRIMARY KEY, property_id TEXT NOT NULL, chat_id INTEGER NOT NULL,
    owner_id INTEGER NOT NULL, period_start INTEGER NOT NULL, amount INTEGER NOT NULL,
    paid INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL, created_at INTEGER NOT NULL,
    paid_at INTEGER NOT NULL DEFAULT 0, UNIQUE(property_id,period_start)
);
CREATE TABLE IF NOT EXISTS government_property_debts_v176(
    property_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, owner_id INTEGER NOT NULL,
    amount INTEGER NOT NULL, updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS government_property_declarations_v176(
    declaration_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
    balance INTEGER NOT NULL, total_value INTEGER NOT NULL, luxury_tax_paid INTEGER NOT NULL,
    maintenance_paid INTEGER NOT NULL, seized_count INTEGER NOT NULL,
    snapshot_json TEXT NOT NULL, created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_government_property_declarations_v176
    ON government_property_declarations_v176(chat_id,user_id,created_at DESC);
CREATE TABLE IF NOT EXISTS government_property_investigations_v176(
    investigation_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, target_user_id INTEGER NOT NULL,
    property_id TEXT NOT NULL DEFAULT '', reason TEXT NOT NULL, status TEXT NOT NULL,
    action_key TEXT NOT NULL DEFAULT '', result TEXT NOT NULL DEFAULT '',
    bill_id TEXT NOT NULL DEFAULT '', created_by INTEGER NOT NULL,
    created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, resolved_at INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_government_property_investigations_v176
    ON government_property_investigations_v176(chat_id,status,updated_at DESC);
CREATE TABLE IF NOT EXISTS government_property_auctions_v176(
    auction_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, property_id TEXT NOT NULL UNIQUE,
    former_owner_id INTEGER NOT NULL, start_price INTEGER NOT NULL, current_price INTEGER NOT NULL DEFAULT 0,
    current_bidder_id INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL,
    started_at INTEGER NOT NULL, ends_at INTEGER NOT NULL, resolved_at INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_government_property_auctions_v176
    ON government_property_auctions_v176(chat_id,status,ends_at);
CREATE TABLE IF NOT EXISTS government_property_bids_v176(
    bid_id TEXT PRIMARY KEY, auction_id TEXT NOT NULL, bidder_id INTEGER NOT NULL,
    amount INTEGER NOT NULL, created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_government_property_bids_v176
    ON government_property_bids_v176(auction_id,created_at DESC);
CREATE TABLE IF NOT EXISTS government_property_operations_v176(
    operation_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, actor_id INTEGER NOT NULL,
    target_user_id INTEGER NOT NULL DEFAULT 0, operation_type TEXT NOT NULL,
    amount INTEGER NOT NULL DEFAULT 0, property_id TEXT NOT NULL DEFAULT '',
    program_run_id TEXT NOT NULL DEFAULT '', detail TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}', created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_government_property_operations_v176
    ON government_property_operations_v176(chat_id,created_at DESC);
"""


def _json(value: Any, default: Any) -> Any:
    if isinstance(value, type(default)):
        return value
    try:
        parsed = json.loads(str(value or ""))
        return parsed if isinstance(parsed, type(default)) else default
    except Exception:
        return default


def _fmt(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _office_level(offices: list[str]) -> int:
    return max((OFFICE_LEVELS.get(str(key), 0) for key in offices), default=0)


def _program_cost(program_key: str, balance: int, requested: int = 0) -> int:
    spec = PROGRAMS[program_key]
    if spec["cost_mode"] == "reserve_10pct":
        return max(int(spec["min_cost"]), min(int(spec["max_cost"]), int(balance) // 10))
    return max(int(spec["min_cost"]), min(int(spec["max_cost"]), int(requested)))


async def ensure_schema(core: Any) -> None:
    if getattr(core, "_government_programs_property_v176_schema_ready", False):
        return
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.executescript(SCHEMA_SQL)
        await conn.commit()
    core._government_programs_property_v176_schema_ready = True


async def _operation(
    core: Any,
    chat_id: int,
    actor_id: int,
    operation_type: str,
    detail: str,
    *,
    target_user_id: int = 0,
    amount: int = 0,
    property_id: str = "",
    program_run_id: str = "",
    payload: dict[str, Any] | None = None,
) -> str:
    operation_id = secrets.token_urlsafe(12)
    conn = core.db._require_connection()
    await conn.execute(
        """
        INSERT INTO government_property_operations_v176(
          operation_id,chat_id,actor_id,target_user_id,operation_type,amount,
          property_id,program_run_id,detail,payload_json,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            operation_id, int(chat_id), int(actor_id), int(target_user_id), str(operation_type),
            int(amount), str(property_id), str(program_run_id), str(detail),
            json.dumps(payload or {}, ensure_ascii=False), gov._now(),
        ),
    )
    return operation_id


async def _active_effect(core: Any, chat_id: int, effect_key: str) -> Any | None:
    await ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT * FROM government_program_effects_v176
        WHERE chat_id=? AND effect_key=? AND active=1 AND ends_at>?
        ORDER BY ends_at DESC LIMIT 1
        """,
        (int(chat_id), str(effect_key), gov._now()),
    )
    return await cursor.fetchone()


async def oversight_bonus(core: Any, chat_id: int) -> int:
    row = await _active_effect(core, chat_id, "oversight_operation")
    return max(0, int(row["value"] or 0)) if row else 0

