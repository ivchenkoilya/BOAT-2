from __future__ import annotations

from typing import Any

import finance_investments_v127_core as investments
import finance_system_v112 as finance


VERSION = "Reality 129 · Портфель и быстрые вклады"

ROLE_LOAN_LIMITS = {
    "decoration": 5_000,
    "dust": 10_000,
    "extras": 25_000,
    "secondary": 50_000,
    "hero": 100_000,
}

DEPOSIT_UPDATE: dict[str, dict[str, Any]] = {
    "flex": {
        "title": "Гибкий",
        "term_days": 3,
        "yield_percent": 1.5,
        "daily_percent": 0.5,
        "early": "allowed",
        "early_note": "Можно снять в любой момент. Доход начисляется по 0,5% в сутки, максимум за 3 дня.",
    },
    "safe7": {
        "title": "Быстрый",
        "term_days": 3,
        "yield_percent": 3.0,
        "early": "interest_lost",
        "early_note": "При досрочном снятии возвращается только основная сумма.",
    },
    "premium14": {
        "title": "Премиальный",
        "term_days": 7,
        "yield_percent": 8.0,
        "early": "penalty_3",
        "early_note": "При досрочном снятии удерживается 3% от основной суммы.",
    },
    "capital30": {
        "title": "Главный капитал",
        "term_days": 10,
        "yield_percent": 14.0,
        "early": "locked",
        "early_note": "Максимальный доход за 10 дней. Досрочное снятие недоступно.",
    },
}


def _role_limit(core: Any, points: int) -> tuple[str, int]:
    value = int(points)
    if value >= int(core.HERO_MIN_POINTS):
        return "Главный герой", ROLE_LOAN_LIMITS["hero"]
    if value >= int(core.SECONDARY_MIN_POINTS):
        return "Второстепенная роль", ROLE_LOAN_LIMITS["secondary"]
    if value >= int(core.EXTRAS_MIN_POINTS):
        return "Массовка", ROLE_LOAN_LIMITS["extras"]
    if value >= int(core.DUST_MIN_POINTS):
        return "Пыль", ROLE_LOAN_LIMITS["dust"]
    return "Декорация", ROLE_LOAN_LIMITS["decoration"]


def install_finance_products_v129(core: Any) -> None:
    if getattr(core, "_finance_products_v129_installed", False):
        return
    core._finance_products_v129_installed = True
    core.FINANCE_SYSTEM_VERSION = VERSION

    # Все старые обработчики и Mini App читают эти значения из модуля во время операции.
    finance.LOAN_MAX = ROLE_LOAN_LIMITS["hero"]
    finance._role_limit = _role_limit
    investments.DEPOSIT_PLANS.clear()
    investments.DEPOSIT_PLANS.update(DEPOSIT_UPDATE)

    previous_connect = core.Database.connect

    async def connect_with_product_migration(self: Any) -> None:
        await previous_connect(self)
        conn = self._require_connection()
        async with self.lock:
            # Уже открытые длинные вклады тоже сокращаются до новых сроков,
            # поэтому пользователь не останется ждать старые 14 или 30 дней.
            for plan_key, plan in DEPOSIT_UPDATE.items():
                max_seconds = int(plan["term_days"]) * 86_400
                await conn.execute(
                    """
                    UPDATE finance_deposits_v127
                    SET matures_at=MIN(matures_at,started_at+?)
                    WHERE plan_key=? AND status='active'
                    """,
                    (max_seconds, plan_key),
                )
            await conn.commit()

    core.Database.connect = connect_with_product_migration
