from __future__ import annotations

import json
import secrets
from typing import Any

import government_programs_property_v176_common as v176
import government_treasury_management_v164 as treasury
import government_v127 as gov

VERSION = "Reality 177 · Государственные программы, рейтинг власти и имущество"
DAY = 86_400
WEEK = 7 * DAY
RATING_VOTE_COOLDOWN = DAY

# Reality 177 is the canonical catalogue used by both the API and the UI.
# Existing completed runs keep their stored cost in government_programs_v176.
PROGRAMS: dict[str, dict[str, Any]] = {
    "anti_crisis": {
        **v176.PROGRAMS["anti_crisis"],
        "min_cost": 20_000,
        "max_cost": 400_000,
        "base_min_cost": 5_000,
        "base_max_cost": 100_000,
        "cost_mode": "reserve_10pct_x4",
    },
    "festival": {**v176.PROGRAMS["festival"], "min_cost": 40_000, "max_cost": 4_000_000},
    "social_help": {**v176.PROGRAMS["social_help"], "min_cost": 12_000, "max_cost": 4_000_000},
    "oversight_operation": {**v176.PROGRAMS["oversight_operation"], "min_cost": 12_000, "max_cost": 1_000_000},
    "market_intervention": {**v176.PROGRAMS["market_intervention"], "min_cost": 20_000, "max_cost": 1_000_000},
    "election_campaign": {**v176.PROGRAMS["election_campaign"], "min_cost": 20_000, "max_cost": 1_000_000},
    "infrastructure": {
        "emoji": "🏗", "title": "Модернизация инфраструктуры", "fund_key": "event_fund",
        "duration": DAY, "cooldown": DAY, "roles": {"president", "finance"},
        "cost_mode": "manual", "min_cost": 60_000, "max_cost": 2_000_000,
        "effect": "На 24 часа увеличивает государственные налоговые поступления на 15%.",
    },
    "education_grants": {
        "emoji": "🎓", "title": "Образовательные гранты", "fund_key": "social_fund",
        "duration": 0, "cooldown": DAY, "roles": {"president", "ombudsman", "finance"},
        "cost_mode": "manual", "min_cost": 40_000, "max_cost": 2_000_000,
        "effect": "Распределяет гранты между участниками с небольшим карьерным влиянием.",
    },
    "emergency_social": {
        "emoji": "🏥", "title": "Экстренная социальная поддержка", "fund_key": "social_fund",
        "duration": 0, "cooldown": 12 * 3600, "roles": {"president", "ombudsman"},
        "cost_mode": "manual", "min_cost": 32_000, "max_cost": 1_500_000,
        "effect": "Выдаёт адресную помощь участникам с минимальным обычным балансом.",
    },
    "cyber_defense": {
        "emoji": "🛡", "title": "Киберзащита казны", "fund_key": "oversight",
        "duration": DAY, "cooldown": DAY, "roles": {"president", "security", "oversight"},
        "cost_mode": "manual", "min_cost": 80_000, "max_cost": 2_000_000,
        "effect": "На 24 часа компенсирует 50% подтверждённых потерь казны от краж и опасных событий.",
    },
    "anti_corruption_audit": {
        "emoji": "🔎", "title": "Антикоррупционный аудит", "fund_key": "oversight",
        "duration": DAY, "cooldown": DAY, "roles": {"oversight", "oversight_deputy", "prosecutor", "auditor"},
        "cost_mode": "manual", "min_cost": 48_000, "max_cost": 1_000_000,
        "effect": "Анализирует крупные операции, открывает аудит и даёт дополнительную проверку Надзора.",
    },
    "economy_support": {
        "emoji": "🏭", "title": "Поддержка экономики", "fund_key": "finance_ministry",
        "duration": 12 * 3600, "cooldown": 12 * 3600, "roles": {"president", "finance", "central_bank"},
        "cost_mode": "manual", "min_cost": 100_000, "max_cost": 3_000_000,
        "effect": "Создаёт ограниченный диверсифицированный импульс рынку без гарантии дальнейшего роста.",
    },
    "information_campaign": {
        "emoji": "📢", "title": "Государственная информационная кампания", "fund_key": "event_fund",
        "duration": DAY, "cooldown": DAY, "roles": {"president", "press"},
        "cost_mode": "manual", "min_cost": 40_000, "max_cost": 1_000_000,
        "effect": "Запускает публичную кампанию и временно повышает рейтинг её инициатора.",
    },
    "emergency_mode": {
        "emoji": "🚑", "title": "Режим чрезвычайной ситуации", "fund_key": "reserve",
        "duration": 12 * 3600, "cooldown": DAY, "roles": {"president", "security"},
        "cost_mode": "manual", "min_cost": 120_000, "max_cost": 3_000_000,
        "effect": "Включает защитный режим и открывает одно экстренное пополнение свободной казны.",
    },
    "science_project": {
        "emoji": "🧪", "title": "Государственный научный проект", "fund_key": "event_fund",
        "duration": 12 * 3600, "cooldown": DAY, "roles": {"president", "chair", "deputy", "finance"},
        "cost_mode": "manual", "min_cost": 80_000, "max_cost": 2_000_000,
        "effect": "Через 12 часов создаёт один случайный полезный государственный бонус.",
    },
    "housing_subsidy": {
        "emoji": "🏘", "title": "Жилищная субсидия", "fund_key": "social_fund",
        "duration": 0, "cooldown": DAY, "roles": {"president", "finance", "ombudsman"},
        "cost_mode": "manual", "min_cost": 40_000, "max_cost": 2_000_000,
        "effect": "Погашает задолженность по содержанию имущества выбранного участника.",
    },
}

LEGACY_TO_STRUCTURE = {
    "reserve": "reserve",
    "social": "social_fund",
    "security": "oversight",
    "elections": "election_commission",
    "development": "event_fund",
    "general": "finance_ministry",
}

ROLE_NAMES = {
    "president": "Президент реальности", "chair": "Председатель Госдумы",
    "deputy": "Депутат Госдумы", "finance": "Министр финансов",
    "oversight": "Глава государственного надзора", "oversight_deputy": "Заместитель главы Надзора",
    "central_bank": "Глава Центрального банка", "auditor": "Глава Счётной палаты",
    "cec": "Председатель ЦИК", "ombudsman": "Омбудсмен", "press": "Пресс-секретарь",
    "security": "Секретарь Совбеза", "prosecutor": "Генеральный прокурор",
    "supreme_court": "Председатель Верховного суда",
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS government_fund_migrations_v177(
  chat_id INTEGER NOT NULL, legacy_key TEXT NOT NULL, structure_key TEXT NOT NULL,
  amount INTEGER NOT NULL, migrated_at INTEGER NOT NULL,
  PRIMARY KEY(chat_id,legacy_key)
);
CREATE TABLE IF NOT EXISTS government_program_requests_v177(
  request_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, actor_id INTEGER NOT NULL,
  program_key TEXT NOT NULL, run_id TEXT NOT NULL, result_text TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS government_program_publications_v177(
  run_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, text TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT NOT NULL DEFAULT '', updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS government_program_effects_v177(
  effect_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, effect_key TEXT NOT NULL,
  source_run_id TEXT NOT NULL, value INTEGER NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL DEFAULT '{}', starts_at INTEGER NOT NULL,
  ends_at INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1,
  UNIQUE(chat_id,effect_key,source_run_id)
);
CREATE INDEX IF NOT EXISTS idx_program_effects_v177_active
  ON government_program_effects_v177(chat_id,effect_key,active,ends_at);
CREATE TABLE IF NOT EXISTS government_official_rating_votes_v177(
  vote_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, voter_id INTEGER NOT NULL,
  target_user_id INTEGER NOT NULL, office_key TEXT NOT NULL, seat_no INTEGER NOT NULL,
  office_starts_at INTEGER NOT NULL, value INTEGER NOT NULL, created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rating_votes_v177_recent
  ON government_official_rating_votes_v177(chat_id,voter_id,target_user_id,created_at DESC);
CREATE TABLE IF NOT EXISTS government_official_rating_log_v177(
  log_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
  office_key TEXT NOT NULL, seat_no INTEGER NOT NULL, office_starts_at INTEGER NOT NULL,
  delta INTEGER NOT NULL, rating_after INTEGER NOT NULL, reason TEXT NOT NULL,
  source TEXT NOT NULL, actor_id INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rating_log_v177_user
  ON government_official_rating_log_v177(chat_id,user_id,created_at DESC);
CREATE TABLE IF NOT EXISTS government_official_terms_v177(
  chat_id INTEGER NOT NULL, office_key TEXT NOT NULL, seat_no INTEGER NOT NULL,
  user_id INTEGER NOT NULL, starts_at INTEGER NOT NULL, ends_at INTEGER NOT NULL,
  final_rating INTEGER NOT NULL, archived_at INTEGER NOT NULL,
  PRIMARY KEY(chat_id,office_key,seat_no,starts_at)
);
CREATE TABLE IF NOT EXISTS government_property_meta_v177(
  property_id TEXT PRIMARY KEY, upgrade_level INTEGER NOT NULL DEFAULT 0,
  insurance_until INTEGER NOT NULL DEFAULT 0, insurance_used INTEGER NOT NULL DEFAULT 0,
  is_primary INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS government_voluntary_auctions_v177(
  auction_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, property_id TEXT NOT NULL UNIQUE,
  seller_id INTEGER NOT NULL, start_price INTEGER NOT NULL, current_price INTEGER NOT NULL DEFAULT 0,
  current_bidder_id INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL,
  started_at INTEGER NOT NULL, ends_at INTEGER NOT NULL, resolved_at INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_voluntary_auctions_v177_active
  ON government_voluntary_auctions_v177(chat_id,status,ends_at);
CREATE TABLE IF NOT EXISTS government_voluntary_bids_v177(
  bid_id TEXT PRIMARY KEY, auction_id TEXT NOT NULL, bidder_id INTEGER NOT NULL,
  amount INTEGER NOT NULL, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS government_property_action_requests_v177(
  request_id TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, actor_id INTEGER NOT NULL,
  action TEXT NOT NULL, property_id TEXT NOT NULL, result_text TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
"""


def fmt(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def json_value(value: Any, default: Any) -> Any:
    if isinstance(value, type(default)):
        return value
    try:
        parsed = json.loads(str(value or ""))
        return parsed if isinstance(parsed, type(default)) else default
    except Exception:
        return default


def program_cost(program_key: str, balance: int, requested: int = 0) -> int:
    spec = PROGRAMS[program_key]
    if spec["cost_mode"] == "reserve_10pct_x4":
        base = max(int(spec["base_min_cost"]), min(int(spec["base_max_cost"]), max(0, int(balance)) // 10))
        return base * 4
    return max(int(spec["min_cost"]), min(int(spec["max_cost"]), int(requested or spec["min_cost"])))


def role_label(offices: list[str]) -> str:
    return " · ".join(ROLE_NAMES.get(key, key) for key in offices) or "Государственный служащий"


async def ensure_schema(core: Any) -> None:
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.executescript(SCHEMA_SQL)
        await conn.commit()


async def operation(core: Any, chat_id: int, actor_id: int, action: str, detail: str, *, amount: int = 0, property_id: str = "", run_id: str = "", target_user_id: int = 0, payload: dict[str, Any] | None = None) -> str:
    operation_id = secrets.token_urlsafe(12)
    conn = core.db._require_connection()
    await conn.execute(
        """INSERT INTO government_property_operations_v176(
        operation_id,chat_id,actor_id,target_user_id,operation_type,amount,property_id,
        program_run_id,detail,payload_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (operation_id, int(chat_id), int(actor_id), int(target_user_id), str(action), int(amount),
         str(property_id), str(run_id), str(detail), json.dumps(payload or {}, ensure_ascii=False), gov._now()),
    )
    return operation_id
