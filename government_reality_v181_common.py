from __future__ import annotations

from typing import Any

VERSION = "Reality 181 · Карта государства 2.0"
WORLD_WIDTH = 1200
WORLD_HEIGHT = 760
LAYOUT_VERSION = 181

DISTRICT_BOUNDS: dict[str, dict[str, Any]] = {
    "culture": {
        "x": 25, "y": 28, "width": 270, "height": 335,
        "emoji": "🔬", "title": "Научно-культурный район",
        "accent": "violet",
    },
    "government": {
        "x": 315, "y": 24, "width": 550, "height": 350,
        "emoji": "🏛", "title": "Правительственный центр",
        "accent": "gold",
    },
    "industrial": {
        "x": 25, "y": 395, "width": 395, "height": 335,
        "emoji": "🏭", "title": "Промышленный район",
        "accent": "orange",
    },
    "social": {
        "x": 440, "y": 395, "width": 420, "height": 335,
        "emoji": "🏥", "title": "Социальный район",
        "accent": "green",
    },
    "security": {
        "x": 885, "y": 170, "width": 285, "height": 560,
        "emoji": "🚓", "title": "Район безопасности",
        "accent": "red",
    },
}

# Новая раскладка визуально перераспределяет уже существующие plot_id Reality 180.
# Экономика, project_id и building_id не меняются.
PLOT_LAYOUT: dict[str, tuple[int, int]] = {
    "cul-1": (85, 112), "cul-2": (210, 105),
    "cul-3": (82, 225), "cul-4": (213, 220),
    "cul-5": (92, 322), "cul-6": (222, 315),

    "gov-1": (365, 105), "gov-2": (815, 105),
    "gov-3": (365, 285), "gov-4": (815, 285),
    "gov-5": (500, 323), "gov-6": (682, 323),

    "ind-1": (90, 475), "ind-2": (255, 475),
    "ind-3": (90, 600), "ind-4": (255, 600),
    "ind-5": (170, 700), "ind-6": (350, 685),

    "soc-1": (495, 465), "soc-2": (635, 465), "soc-3": (785, 465),
    "soc-4": (495, 575), "soc-5": (635, 575), "soc-6": (785, 575),
    "soc-7": (495, 690), "soc-8": (635, 690), "soc-9": (785, 690),

    "sec-1": (955, 350), "sec-2": (1080, 510), "sec-3": (955, 670),
}

LANDMARK_LAYOUT: dict[str, tuple[int, int]] = {
    "presidency": (590, 82),
    "finance": (455, 190),
    "duma": (720, 185),
    "court": (590, 235),
    "oversight": (1040, 245),
}

BUILDING_VISUALS: dict[str, dict[str, str]] = {
    "factory": {"short": "Завод", "class": "factory", "symbol": "▥"},
    "power_plant": {"short": "Электростанция", "class": "power", "symbol": "ϟ"},
    "school": {"short": "Школа", "class": "school", "symbol": "A"},
    "hospital": {"short": "Больница", "class": "hospital", "symbol": "+"},
    "housing": {"short": "Жилой комплекс", "class": "housing", "symbol": "▦"},
    "police": {"short": "Полиция", "class": "police", "symbol": "★"},
    "culture_house": {"short": "Дом культуры", "class": "culture", "symbol": "♪"},
    "science": {"short": "Научный институт", "class": "science", "symbol": "⚗"},
    "state_bank": {"short": "Госбанк", "class": "bank", "symbol": "₽"},
    "administration": {"short": "Адм. центр", "class": "administration", "symbol": "◆"},
}

LANDMARK_VISUALS: dict[str, dict[str, str]] = {
    "presidency": {"short": "Президент", "class": "presidency", "symbol": "♛"},
    "duma": {"short": "Госдума", "class": "duma", "symbol": "◫"},
    "finance": {"short": "Минфин", "class": "finance", "symbol": "₽"},
    "oversight": {"short": "Надзор", "class": "oversight", "symbol": "◆"},
    "court": {"short": "Верховный суд", "class": "court", "symbol": "⚖"},
}

FILTERS = (
    {"key": "all", "emoji": "🌐", "title": "Всё"},
    {"key": "construction", "emoji": "🏗", "title": "Стройки"},
    {"key": "active", "emoji": "✅", "title": "Работает"},
    {"key": "problems", "emoji": "⚠", "title": "Проблемы"},
    {"key": "institutions", "emoji": "🏛", "title": "Учреждения"},
)

ROAD_PATHS = (
    "M 18 382 C 260 370, 440 390, 875 385 C 1020 382, 1110 350, 1180 310",
    "M 305 18 C 310 150, 305 260, 315 740",
    "M 870 25 C 866 205, 875 445, 872 742",
    "M 30 382 C 175 270, 245 230, 318 192",
    "M 862 382 C 955 410, 1040 475, 1165 555",
    "M 423 390 C 445 500, 438 620, 425 740",
)


def visual_for(building_key: str) -> dict[str, str]:
    return BUILDING_VISUALS.get(
        str(building_key),
        {"short": str(building_key), "class": "generic", "symbol": "◆"},
    )
