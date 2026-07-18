from __future__ import annotations

from typing import Any

import talent_system as talents


EXTRA_SKILLS: dict[str, dict[str, Any]] = {
    "damage5": {"branch": "damage", "name": "Тяжёлый аргумент", "max": 3, "cost": 1, "parent": "damage1"},
    "damage6": {"branch": "damage", "name": "Разрушитель самооценки", "max": 2, "cost": 2, "parent": "damage5"},
    "damage7": {"branch": "damage", "name": "Финальное слово", "max": 1, "cost": 4, "parent": "damage6"},
    "influence5": {"branch": "influence", "name": "Живой авторитет", "max": 3, "cost": 1, "parent": "influence1"},
    "influence6": {"branch": "influence", "name": "Легенда беседы", "max": 2, "cost": 2, "parent": "influence5"},
    "influence7": {"branch": "influence", "name": "Икона реальности", "max": 1, "cost": 4, "parent": "influence6"},
    "defense5": {"branch": "defense", "name": "Холодный разум", "max": 3, "cost": 1, "parent": "defense1"},
    "defense6": {"branch": "defense", "name": "Непоколебимость", "max": 2, "cost": 2, "parent": "defense5"},
    "defense7": {"branch": "defense", "name": "Недосягаемый", "max": 1, "cost": 4, "parent": "defense6"},
    "rewards5": {"branch": "rewards", "name": "Охотник за удачей", "max": 3, "cost": 1, "parent": "rewards1"},
    "rewards6": {"branch": "rewards", "name": "Золотой случай", "max": 2, "cost": 2, "parent": "rewards5"},
    "rewards7": {"branch": "rewards", "name": "Избранник судьбы", "max": 1, "cost": 4, "parent": "rewards6"},
}


def install_expansion(core: Any) -> None:
    """Добавляет разветвлённые навыки и их серверные эффекты."""
    if getattr(talents, "_expanded_tree_installed", False):
        return
    talents._expanded_tree_installed = True
    talents.SKILLS.update(EXTRA_SKILLS)

    original_calculate_buffs = talents.calculate_buffs

    def calculate_expanded_buffs(levels: dict[str, int]) -> dict[str, float]:
        buffs = original_calculate_buffs(levels)
        buffs["boss_damage"] += levels.get("damage5", 0) * 0.02
        buffs["boss_crit_power"] += levels.get("damage6", 0) * 0.10
        buffs["boss_crit_chance"] += levels.get("damage7", 0) * 0.03
        buffs["activity"] += levels.get("influence5", 0) * 0.02
        buffs["tasks"] += levels.get("influence6", 0) * 0.04
        buffs["influence"] += levels.get("influence7", 0) * 0.05
        buffs["penalty_reduction"] += levels.get("defense5", 0) * 0.03
        buffs["avoid_penalty"] += levels.get("defense6", 0) * 0.04
        buffs["sabotage_reduction"] += levels.get("defense7", 0) * 0.15
        buffs["game_reward"] += levels.get("rewards5", 0) * 0.04
        buffs["rare_reward"] += levels.get("rewards6", 0) * 0.025
        buffs["second_chance"] += levels.get("rewards7", 0) * 0.08
        return buffs

    talents.calculate_buffs = calculate_expanded_buffs

    original_talent_state = talents.talent_state

    async def talent_state_with_user(db: Any, chat_id: int, user_id: int) -> dict[str, Any]:
        data = await original_talent_state(db, chat_id, user_id)
        player = await db.get_player(chat_id, user_id)
        if player is not None:
            data["user"] = {
                "id": user_id,
                "full_name": str(getattr(player, "full_name", "") or "").strip(),
                "username": str(getattr(player, "username", "") or "").strip(),
            }
        return data

    talents.talent_state = talent_state_with_user
