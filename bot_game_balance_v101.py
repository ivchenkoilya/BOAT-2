from __future__ import annotations

import random
from typing import Any


VERSION = "Reality 164 · Игрок 45 против бота 55"
PLAYER_WIN_CHANCE = 0.45
BOT_WIN_CHANCE = 0.55


def _coin_result() -> tuple[bool, str]:
    user_side = random.choice(["Орёл", "Решка"])
    won = random.random() < PLAYER_WIN_CHANCE
    result_side = user_side if won else ("Решка" if user_side == "Орёл" else "Орёл")
    detail = (
        f"Игрок выбрал: <b>{user_side}</b>.\n"
        f"Выпало: <b>{result_side}</b>."
    )
    return won, detail


def _dice_result() -> tuple[bool, str]:
    won = random.random() < PLAYER_WIN_CHANCE
    if won:
        pairs = [(user, bot) for user in range(2, 7) for bot in range(1, user)]
    else:
        pairs = [(user, bot) for user in range(1, 6) for bot in range(user + 1, 7)]
    user_roll, bot_roll = random.choice(pairs)
    detail = (
        f"Игрок: <b>{user_roll}</b>.\n"
        f"Бот: <b>{bot_roll}</b>."
    )
    return won, detail


def install_bot_game_balance_v101(core: Any) -> None:
    if getattr(core, "_bot_game_balance_v101_installed", False):
        return
    core._bot_game_balance_v101_installed = True

    @core.router.callback_query(core.F.data.startswith("botgame:"))
    async def handle_bot_game_v101(callback: Any, bot: Any) -> None:
        if not callback.data:
            return

        parts = callback.data.split(":")
        if len(parts) != 2:
            await callback.answer("Повреждённая игра.", show_alert=True)
            return

        _, game_id = parts
        game = await core.db.get_bot_game(game_id)
        if game is None:
            await callback.answer(
                "Эта игра уже растворилась в реальности.",
                show_alert=True,
            )
            return

        owner_id = int(game["owner_id"])
        game_type = str(game["game_type"])
        stake = int(game["stake"])
        chat_id = int(game["chat_id"])

        if callback.from_user.id != owner_id:
            await callback.answer(
                "Играть должен тот, кто поставил очки.",
                show_alert=True,
            )
            return

        claimed = await core.db.claim_bot_game(game_id, owner_id)
        if not claimed:
            await callback.answer("Эта партия уже завершена.", show_alert=True)
            return

        player = await core.db.get_player(chat_id, owner_id)
        if player is None or player.points < stake:
            current = player.points if player else 0
            result_text = (
                "🚫 <b>ИГРА ОТМЕНЕНА</b> 🚫\n\n"
                f"Для ставки нужно <b>{stake}</b>, "
                f"а у игрока осталось <b>{current}</b>."
            )
            await core.db.finish_bot_game(game_id, result_text)
        else:
            before = player.points
            if game_type == "coin":
                won, detail = _coin_result()
            else:
                won, detail = _dice_result()

            delta = stake if won else -stake
            _, after = await core.db.add_points_with_balance(
                chat_id,
                owner_id,
                delta,
                f"bot_game_{game_type}",
            )
            applied = after.points - before

            # Защитные таланты могут уменьшать проигрыш, но не могут полностью
            # отменить его. Если Древо вернуло −0, принудительно снимаем 1 очко.
            if not won and applied >= 0:
                _, after = await core.db.set_player_points(
                    chat_id,
                    owner_id,
                    before - 1,
                    f"bot_game_{game_type}_minimum_loss",
                )
                applied = after.points - before

            if won:
                outcome = (
                    "👑 Бот официально унижен. "
                    "Ты забираешь его воображаемые деньги."
                )
            else:
                outcome = (
                    "💀 Сегодня бот удержал ставку. "
                    "Даже Древо знаний не может полностью отменить проигрыш."
                )

            title = (
                "🪙 МОНЕТКА ПРОТИВ БОТА 🪙"
                if game_type == "coin"
                else "🎲 КУБИК ПРОТИВ БОТА 🎲"
            )
            signed = (
                f"+{applied}"
                if applied > 0
                else "0"
                if applied == 0
                else f"−{abs(applied)}"
            )
            result_text = (
                f"<b>{title}</b>\n\n"
                f"{core.player_link(after)}\n"
                f"{detail}\n\n"
                f"{outcome}\n\n"
                f"🍀 Шанс победы игрока: <b>45%</b>.\n"
                f"🤖 Шанс победы бота: <b>55%</b>.\n"
                f"Ставка: <b>{stake}</b>.\n"
                f"Изменение: <b>{signed}</b>.\n"
                f"Баланс: <b>{before} → {after.points}</b>."
            )
            await core.db.finish_bot_game(game_id, result_text)

        if callback.inline_message_id:
            await bot.edit_message_text(
                inline_message_id=callback.inline_message_id,
                text=result_text,
                parse_mode=core.ParseMode.HTML,
            )
        elif callback.message:
            await callback.message.edit_text(
                result_text,
                parse_mode=core.ParseMode.HTML,
            )

        await callback.answer("Игра завершена!")

    # Старый обработчик с шансом 50/50 уже зарегистрирован в main.py.
    # Этот слой должен обрабатывать кнопку первым, иначе изменения не применятся.
    handlers = core.router.callback_query.handlers
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "handle_bot_game_v101"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
