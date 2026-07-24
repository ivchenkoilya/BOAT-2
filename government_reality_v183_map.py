from __future__ import annotations

import copy
from typing import Any

from government_reality_v183_common import (
    CLIENT_BUILD,
    DISTRICT_BUILDINGS,
    PROGRAM_EVENT_VISUALS,
    VERSION,
    development_tier,
)


def _catalog_payload(construction: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in list(construction.get("catalog") or []):
        key = str(item.get("key") or "")
        district = next((name for name, keys in DISTRICT_BUILDINGS.items() if key in keys), "government")
        result.append(
            {
                "key": key,
                "district": district,
                "emoji": str(item.get("emoji") or "🏗"),
                "title": str(item.get("title") or key),
                "effect": str(item.get("effect") or ""),
                "cost": int(item.get("cost") or 0),
                "duration": int(item.get("duration") or 0),
                "count": int(item.get("count") or 0),
                "available": bool(item.get("available")),
                "sources": [
                    {
                        "key": str(source.get("key") or ""),
                        "title": str(source.get("title") or source.get("key") or ""),
                        "balance": int(source.get("balance") or 0),
                    }
                    for source in list(item.get("sources") or [])
                ],
            }
        )
    return result


def _empty_plots(data: dict[str, Any]) -> list[dict[str, Any]]:
    occupied = {str(item.get("plot_id") or "") for item in list(data.get("objects") or [])}
    result: list[dict[str, Any]] = []
    for item in list(data.get("empty_plots") or []):
        plot_id = str(item.get("plot_id") or "")
        if not plot_id or plot_id in occupied:
            continue
        district = str(item.get("district") or "government")
        result.append(
            {
                "plot_id": plot_id,
                "district": district,
                "building_keys": list(DISTRICT_BUILDINGS.get(district, ())),
            }
        )
    return result


def _event_payload(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        key = str(row.get("key") or "")
        visual = PROGRAM_EVENT_VISUALS.get(key, {"class": "state", "label": str(row.get("title") or key)})
        result.append(
            {
                **dict(row),
                "event_class": str(visual["class"]),
                "event_label": str(visual["label"]),
            }
        )
    return result


def enhance_map_state_v183(
    base: dict[str, Any],
    construction: dict[str, Any],
) -> dict[str, Any]:
    data = copy.deepcopy(base or {})
    metrics = dict(data.get("metrics") or {})
    tier = development_tier(int(metrics.get("development") or 0))
    metrics["development_tier"] = int(tier["level"])
    metrics["development_title"] = str(tier["title"])

    return {
        **data,
        "version": VERSION,
        "map_client_version": CLIENT_BUILD,
        "development": tier,
        "metrics": metrics,
        "empty_plots": _empty_plots(data),
        "construction_catalog": _catalog_payload(construction),
        "can_propose": bool(construction.get("can_propose")),
        "program_events": _event_payload(list(data.get("active_programs") or [])),
    }
