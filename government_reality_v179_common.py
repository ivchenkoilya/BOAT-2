from __future__ import annotations

import json
from typing import Any

VERSION = "Reality 179 · Общая казна, строительство и доверие власти"
DAY = 86_400
WEEK = 7 * DAY
MAX_SQLITE_INTEGER = 9_223_372_036_854_775_807
DIRECT_PROJECT_LIMIT = 1_000_000
MAX_BUILDINGS_PER_TYPE = 3

BUILDINGS: dict[str, dict[str, Any]] = {
    "factory": {
        "emoji": "🏭", "title": "Государственный завод", "cost": 1_000_000,
        "duration": 24 * 3600, "maintenance_bp": 200,
        "sources": ("state_treasury", "event_fund"), "trust": 5,
        "effect": "Ежедневный ограниченный доход казны и поддержка промышленной экономики.",
    },
    "school": {
        "emoji": "🏫", "title": "Государственная школа", "cost": 600_000,
        "duration": 18 * 3600, "maintenance_bp": 100,
        "sources": ("state_treasury", "social_fund", "event_fund"), "trust": 4,
        "effect": "Усиливает образовательные гранты и повышает доверие к власти.",
    },
    "hospital": {
        "emoji": "🏥", "title": "Больница", "cost": 900_000,
        "duration": 24 * 3600, "maintenance_bp": 150,
        "sources": ("state_treasury", "social_fund"), "trust": 5,
        "effect": "Усиливает социальную помощь и снижает ущерб кризисных событий.",
    },
    "housing": {
        "emoji": "🏘", "title": "Жилой комплекс", "cost": 750_000,
        "duration": 20 * 3600, "maintenance_bp": 100,
        "sources": ("social_fund", "event_fund"), "trust": 4,
        "effect": "Снижает часть расходов на содержание имущества и поддерживает субсидии.",
    },
    "state_bank": {
        "emoji": "🏦", "title": "Государственный банк", "cost": 1_500_000,
        "duration": 36 * 3600, "maintenance_bp": 200,
        "sources": ("state_treasury", "finance_ministry"), "trust": 5,
        "effect": "Улучшает государственные вклады и уменьшает часть финансовых комиссий.",
    },
    "police": {
        "emoji": "🚓", "title": "Полицейский участок", "cost": 700_000,
        "duration": 18 * 3600, "maintenance_bp": 150,
        "sources": ("oversight",), "trust": 4,
        "effect": "Усиливает Надзор, добавляет проверку и уменьшает ущерб от краж казны.",
    },
    "power_plant": {
        "emoji": "⚡", "title": "Электростанция", "cost": 2_000_000,
        "duration": 48 * 3600, "maintenance_bp": 250,
        "sources": ("event_fund", "state_treasury"), "trust": 6,
        "effect": "Усиливает заводы и инфраструктурные экономические эффекты.",
    },
    "culture_house": {
        "emoji": "🎭", "title": "Дом культуры", "cost": 500_000,
        "duration": 12 * 3600, "maintenance_bp": 100,
        "sources": ("event_fund",), "trust": 3,
        "effect": "Усиливает фестивали и государственные информационные события.",
    },
    "administration": {
        "emoji": "🏛", "title": "Административный центр", "cost": 1_200_000,
        "duration": 30 * 3600, "maintenance_bp": 150,
        "sources": ("state_treasury",), "trust": 5,
        "effect": "Повышает эффективность отчётности и престиж государственных решений.",
    },
    "science": {
        "emoji": "🔬", "title": "Научный институт", "cost": 1_800_000,
        "duration": 48 * 3600, "maintenance_bp": 200,
        "sources": ("event_fund",), "trust": 6,
        "effect": "Усиливает научные проекты и создаёт дополнительные полезные бонусы.",
    },
}

SOURCE_TITLES = {
    "state_treasury": "🏛 Общая казна",
    "reserve": "🛡 Резервный фонд",
    "social_fund": "🤝 Социальный фонд",
    "oversight": "🛡 Фонд безопасности",
    "election_commission": "🗳 Фонд выборов",
    "event_fund": "🚀 Фонд развития",
    "finance_ministry": "💰 Министерство финансов",
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS government_contribution_requests_v179(
  request_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
  amount INTEGER NOT NULL, fund_key TEXT NOT NULL, result_text TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS government_construction_projects_v179(
  project_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, building_key TEXT NOT NULL,
  initiator_id INTEGER NOT NULL, initiator_office TEXT NOT NULL DEFAULT '',
  source_key TEXT NOT NULL, total_cost INTEGER NOT NULL, funded_amount INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL, request_id TEXT NOT NULL UNIQUE, bill_id TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL, starts_at INTEGER NOT NULL DEFAULT 0,
  completes_at INTEGER NOT NULL DEFAULT 0, cancelled_reason TEXT NOT NULL DEFAULT '',
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_construction_projects_v179_chat
  ON government_construction_projects_v179(chat_id,status,created_at DESC);

CREATE TABLE IF NOT EXISTS government_construction_funding_v179(
  funding_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, chat_id INTEGER NOT NULL,
  source_type TEXT NOT NULL, source_key TEXT NOT NULL DEFAULT '', actor_id INTEGER NOT NULL DEFAULT 0,
  amount INTEGER NOT NULL, request_id TEXT NOT NULL UNIQUE, created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_construction_funding_v179_project
  ON government_construction_funding_v179(project_id,created_at DESC);

CREATE TABLE IF NOT EXISTS government_construction_contributions_v179(
  contribution_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, chat_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL, amount INTEGER NOT NULL, score INTEGER NOT NULL,
  request_id TEXT NOT NULL UNIQUE, created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_construction_contributions_v179_user
  ON government_construction_contributions_v179(chat_id,user_id,created_at DESC);

CREATE TABLE IF NOT EXISTS government_buildings_v179(
  building_id TEXT PRIMARY KEY, project_id TEXT NOT NULL UNIQUE, chat_id INTEGER NOT NULL,
  building_key TEXT NOT NULL, level_no INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'active',
  source_key TEXT NOT NULL, initiator_id INTEGER NOT NULL, completed_at INTEGER NOT NULL,
  next_income_at INTEGER NOT NULL DEFAULT 0, next_maintenance_at INTEGER NOT NULL,
  maintenance_debt INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_buildings_v179_chat
  ON government_buildings_v179(chat_id,building_key,status);

CREATE TABLE IF NOT EXISTS government_building_effects_v179(
  building_id TEXT NOT NULL, effect_key TEXT NOT NULL, value INTEGER NOT NULL,
  active INTEGER NOT NULL DEFAULT 1, updated_at INTEGER NOT NULL,
  PRIMARY KEY(building_id,effect_key)
);
CREATE TABLE IF NOT EXISTS government_building_income_v179(
  building_id TEXT NOT NULL, period_at INTEGER NOT NULL, amount INTEGER NOT NULL,
  created_at INTEGER NOT NULL, PRIMARY KEY(building_id,period_at)
);
CREATE TABLE IF NOT EXISTS government_building_maintenance_v179(
  building_id TEXT NOT NULL, period_at INTEGER NOT NULL, amount INTEGER NOT NULL,
  paid INTEGER NOT NULL DEFAULT 0, source_key TEXT NOT NULL, created_at INTEGER NOT NULL,
  PRIMARY KEY(building_id,period_at)
);
CREATE TABLE IF NOT EXISTS government_building_debts_v179(
  building_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, amount INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS government_construction_scores_v179(
  chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, score INTEGER NOT NULL DEFAULT 0,
  amount INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL,
  PRIMARY KEY(chat_id,user_id)
);
CREATE TABLE IF NOT EXISTS government_construction_log_v179(
  log_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, project_id TEXT NOT NULL DEFAULT '',
  building_id TEXT NOT NULL DEFAULT '', operation_type TEXT NOT NULL, actor_id INTEGER NOT NULL DEFAULT 0,
  amount INTEGER NOT NULL DEFAULT 0, detail TEXT NOT NULL, created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_construction_log_v179_chat
  ON government_construction_log_v179(chat_id,created_at DESC);

CREATE TABLE IF NOT EXISTS government_program_building_bonus_v179(
  run_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, program_key TEXT NOT NULL,
  amount INTEGER NOT NULL, detail TEXT NOT NULL, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS government_property_housing_subsidies_v179(
  property_id TEXT NOT NULL, period_start INTEGER NOT NULL, chat_id INTEGER NOT NULL,
  owner_id INTEGER NOT NULL, amount INTEGER NOT NULL, created_at INTEGER NOT NULL,
  PRIMARY KEY(property_id,period_start)
);

CREATE TABLE IF NOT EXISTS government_trust_events_v179(
  event_key TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
  delta INTEGER NOT NULL, reason TEXT NOT NULL, source TEXT NOT NULL,
  actor_id INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS government_trust_state_v179(
  chat_id INTEGER PRIMARY KEY, overall_trust INTEGER NOT NULL DEFAULT 50,
  last_recalc_at INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL
);
"""


def clamp_trust(value: int) -> int:
    return max(0, min(100, int(value)))


def json_load(value: Any, default: Any) -> Any:
    try:
        parsed = json.loads(str(value or ""))
        return parsed if isinstance(parsed, type(default)) else default
    except Exception:
        return default


def score_title(score: int) -> str:
    value = max(0, int(score))
    if value >= 25_000:
        return "Великий созидатель"
    if value >= 10_000:
        return "Строитель Реальности"
    if value >= 4_000:
        return "Архитектор государства"
    if value >= 1_000:
        return "Меценат района"
    return "Помощник стройки"


async def ensure_schema(core: Any) -> None:
    if getattr(core, "_government_reality_v179_schema_ready", False):
        return
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.executescript(SCHEMA_SQL)
        await conn.commit()
    core._government_reality_v179_schema_ready = True
