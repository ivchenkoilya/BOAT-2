from __future__ import annotations

import re
import secrets
from typing import Any

import sanctions_v126 as sanctions


VERSION = "Reality 126 · Защита санкций от обхода"


def _chat_id(start_param: str | None, request: Any, data: dict[str, Any]) -> int:
    raw = data.get("chat_id") or request.query.get("chat_id")
    try:
        value = int(raw)
        if value < 0:
            return value
    except (TypeError, ValueError):
        pass
    matches = re.findall(r"-\d+", str(start_param or ""))
    return int(matches[-1]) if matches else 0


def install_sanctions_hotfix_v126(core: Any) -> None:
    if getattr(core, "_sanctions_hotfix_v126_installed", False):
        return
    core._sanctions_hotfix_v126_installed = True
    core.SANCTIONS_VERSION = VERSION

    # Финансовая санкция запрещает новые переводы и займы, но не мешает
    # посмотреть долги, кредитную историю и погасить уже существующий долг.
    sanctions.FINANCE_COMMANDS.difference_update(
        {"finance", "money", "bank", "repay", "debts", "credit"}
    )
    sanctions.GAMBLING_COMMANDS.add("ego")

    original_callback_category = sanctions._callback_category

    def callback_category(data: str) -> str | None:
        value = str(data or "").casefold()
        if value.startswith("ego:"):
            return "gambling"
        if value.startswith(("fin112:", "fin118:", "finance:")):
            safe_tokens = (
                ":debts", ":owed", ":credit", ":rules", ":repay",
                ":cancel:", ":reject:",
            )
            if any(token in value for token in safe_tokens):
                return None
            return "finance"
        return original_callback_category(data)

    sanctions._callback_category = callback_category

    # Старый web-middleware блокировал даже погашение долга. Финансовые пути
    # передаём отдельному селективному middleware ниже.
    original_web_category = sanctions._web_category

    def web_category(path: str) -> str | None:
        if "finance" in str(path or "").casefold():
            return None
        return original_web_category(path)

    sanctions._web_category = web_category

    original_bot_game = core.prepare_bot_game_result

    async def prepare_bot_game_guarded(
        user: Any,
        game_type: str,
        stake: int | None,
        chat_id: int,
    ) -> Any:
        row = await sanctions.blocking_sanction(core, chat_id, user.id, "gambling")
        if row is not None:
            text = await sanctions._blocked_text(core, row)
            return core.inline_article(
                f"sanction:botgame:{user.id}:{secrets.token_hex(4)}",
                "🚫 Игра на влияние недоступна",
                "Действует постановление Надзора",
                text,
            )
        return await original_bot_game(user, game_type, stake, chat_id)

    core.prepare_bot_game_result = prepare_bot_game_guarded

    original_ego = core.prepare_ego_challenge_result

    async def prepare_ego_guarded(user: Any, query: str, chat_id: int) -> Any:
        row = await sanctions.blocking_sanction(core, chat_id, user.id, "gambling")
        if row is not None:
            text = await sanctions._blocked_text(core, row)
            return core.inline_article(
                f"sanction:ego:{user.id}:{secrets.token_hex(4)}",
                "🚫 Битва эго недоступна",
                "Действует постановление Надзора",
                text,
            )
        return await original_ego(user, query, chat_id)

    core.prepare_ego_challenge_result = prepare_ego_guarded

    original_action = core.prepare_action_task

    async def prepare_action_guarded(user: Any, chat_id: int) -> Any:
        row = await sanctions.blocking_sanction(core, chat_id, user.id, "tasks")
        if row is not None:
            text = await sanctions._blocked_text(core, row)
            return core.inline_article(
                f"sanction:action:{user.id}:{secrets.token_hex(4)}",
                "🚫 Действия недоступны",
                "Действует постановление Надзора",
                text,
            )
        return await original_action(user, chat_id)

    core.prepare_action_task = prepare_action_guarded

    @core.web.middleware
    async def selective_finance_sanctions(request: Any, handler: Any):
        path = str(request.path or "").casefold()
        if request.method.upper() != "POST" or "finance" not in path or "/api/" not in path:
            return await handler(request)
        try:
            data = await request.json()
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
        action = str(data.get("action") or "").casefold()
        # Погашение долга и отмена/отклонение ещё не вступившей в силу заявки
        # остаются доступными. Остальные POST-запросы создают новую операцию.
        if action in {"repay", "cancel", "reject"}:
            return await handler(request)
        user, start_param = core._webapp_auth(request)
        if user is None:
            return await handler(request)
        chat_id = _chat_id(start_param, request, data)
        if chat_id >= 0:
            return await handler(request)
        row = await sanctions.blocking_sanction(core, chat_id, int(user.id), "finance")
        if row is None:
            return await handler(request)
        spec = sanctions.SANCTION_TYPES.get(
            str(row["sanction_type"]), {"title": "Финансовая блокировка"}
        )
        return core.web.json_response(
            {
                "ok": False,
                "sanctioned": True,
                "reason": (
                    f"Действует санкция: {spec['title']}. "
                    f"Осталось: {sanctions._remaining_text(int(row['expires_at']))}."
                ),
            },
            status=403,
        )

    previous_application = core.web.Application

    def application_with_selective_finance(*args: Any, **kwargs: Any):
        middlewares = list(kwargs.pop("middlewares", []) or [])
        kwargs["middlewares"] = [selective_finance_sanctions, *middlewares]
        return previous_application(*args, **kwargs)

    core.web.Application = application_with_selective_finance
