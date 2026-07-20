from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import career_rewards_v120 as rewards
from career_model_v120 import deterministic_range, fmt


VERSION = "Reality 122 · Карьера за действия"
_ACTION_MARKER = re.compile(r"#ACTION_([0-9a-f]{10})", flags=re.IGNORECASE)


def _today_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


async def _task_before_completion(core: Any, message: Any) -> Any | None:
    if not message.from_user or not message.reply_to_message:
        return None
    replied_text = (
        message.reply_to_message.text
        or message.reply_to_message.caption
        or ""
    )
    match = _ACTION_MARKER.search(replied_text)
    if match is not None:
        return await core.db.get_action_task(match.group(1).lower())
    return await core.db.get_open_social_task(
        int(message.chat.id),
        int(message.from_user.id),
    )


def install_career_interactions_v122(core: Any) -> None:
    if getattr(core, "_career_interactions_v122_installed", False):
        return
    core._career_interactions_v122_installed = True
    core.CAREER_INTERACTIONS_VERSION = VERSION

    original_roulette = core.apply_roulette

    async def apply_roulette_with_career(chat_id: int, user: Any) -> str:
        before_player = await core.db.get_player(int(chat_id), int(user.id))
        before = int(before_player.points) if before_player is not None else 0
        text = await original_roulette(int(chat_id), user)
        after_player = await core.db.get_player(int(chat_id), int(user.id))
        after = int(after_player.points) if after_player is not None else before
        if after <= before:
            return text
        source_id = f"{int(chat_id)}:{int(user.id)}:{_today_key()}"
        added = await rewards.award(
            core,
            int(chat_id),
            int(user.id),
            500,
            "roulette_positive_day",
            source_id,
            "Первый положительный результат дня в рулетке",
        )
        if added > 0:
            return text + f"\n⭐ Карьерное влияние: <b>+{fmt(added)}</b>."
        return text + "\n⭐ Карьерная награда за положительную рулетку сегодня уже получена."

    core.apply_roulette = apply_roulette_with_career

    original_complete = core.maybe_complete_action_task

    async def maybe_complete_action_task_with_career(message: Any) -> bool:
        task = await _task_before_completion(core, message)
        handled = await original_complete(message)
        if not handled or task is None or not message.from_user:
            return handled

        refreshed = await core.db.get_action_task(str(task["task_id"]))
        if refreshed is None or str(refreshed["status"]) != "completed":
            return handled

        task_id = str(refreshed["task_id"])
        task_key = str(refreshed["task_key"] or "")
        if task_key.startswith("social:"):
            amount = deterministic_range(f"secret-task:{task_id}", 3_000, 5_000)
            source_type = "secret_task"
            reason = "Сложное или тайное задание"
        else:
            amount = 1_500
            source_type = "task"
            reason = "Проверяемое действие"

        added = await rewards.award(
            core,
            int(message.chat.id),
            int(message.from_user.id),
            amount,
            source_type,
            task_id,
            reason,
        )
        if added > 0:
            await core.ephemeral_reply(
                message,
                f"⭐ <b>Карьерное влияние: +{fmt(added)}</b>.",
            )
        return handled

    core.maybe_complete_action_task = maybe_complete_action_task_with_career
