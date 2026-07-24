from __future__ import annotations

import copy
import random
from typing import Any

from government_reality_v181_common import (
    DISTRICT_BOUNDS,
    FILTERS,
    LANDMARK_LAYOUT,
    LANDMARK_VISUALS,
    LAYOUT_VERSION,
    PLOT_LAYOUT,
    ROAD_PATHS,
    VERSION,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    visual_for,
)

PROBLEM_STATUSES = {"underfunded", "frozen", "cancelled"}
CONSTRUCTION_STATUSES = {"awaiting_vote", "awaiting_funding", "building"}


def _fallback_position(plot_id: str, district: str, index: int) -> tuple[int, int]:
    bounds = DISTRICT_BOUNDS.get(str(district), DISTRICT_BOUNDS["government"])
    columns = 3
    col = index % columns
    row = index // columns
    x = int(bounds["x"]) + 58 + col * max(88, (int(bounds["width"]) - 110) // columns)
    y = int(bounds["y"]) + 92 + row * 102
    return (
        min(WORLD_WIDTH - 55, max(55, x)),
        min(WORLD_HEIGHT - 55, max(55, y)),
    )


def _decoration_seed(chat_id: int) -> random.Random:
    return random.Random((int(chat_id) << 7) ^ 0x181C17)


def _decorations(chat_id: int) -> list[dict[str, Any]]:
    rng = _decoration_seed(int(chat_id))
    result: list[dict[str, Any]] = []
    specs = {
        "government": ("lamp", "flag", "fountain", "tree"),
        "industrial": ("lamp", "parking", "truck", "pipe"),
        "social": ("tree", "tree", "lamp", "park", "car"),
        "security": ("lamp", "barrier", "car", "flag"),
        "culture": ("tree", "lamp", "park", "fountain"),
    }
    for district, bounds in DISTRICT_BOUNDS.items():
        count = 9 if district in {"social", "government"} else 7
        types = specs[district]
        for index in range(count):
            x = rng.randint(int(bounds["x"]) + 25, int(bounds["x"]) + int(bounds["width"]) - 25)
            y = rng.randint(int(bounds["y"]) + 45, int(bounds["y"]) + int(bounds["height"]) - 24)
            result.append(
                {
                    "id": f"{district}-{index}",
                    "district": district,
                    "type": rng.choice(types),
                    "x": x,
                    "y": y,
                    "scale": round(rng.uniform(0.78, 1.18), 2),
                    "rotation": rng.randint(-18, 18),
                }
            )
    return result


def _district_stats(objects: list[dict[str, Any]], landmarks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key, bounds in DISTRICT_BOUNDS.items():
        rows = [item for item in objects if str(item.get("district")) == key]
        active = sum(1 for item in rows if str(item.get("status")) == "active")
        construction = sum(1 for item in rows if str(item.get("status")) in CONSTRUCTION_STATUSES)
        problems = sum(
            1
            for item in rows
            if str(item.get("status")) in PROBLEM_STATUSES
            or int(item.get("maintenance_debt") or 0) > 0
        )
        institutions = sum(1 for item in landmarks if str(item.get("district")) == key)
        result.append(
            {
                "key": key,
                "emoji": str(bounds["emoji"]),
                "title": str(bounds["title"]),
                "accent": str(bounds["accent"]),
                "x": int(bounds["x"]),
                "y": int(bounds["y"]),
                "width": int(bounds["width"]),
                "height": int(bounds["height"]),
                "objects": len(rows),
                "active": active,
                "construction": construction,
                "problems": problems,
                "institutions": institutions,
            }
        )
    return result


def enhance_map_state(base: dict[str, Any], chat_id: int) -> dict[str, Any]:
    data = copy.deepcopy(base or {})
    objects = list(data.get("objects") or [])
    district_indexes: dict[str, int] = {}

    for item in objects:
        plot_id = str(item.get("plot_id") or "")
        district = str(item.get("district") or "government")
        index = district_indexes.get(district, 0)
        district_indexes[district] = index + 1
        x, y = PLOT_LAYOUT.get(plot_id, _fallback_position(plot_id, district, index))
        visual = visual_for(str(item.get("building_key") or ""))
        status = str(item.get("status") or "")
        item.update(
            {
                "x": x,
                "y": y,
                "short_title": visual["short"],
                "visual_class": visual["class"],
                "visual_symbol": visual["symbol"],
                "is_construction": status in CONSTRUCTION_STATUSES,
                "is_problem": status in PROBLEM_STATUSES or int(item.get("maintenance_debt") or 0) > 0,
                "is_active": status == "active",
            }
        )

    landmarks = list(data.get("landmarks") or [])
    for item in landmarks:
        key = str(item.get("key") or "")
        x, y = LANDMARK_LAYOUT.get(key, (int(item.get("x") or 50), int(item.get("y") or 50)))
        visual = LANDMARK_VISUALS.get(
            key,
            {"short": str(item.get("title") or key), "class": "institution", "symbol": "◆"},
        )
        item.update(
            {
                "x": x,
                "y": y,
                "short_title": visual["short"],
                "visual_class": visual["class"],
                "visual_symbol": visual["symbol"],
            }
        )

    district_stats = _district_stats(objects, landmarks)
    metrics = dict(data.get("metrics") or {})
    metrics["problems"] = sum(1 for item in objects if bool(item.get("is_problem")))
    metrics["institutions"] = len(landmarks)

    return {
        **data,
        "version": VERSION,
        "layout_version": LAYOUT_VERSION,
        "world": {"width": WORLD_WIDTH, "height": WORLD_HEIGHT},
        "objects": objects,
        "landmarks": landmarks,
        "districts": district_stats,
        "district_bounds": [dict(item) for item in district_stats],
        "filters": [dict(item) for item in FILTERS],
        "roads": list(ROAD_PATHS),
        "decorations": _decorations(int(chat_id)),
        "metrics": metrics,
    }
