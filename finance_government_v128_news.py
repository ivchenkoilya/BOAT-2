from __future__ import annotations

import json
import re
from typing import Any

from finance_investments_v127_core import MARKET_TICK_SECONDS, _now
from finance_market_news_v128 import _general_effects, _insert_news, company_news


MODE_EFFECTS: dict[str, dict[str, int]] = {
    "growth": {"EGO": 260, "HERO": 340, "NPC": 180, "CORV": 230, "CENTER": 120},
    "stability": {"EGO": 150, "HERO": 110, "NPC": 70, "CORV": 60, "CENTER": -180},
    "crisis": {"EGO": -330, "HERO": -290, "NPC": -240, "CORV": -370, "CENTER": 460},
    "freeze": {"EGO": -210, "HERO": -180, "NPC": -160, "CORV": -230, "CENTER": -90},
    "inflation": {"EGO": -190, "HERO": 120, "NPC": -220, "CORV": 170, "CENTER": 270},
}

MODE_LABELS = {
    "growth": "режим экономического роста",
    "stability": "режим стабилизации",
    "crisis": "кризисный режим",
    "freeze": "режим заморозки операций",
    "inflation": "инфляционный режим",
}


def _payload(row: Any) -> dict[str, Any]:
    try:
        value = json.loads(str(row["payload_json"] or "{}"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _mode_from_detail(detail: str, payload: dict[str, Any]) -> str:
    direct = str(payload.get("mode") or "").casefold()
    if direct in MODE_EFFECTS:
        return direct
    lower = str(detail or "").casefold()
    for mode in MODE_EFFECTS:
        if re.search(rf"\b{re.escape(mode)}\b", lower):
            return mode
    return "stability"


def _policy_effects(detail: str) -> dict[str, int]:
    lower = str(detail or "").casefold()
    match = re.search(r"комиссия\s+([0-9]+(?:[.,][0-9]+)?)%", lower)
    fee = float(match.group(1).replace(",", ".")) if match else 0.0
    pressure = max(20, min(300, round(fee * 42)))
    loan_match = re.search(r"за[её]м\s+до\s+([0-9\s]+)", lower)
    loan_limit = int(re.sub(r"\D", "", loan_match.group(1))) if loan_match else 1_000_000
    liquidity = 120 if loan_limit >= 500_000 else -160 if loan_limit <= 50_000 else 20
    return {
        "EGO": liquidity - pressure,
        "HERO": round(liquidity * 0.8) - round(pressure * 0.5),
        "NPC": round(liquidity * 0.45) - round(pressure * 0.25),
        "CORV": round(liquidity * 0.65) - round(pressure * 0.75),
        "CENTER": -round(liquidity * 0.5) + round(pressure * 0.35),
    }


def _action_effects(row: Any) -> dict[str, int]:
    key = str(row["action_key"] or "")
    detail = str(row["detail"] or "")
    title = str(row["title"] or "")
    payload = _payload(row)
    if key == "economic_mode":
        return dict(MODE_EFFECTS[_mode_from_detail(detail, payload)])
    if key == "economic_policy":
        return _policy_effects(detail)
    if key == "emergency":
        return {"EGO": -310, "HERO": -260, "NPC": -230, "CORV": -340, "CENTER": 520}
    if key == "security_meeting":
        return {"EGO": -80, "HERO": -50, "NPC": -40, "CORV": -90, "CENTER": 190}
    if key == "security_report":
        effects = _general_effects(title, detail)
        effects["CENTER"] = effects.get("CENTER", 0) - 70
        return effects
    if key in {"decree", "statement", "public_appeal"}:
        return _general_effects(title, detail)
    if key in {"treasury_audit", "tax_audit", "budget_audit"}:
        return {"EGO": 55, "HERO": 35, "NPC": 20, "CORV": 15, "CENTER": -80}
    return {}


def _source_title(row: Any) -> str:
    key = str(row["action_key"] or "")
    detail = str(row["detail"] or "")
    payload = _payload(row)
    if key == "economic_mode":
        mode = _mode_from_detail(detail, payload)
        return f"Центральный банк ввёл {MODE_LABELS.get(mode, mode)}"
    if key == "economic_policy":
        return f"Центральный банк изменил параметры рынка: {detail}"
    if key == "emergency":
        return "Правительство ввело чрезвычайный режим"
    if key == "security_meeting":
        return "Созван Совет безопасности"
    return str(row["title"] or "Решение правительства")


async def sync_power_news(core: Any, chat_id: int) -> None:
    conn = core.db._require_connection()
    cutoff = _now() - 3 * 86_400
    try:
        cursor = await conn.execute(
            """
            SELECT * FROM government_power_log_v128
            WHERE chat_id=? AND created_at>=? AND action_key IN (
                'economic_policy','economic_mode','emergency','security_meeting',
                'security_report','decree','statement','public_appeal',
                'treasury_audit','tax_audit','budget_audit'
            )
            ORDER BY created_at DESC LIMIT 160
            """,
            (int(chat_id), cutoff),
        )
        rows = list(await cursor.fetchall())
    except Exception:
        return

    impact_at = (_now() // MARKET_TICK_SECONDS) * MARKET_TICK_SECONDS
    async with core.db.lock:
        for row in rows:
            effects = _action_effects(row)
            if not effects:
                continue
            source = _source_title(row)
            action_key = str(row["action_key"] or "")
            category = (
                "Центральный банк"
                if action_key in {"economic_policy", "economic_mode"}
                else "Совет безопасности"
                if action_key in {"emergency", "security_meeting", "security_report"}
                else "Действие правительства"
            )
            for symbol, effect in effects.items():
                title, summary, body = company_news(symbol, source, int(effect))
                await _insert_news(
                    conn,
                    chat_id=chat_id,
                    symbol=symbol,
                    source_key=f"power:{row['action_id']}",
                    source_type="government_power",
                    category=category,
                    title=title,
                    summary=summary,
                    body=body,
                    effect_bp=int(effect),
                    event_at=impact_at,
                    source_at=int(row["created_at"]),
                )
        await conn.commit()
