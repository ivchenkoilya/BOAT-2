from __future__ import annotations

import re
from typing import Any

import talent_system as talents


VERSION = "Reality 164 · Усиленные награды и риск игр"
REWARD_MULTIPLIER = 10


def _replace_first_number(text: str, before: int, after: int) -> str:
    if before <= 0 or before == after:
        return str(text)
    return re.sub(
        rf"(?<!\d){re.escape(str(before))}(?!\d)",
        str(after),
        str(text),
        count=1,
    )


def _scaled_positive(value: int) -> int:
    number = int(value)
    return number * REWARD_MULTIPLIER if number > 0 else number


def install_economy_rewards_v164(core: Any) -> None:
    """Умножает положительные награды Шара и увеличения влияния в десять раз."""
    if getattr(core, "_economy_rewards_v164_installed", False):
        return
    core._economy_rewards_v164_installed = True
    core.ECONOMY_REWARDS_VERSION = VERSION

    # «Увеличить влияние» формирует награду через roll_score_action.
    # Масштабируем базу до применения бонусов Древа знаний.
    original_roll_score_action = core.roll_score_action

    def roll_score_action_v164(action_key: str) -> tuple[int, str]:
        delta, event_text = original_roll_score_action(action_key)
        value = int(delta)
        if str(action_key) == "influence" and value > 0:
            scaled = _scaled_positive(value)
            return scaled, _replace_first_number(str(event_text), value, scaled)
        return value, str(event_text)

    core.roll_score_action = roll_score_action_v164

    # До принятия судьбы карточка показывает тот же десятикратный положительный
    # результат, который затем реально будет начислен. Отрицательные исходы не меняем.
    original_fate_vision_text = core.fate_vision_text

    def fate_vision_text_v164(
        player: Any,
        session_id: str,
        rarity: str,
        delta: int,
        prophecy: str,
        challenged: bool,
    ) -> str:
        return original_fate_vision_text(
            player,
            session_id,
            rarity,
            _scaled_positive(int(delta)),
            prophecy,
            challenged,
        )

    core.fate_vision_text = fate_vision_text_v164

    # Шар судьбы хранит базовый исход в сессии. При окончательном принятии
    # увеличиваем только положительное начисление. Это также работает со старыми
    # сессиями, созданными до обновления.
    original_add_points = core.Database.add_points_with_balance

    async def add_points_with_rewards_v164(self: Any, *args: Any, **kwargs: Any):
        extracted = talents._extract_score_args(args, kwargs)
        if extracted is not None:
            _chat_id, _user_id, delta, reason = extracted
            if int(delta) > 0 and "fate_orb_result" in str(reason or "").casefold():
                args, kwargs = talents._replace_delta(
                    args,
                    kwargs,
                    _scaled_positive(int(delta)),
                )
        return await original_add_points(self, *args, **kwargs)

    core.Database.add_points_with_balance = add_points_with_rewards_v164

    original_inline_menu_specs = core.inline_menu_specs

    def inline_menu_specs_v164(user: Any) -> list[dict[str, Any]]:
        items = original_inline_menu_specs(user)
        for item in items:
            action = str(item.get("action") or "")
            if action == "score:influence":
                item["description"] = (
                    "Положительная награда увеличена в 10 раз · кулдаун 6 часов"
                )
            elif action == "fate":
                item["description"] = "Положительные награды Шара увеличены в 10 раз"
        return items

    core.inline_menu_specs = inline_menu_specs_v164
