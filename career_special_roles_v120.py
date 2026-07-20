from __future__ import annotations

from typing import Any

from career_model_v120 import CAREER_CENTER, CAREER_HERO, career_value


def install_career_special_roles_v120(core: Any) -> None:
    if getattr(core, "_career_special_roles_v120_installed", False):
        return
    core._career_special_roles_v120_installed = True

    async def rebellion_target_candidates_v120(
        chat_id: int,
        exclude_user_id: int | None = None,
    ) -> list[Any]:
        temporary_id = await core.temporary_hero_day_user_id(chat_id)
        ids = await core.db.active_sabotage_usurper_ids(chat_id)
        result: list[Any] = []
        seen: set[int] = set()
        for user_id in ids:
            actor_id = int(user_id)
            if actor_id in seen:
                continue
            if exclude_user_id is not None and actor_id == int(exclude_user_id):
                continue
            if temporary_id is not None and actor_id == int(temporary_id):
                continue
            player = await core.db.get_player(chat_id, actor_id)
            if player is None:
                continue
            result.append(player)
            seen.add(actor_id)
        return result

    core.rebellion_target_candidates = rebellion_target_candidates_v120

    handlers = core.router.callback_query.handlers
    old_handler = next(
        (
            handler
            for handler in handlers
            if getattr(handler.callback, "__name__", "") == "handle_role_ability_use"
        ),
        None,
    )
    if old_handler is None:
        return
    original_callback = old_handler.callback
    handlers[:] = [handler for handler in handlers if handler is not old_handler]

    @core.router.callback_query(core.F.data.startswith("ability:use:"))
    async def handle_role_ability_use_v120(callback: Any, bot: Any) -> None:
        if not callback.data or not callback.from_user:
            return await original_callback(callback, bot)
        parts = str(callback.data).split(":")
        if len(parts) != 3:
            return await original_callback(callback, bot)
        event = await core.db.get_role_ability_event(parts[2])
        if event is None:
            return await original_callback(callback, bot)
        chat_id = int(event["chat_id"])
        user_id = int(callback.from_user.id)
        player = await core.db.get_player(chat_id, user_id)
        effective_career = career_value(player.points) if player is not None else 0
        if effective_career < CAREER_CENTER:
            hero_day = await core.db.get_hero_day_state(chat_id)
            temporary_hero = bool(
                hero_day is not None and int(hero_day["user_id"]) == user_id
            )
            sabotage = await core.db.get_active_sabotage_for_usurper(chat_id, user_id)
            if temporary_hero or sabotage is not None:
                effective_career = max(effective_career, CAREER_HERO)
        role_context = core.CAREER_ROLE_CONTEXT_V120
        token = role_context.set(effective_career)
        try:
            await original_callback(callback, bot)
        finally:
            role_context.reset(token)

    handlers = core.router.callback_query.handlers
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "handle_role_ability_use_v120"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
