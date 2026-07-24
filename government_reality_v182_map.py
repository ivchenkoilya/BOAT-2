from __future__ import annotations

import copy
import random
from typing import Any

from government_reality_v182_common import LAYOUT_VERSION, VERSION, layout_payload


def _decorations(chat_id: int, mode: str, districts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rng = random.Random((int(chat_id) << 9) ^ (0x182A if mode == "mobile" else 0x182B))
    result: list[dict[str, Any]] = []
    pools = {
        "government": ("lamp", "flag", "fountain", "tree"),
        "industrial": ("lamp", "parking", "truck", "pipe"),
        "social": ("tree", "tree", "lamp", "park", "car"),
        "security": ("lamp", "barrier", "car", "flag"),
        "culture": ("tree", "lamp", "park", "fountain"),
    }
    for district, bounds in districts.items():
        count = 7 if mode == "mobile" else 9
        for index in range(count):
            margin_x = min(42, max(20, int(bounds["width"]) // 7))
            margin_y = 50
            result.append({
                "id": f"{mode}-{district}-{index}",
                "district": district,
                "type": rng.choice(pools[district]),
                "x": rng.randint(int(bounds["x"]) + margin_x, int(bounds["x"]) + int(bounds["width"]) - margin_x),
                "y": rng.randint(int(bounds["y"]) + margin_y, int(bounds["y"]) + int(bounds["height"]) - 24),
                "scale": round(rng.uniform(0.82, 1.15), 2),
                "rotation": rng.randint(-15, 15),
            })
    return result


def enhance_map_state_v182(base: dict[str, Any], chat_id: int) -> dict[str, Any]:
    data = copy.deepcopy(base or {})
    layouts = layout_payload()
    for mode, layout in layouts.items():
        layout["decorations"] = _decorations(int(chat_id), mode, layout["districts"])

    for item in data.get("objects") or []:
        progress = max(0, min(100, int(item.get("progress") or 0)))
        status = str(item.get("status") or "")
        if status == "awaiting_vote":
            stage = "plan"
        elif status == "awaiting_funding":
            stage = "foundation"
        elif status == "building":
            stage = "frame" if progress < 45 else "shell" if progress < 80 else "finishing"
        else:
            stage = "complete"
        item["construction_stage"] = stage
        item["progress_label"] = f"{progress}%" if status in {"awaiting_funding", "building"} else ""

    metrics = dict(data.get("metrics") or {})
    metrics["working"] = int(metrics.get("active") or 0)
    metrics["building"] = int(metrics.get("construction") or 0)

    return {
        **data,
        "version": VERSION,
        "layout_version": LAYOUT_VERSION,
        "layouts": layouts,
        "metrics": metrics,
    }
