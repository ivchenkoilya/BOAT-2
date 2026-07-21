from __future__ import annotations

import re
import secrets
from typing import Any


VERSION = "Reality 135 · Ставки до миллиона"
MAX_BOT_GAME_STAKE = 1_000_000


def _formatted(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _parse_game_and_amount(query: str) -> tuple[str, int | None] | None:
    clean = str(query or "").strip().casefold().replace("\u00a0", " ")
    match = re.fullmatch(
        r"(монетка|монета|орёл|орел|кубик|кости)(?:\s+(.+))?",
        clean,
    )
    if not match:
        return None

    game_type = "coin" if match.group(1) in {"монетка", "монета", "орёл", "орел"} else "dice"
    raw_amount = match.group(2)
    if raw_amount is None or not raw_amount.strip():
        return game_type, None

    normalized = re.sub(r"[\s._,]", "", raw_amount)
    if not normalized.isdigit() or len(normalized) > 12:
        return None
    return game_type, int(normalized)


def install_bot_game_stake_limit_v135(core: Any) -> None:
    if getattr(core, "_bot_game_stake_limit_v135_installed", False):
        return
    core._bot_game_stake_limit_v135_installed = True
    core.BOT_GAME_STAKE_VERSION = VERSION
    core.BOT_GAME_MAX_STAKE = MAX_BOT_GAME_STAKE

    original_parser = core.parse_bot_game_query

    def parse_bot_game_query_v135(query: str):
        parsed = _parse_game_and_amount(query)
        return parsed if parsed is not None else original_parser(query)

    core.parse_bot_game_query = parse_bot_game_query_v135

    original_prepare = core.prepare_bot_game_result

    async def prepare_bot_game_result_v135(
        user: Any,
        game_type: str,
        stake: int | None,
        chat_id: int,
    ):
        if stake is not None and int(stake) > MAX_BOT_GAME_STAKE:
            title = (
                "🪙 Монетка против бота 🪙"
                if str(game_type) == "coin"
                else "🎲 Кубик против бота 🎲"
            )
            return core.inline_article(
                f"botgame_max:{game_type}:{user.id}:{secrets.token_hex(3)}",
                f"🚫 Максимальная ставка — {_formatted(MAX_BOT_GAME_STAKE)}",
                "Используется только обычное влияние",
                (
                    f"{title}\n\n"
                    f"Максимальная ставка: <b>{_formatted(MAX_BOT_GAME_STAKE)} "
                    "обычного влияния</b>.\n"
                    f"Ты попытался поставить: <b>{_formatted(int(stake))}</b>.\n\n"
                    "Уменьши ставку до миллиона или ниже."
                ),
            )
        return await original_prepare(user, game_type, stake, chat_id)

    core.prepare_bot_game_result = prepare_bot_game_result_v135

    original_create = core.Database.create_bot_game

    async def create_bot_game_v135(self: Any, *args: Any, **kwargs: Any):
        raw_stake = kwargs.get("stake")
        if raw_stake is None and args:
            raw_stake = args[-1]
        try:
            stake_value = int(raw_stake)
        except (TypeError, ValueError):
            raise ValueError("Некорректная ставка.")
        if stake_value < 1:
            raise ValueError("Минимальная ставка — 1 обычное влияние.")
        if stake_value > MAX_BOT_GAME_STAKE:
            raise ValueError(
                f"Максимальная ставка в кубике и монетке — {_formatted(MAX_BOT_GAME_STAKE)}."
            )
        return await original_create(self, *args, **kwargs)

    core.Database.create_bot_game = create_bot_game_v135
