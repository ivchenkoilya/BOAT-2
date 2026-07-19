from __future__ import annotations

from typing import Any


VERSION = "Reality 88 · Щедрое влияние"
BASE_REWARD_MIN = 50
BASE_REWARD_MAX = 150


def install_influence_reward_v88(core: Any) -> None:
    """Повышает базовую награду действия «Увеличить влияние»."""
    if getattr(core, "_influence_reward_v88_installed", False):
        return
    core._influence_reward_v88_installed = True
    core.BOT_VERSION = VERSION

    original_roll_score_action = core.roll_score_action

    def roll_score_action_v88(action_key: str) -> tuple[int, str]:
        if action_key != "influence":
            return original_roll_score_action(action_key)

        # Фразу берём из старой реализации, а слабую награду 1–100 заменяем
        # заметной базовой выплатой 50–150. Все бонусы Древа применяются позже.
        _, phrase = original_roll_score_action(action_key)
        return core.random.randint(BASE_REWARD_MIN, BASE_REWARD_MAX), phrase

    core.roll_score_action = roll_score_action_v88

    original_inline_menu_specs = core.inline_menu_specs

    def inline_menu_specs_v88(user: Any) -> list[dict[str, Any]]:
        items = original_inline_menu_specs(user)
        for item in items:
            if str(item.get("action") or "") == "score:influence":
                item["description"] = (
                    "50–150 базовых очков · бонусы Древа сверху · кулдаун 6 часов"
                )
        return items

    core.inline_menu_specs = inline_menu_specs_v88

    original_about = core.about_bot_text

    def about_bot_text_v88() -> str:
        return (
            original_about()
            + "\n• базовая награда команды повышена с 1–100 до 50–150 влияния;"
            + "\n• усиления Древа применяются поверх этой суммы."
        )

    core.about_bot_text = about_bot_text_v88
