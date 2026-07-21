from __future__ import annotations

import time
from typing import Any

import government_institutions_v128 as institutions


VERSION = "Reality 138 · Безопасный лимит ставок ЦБ"
MAX_WAGER = 1_000_000


def install_central_bank_wager_limit_v137(core: Any) -> None:
    """Поднимает обычный лимит ставок ЦБ без вмешательства в запуск БД.

    Предыдущая версия оборачивала Database.connect и могла задерживать открытие
    веб-порта на Amvera. Теперь миграция выполняется лениво при чтении политики,
    когда приложение уже полностью запущено.
    """
    if getattr(core, "_central_bank_wager_limit_v137_installed", False):
        return
    core._central_bank_wager_limit_v137_installed = True
    core.CENTRAL_BANK_WAGER_VERSION = VERSION
    core.BOT_GAME_MAX_STAKE = MAX_WAGER
    institutions.VERSION = VERSION

    for action in institutions.OFFICE_ACTIONS.get("central_bank", []):
        if action.get("key") == "economic_policy":
            action["hint"] = "Комиссия, ставки до 1 000 000 и лимиты займов"

    original_policy = institutions._policy

    async def policy_with_million_wager(
        core_value: Any,
        chat_id: int,
    ) -> dict[str, Any]:
        policy = dict(await original_policy(core_value, int(chat_id)))
        mode = str(policy.get("economic_mode") or "stability")
        emergency = bool(policy.get("emergency"))

        # Базовое значение в базе всегда миллион. Спецрежимы по-прежнему могут
        # временно уменьшать фактически возвращаемый лимит.
        try:
            conn = core_value.db._require_connection()
            await conn.execute(
                """
                UPDATE government_policy_v128
                SET max_wager = ?, updated_at = ?
                WHERE chat_id = ? AND max_wager <> ?
                """,
                (MAX_WAGER, int(time.time()), int(chat_id), MAX_WAGER),
            )
            await conn.commit()
        except Exception:
            # Ошибка миграции не должна останавливать бота или веб-сервер.
            pass

        if not emergency and mode in {"stability", "growth", "inflation"}:
            policy["max_wager"] = MAX_WAGER
        return policy

    institutions._policy = policy_with_million_wager
