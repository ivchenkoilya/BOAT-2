from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

import hero_loadouts_v103 as loadouts


HERO_UPDATES: dict[int, dict[str, Any]] = {
    1: {
        "name": "Каблучий",
        "title": "Узник обручального кольца",
        "description": (
            "Когда-то Каблучий свободно странствовал по миру, но после заключения "
            "брачного союза оказался связан древними правилами семейного договора. "
            "Теперь для выхода из крепости ему требуется особое разрешение. Получив "
            "его, он ненадолго возвращается к друзьям и сражается так, будто следующего "
            "выхода может не быть."
        ),
    },
    2: {
        "name": "Вайбус",
        "title": "Призрак общей сходки",
        "description": (
            "Представитель легендарного движения «Плюс Вайб». Всегда уверенно говорит, "
            "что придёт на встречу с друзьями, но в последний момент бесследно исчезает. "
            "Обычно его можно обнаружить курящим где-нибудь в стороне или занятым "
            "поисками загадочного крестика на карте."
        ),
    },
    3: {
        "name": "Солёний",
        "title": "Владыка тухлых кроссовок",
        "description": (
            "Креативный и непредсказуемый работник завода, способный превратить любую "
            "глупую идею в легендарную историю. Его тухлые кроссовки создают настолько "
            "сильную ауру, что окружающие чувствуют приближение Солёния раньше, чем видят "
            "его. Сам он запаха не замечает и считает, что остальные просто не выдерживают "
            "его присутствия."
        ),
    },
    6: {
        "name": "Сливариус",
        "title": "Малый дипломат",
        "description": (
            "Второй представитель «Плюс Вайба» и постоянный спутник Вайбуса. Редко "
            "появляется на встречах один, часто курит и не отличается крупными размерами. "
            "Маленький и щуплый, зато быстрый, прыгучий и невероятно скользкий. Умеет "
            "договариваться, находить компромиссы и дипломатично выбираться из сложных "
            "ситуаций."
        ),
    },
}

ITEM_UPDATES: dict[str, dict[str, Any]] = {
    # Ключ сохраняется прежним, чтобы уже купленный предмет не пропал из SQLite.
    "developer_sock": {
        "name": "Тухлые кроссовки Владыки",
        "icon": "👟",
        "description": (
            "Рабочая обувь Солёния, пропитанная потом, заводской пылью и собственной "
            "удушающей аурой. Даёт +5% к урону владельца и снижает урон босса по всему "
            "отряду на 7%."
        ),
    },
}


async def _rewrite_recent_logs(db: Any, boss_id: str, since: int) -> None:
    """Обновляет старые внутренние названия в только что созданных записях боя."""
    conn = db._require_connection()
    async with db.lock:
        await conn.execute(
            """
            UPDATE boss_logs
            SET log_text = REPLACE(
                REPLACE(
                    REPLACE(log_text, 'Сливариус исчез', 'Вайбус исчез'),
                    'Скользий', 'Сливариус'
                ),
                'Тухлый носок', 'Тухлые кроссовки Владыки'
            )
            WHERE boss_id = ? AND created_at >= ?
            """,
            (str(boss_id), int(since)),
        )
        await conn.commit()


def install_hero_content_v105(core: Any) -> None:
    if getattr(core, "_hero_content_v105_installed", False):
        return
    core._hero_content_v105_installed = True

    for hero_id, values in HERO_UPDATES.items():
        if hero_id in loadouts.HEROES:
            loadouts.HEROES[hero_id].update(values)

    for item_key, values in ITEM_UPDATES.items():
        if item_key in loadouts.ITEMS:
            loadouts.ITEMS[item_key].update(values)

    original_hit: Callable[..., Awaitable[dict[str, Any]]] = core.Database.boss_apply_hit
    original_action: Callable[..., Awaitable[dict[str, Any]]] = core.Database.boss_perform_action

    async def hit_with_current_names(
        self: Any,
        boss_id: str,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        started_at = int(time.time()) - 1
        result = await original_hit(self, boss_id, chat_id, user_id)
        if result.get("ok"):
            await _rewrite_recent_logs(self, boss_id, started_at)
        return result

    async def action_with_current_names(
        self: Any,
        boss_id: str,
    ) -> dict[str, Any]:
        started_at = int(time.time()) - 1
        result = await original_action(self, boss_id)
        if result.get("ok"):
            await _rewrite_recent_logs(self, boss_id, started_at)
            notes = [
                str(note)
                .replace("Сливариус исчез", "Вайбус исчез")
                .replace("Скользий", "Сливариус")
                .replace("Тухлый носок", "Тухлые кроссовки Владыки")
                for note in list(result.get("loadout_notes") or [])
            ]
            if notes:
                result = dict(result)
                result["loadout_notes"] = notes
        return result

    core.Database.boss_apply_hit = hit_with_current_names
    core.Database.boss_perform_action = action_with_current_names
