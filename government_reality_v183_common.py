from __future__ import annotations

from typing import Any

VERSION = "Reality 183 · Живой город"
CLIENT_BUILD = "183-20260724-a"

DISTRICT_BUILDINGS: dict[str, tuple[str, ...]] = {
    "government": ("administration", "state_bank"),
    "industrial": ("factory", "power_plant"),
    "social": ("school", "hospital", "housing"),
    "security": ("police",),
    "culture": ("culture_house", "science"),
}

PROGRAM_EVENT_VISUALS: dict[str, dict[str, str]] = {
    "anti_crisis": {"class": "crisis", "label": "Антикризисный штаб"},
    "festival": {"class": "festival", "label": "Государственный фестиваль"},
    "social_help": {"class": "social", "label": "Социальная помощь"},
    "oversight_operation": {"class": "audit", "label": "Операция Надзора"},
    "market_intervention": {"class": "finance", "label": "Финансовая интервенция"},
    "election_campaign": {"class": "election", "label": "Избирательная кампания"},
    "infrastructure": {"class": "construction", "label": "Модернизация инфраструктуры"},
    "education_grants": {"class": "education", "label": "Образовательные гранты"},
    "emergency_social": {"class": "medical", "label": "Экстренная поддержка"},
    "cyber_defense": {"class": "cyber", "label": "Киберзащита казны"},
    "anti_corruption_audit": {"class": "audit", "label": "Антикоррупционный аудит"},
    "economy_support": {"class": "finance", "label": "Поддержка экономики"},
    "information_campaign": {"class": "media", "label": "Информационная кампания"},
    "emergency_mode": {"class": "emergency", "label": "Режим чрезвычайной ситуации"},
    "science_project": {"class": "science", "label": "Научный проект"},
    "housing_subsidy": {"class": "housing", "label": "Жилищная субсидия"},
}

DEVELOPMENT_TIERS: tuple[dict[str, Any], ...] = (
    {"min": 0, "level": 1, "title": "Зарождающееся государство", "traffic": 1, "decor": 0},
    {"min": 20, "level": 2, "title": "Развивающийся город", "traffic": 2, "decor": 1},
    {"min": 40, "level": 3, "title": "Благоустроенная столица", "traffic": 3, "decor": 2},
    {"min": 60, "level": 4, "title": "Процветающее государство", "traffic": 4, "decor": 3},
    {"min": 80, "level": 5, "title": "Великая столица", "traffic": 5, "decor": 4},
)


def development_tier(value: int) -> dict[str, Any]:
    current = DEVELOPMENT_TIERS[0]
    for tier in DEVELOPMENT_TIERS:
        if int(value) >= int(tier["min"]):
            current = tier
    return dict(current)
