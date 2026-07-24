from __future__ import annotations

from typing import Any

VERSION = "Reality 180 · Карта государства"

DISTRICTS: dict[str, dict[str, str]] = {
    "government": {
        "emoji": "🏛",
        "title": "Правительственный центр",
        "subtitle": "Администрация, финансы и государственные решения",
    },
    "industrial": {
        "emoji": "🏭",
        "title": "Промышленный район",
        "subtitle": "Производство, энергетика и доходы государства",
    },
    "social": {
        "emoji": "🏥",
        "title": "Социальный район",
        "subtitle": "Школы, больницы и государственное жильё",
    },
    "security": {
        "emoji": "🚓",
        "title": "Район безопасности",
        "subtitle": "Надзор, защита казны и правопорядок",
    },
    "culture": {
        "emoji": "🔬",
        "title": "Научно-культурный район",
        "subtitle": "Наука, образование и государственные события",
    },
}

BUILDING_DISTRICTS = {
    "factory": "industrial",
    "power_plant": "industrial",
    "school": "social",
    "hospital": "social",
    "housing": "social",
    "police": "security",
    "culture_house": "culture",
    "science": "culture",
    "state_bank": "government",
    "administration": "government",
}

STATIC_LANDMARKS = (
    {"key": "presidency", "emoji": "👑", "title": "Администрация Президента", "district": "government", "x": 49, "y": 13},
    {"key": "duma", "emoji": "🗳", "title": "Государственная дума", "district": "government", "x": 62, "y": 19},
    {"key": "finance", "emoji": "💰", "title": "Министерство финансов", "district": "government", "x": 36, "y": 20},
    {"key": "oversight", "emoji": "🛡", "title": "Государственный надзор", "district": "security", "x": 80, "y": 42},
    {"key": "court", "emoji": "⚖️", "title": "Верховный суд", "district": "government", "x": 51, "y": 29},
)

# Координаты заданы в процентах внутри масштабируемого HTML-поля.
# Всего 30 участков — достаточно для ограничения: 10 типов × 3 объекта.
PLOTS = (
    {"plot_id": "gov-1", "district": "government", "slot_no": 1, "x": 31, "y": 11},
    {"plot_id": "gov-2", "district": "government", "slot_no": 2, "x": 69, "y": 11},
    {"plot_id": "gov-3", "district": "government", "slot_no": 3, "x": 27, "y": 29},
    {"plot_id": "gov-4", "district": "government", "slot_no": 4, "x": 72, "y": 30},
    {"plot_id": "gov-5", "district": "government", "slot_no": 5, "x": 39, "y": 37},
    {"plot_id": "gov-6", "district": "government", "slot_no": 6, "x": 62, "y": 38},
    {"plot_id": "ind-1", "district": "industrial", "slot_no": 1, "x": 12, "y": 55},
    {"plot_id": "ind-2", "district": "industrial", "slot_no": 2, "x": 25, "y": 54},
    {"plot_id": "ind-3", "district": "industrial", "slot_no": 3, "x": 8, "y": 71},
    {"plot_id": "ind-4", "district": "industrial", "slot_no": 4, "x": 21, "y": 72},
    {"plot_id": "ind-5", "district": "industrial", "slot_no": 5, "x": 34, "y": 63},
    {"plot_id": "ind-6", "district": "industrial", "slot_no": 6, "x": 35, "y": 79},
    {"plot_id": "soc-1", "district": "social", "slot_no": 1, "x": 48, "y": 54},
    {"plot_id": "soc-2", "district": "social", "slot_no": 2, "x": 60, "y": 53},
    {"plot_id": "soc-3", "district": "social", "slot_no": 3, "x": 72, "y": 55},
    {"plot_id": "soc-4", "district": "social", "slot_no": 4, "x": 45, "y": 69},
    {"plot_id": "soc-5", "district": "social", "slot_no": 5, "x": 58, "y": 68},
    {"plot_id": "soc-6", "district": "social", "slot_no": 6, "x": 71, "y": 70},
    {"plot_id": "soc-7", "district": "social", "slot_no": 7, "x": 48, "y": 83},
    {"plot_id": "soc-8", "district": "social", "slot_no": 8, "x": 61, "y": 82},
    {"plot_id": "soc-9", "district": "social", "slot_no": 9, "x": 74, "y": 84},
    {"plot_id": "sec-1", "district": "security", "slot_no": 1, "x": 84, "y": 55},
    {"plot_id": "sec-2", "district": "security", "slot_no": 2, "x": 88, "y": 70},
    {"plot_id": "sec-3", "district": "security", "slot_no": 3, "x": 89, "y": 84},
    {"plot_id": "cul-1", "district": "culture", "slot_no": 1, "x": 8, "y": 12},
    {"plot_id": "cul-2", "district": "culture", "slot_no": 2, "x": 18, "y": 20},
    {"plot_id": "cul-3", "district": "culture", "slot_no": 3, "x": 8, "y": 31},
    {"plot_id": "cul-4", "district": "culture", "slot_no": 4, "x": 18, "y": 39},
    {"plot_id": "cul-5", "district": "culture", "slot_no": 5, "x": 7, "y": 45},
    {"plot_id": "cul-6", "district": "culture", "slot_no": 6, "x": 22, "y": 45},
)

PLOT_BY_ID = {str(item["plot_id"]): item for item in PLOTS}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS government_map_plots_v180(
  chat_id INTEGER NOT NULL,
  plot_id TEXT NOT NULL,
  district TEXT NOT NULL,
  slot_no INTEGER NOT NULL,
  x INTEGER NOT NULL,
  y INTEGER NOT NULL,
  project_id TEXT,
  building_id TEXT,
  building_key TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY(chat_id,plot_id),
  UNIQUE(project_id),
  UNIQUE(building_id)
);
CREATE INDEX IF NOT EXISTS idx_government_map_plots_v180_chat
  ON government_map_plots_v180(chat_id,district,status);
"""


def district_for(building_key: str) -> str:
    return BUILDING_DISTRICTS.get(str(building_key), "government")


def plot_payload(plot_id: str) -> dict[str, Any]:
    return dict(PLOT_BY_ID[str(plot_id)])
