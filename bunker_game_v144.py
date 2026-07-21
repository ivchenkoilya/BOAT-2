from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from aiogram.filters import Command
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message


VERSION = "Reality 145 · Bunker Stable Route"
GAME_PATH = Path(__file__).resolve().parent / "games" / "bunker"
ADMIN_PIN = "6767"


def _bunker_link(core: Any, chat_id: int) -> str:
    if core.WEBAPP_PUBLIC_URL:
        return (
            f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/games/bunker/"
            f"?chat_id={int(chat_id)}&build=145-{int(time.time())}"
        )
    if core.WEBAPP_SHORT_NAME and core.BOT_PUBLIC_USERNAME:
        return (
            f"https://t.me/{core.BOT_PUBLIC_USERNAME}/"
            f"{core.WEBAPP_SHORT_NAME}?startapp=games_{int(chat_id)}"
        )
    return ""


def install_bunker_game_v144(core: Any) -> None:
    """Подключает команду и карточку тестовой игры «Бункер».

    HTTP-маршруты регистрирует отдельный финальный слой
    ``bunker_route_fix_v145``. Это исключает потерю маршрута в длинной
    цепочке серверных расширений.
    """
    if getattr(core, "_bunker_game_v144_installed", False):
        return
    core._bunker_game_v144_installed = True

    original_group_commands = core.group_bot_commands

    def group_commands_with_bunker() -> list[BotCommand]:
        commands = original_group_commands()
        if any(command.command == "bunker" for command in commands):
            return commands
        commands.append(BotCommand(command="bunker", description="Классическая игра Бункер"))
        return commands

    core.group_bot_commands = group_commands_with_bunker

    @core.router.message(Command("bunker"))
    async def cmd_bunker(message: Message) -> None:
        if not await core.require_group_command(message, "Бункер"):
            return
        if not message.from_user:
            return
        chat_id = int(message.chat.id)
        await core.db.upsert_player(chat_id, message.from_user)
        link = _bunker_link(core, chat_id)
        if not link:
            await message.answer("⚠️ Адрес Mini App не настроен.")
            return
        await message.answer(
            "☢️ <b>БУНКЕР · ТЕСТОВЫЙ СТОЛ</b>\n\n"
            "Отдельная визуальная Mini App: игроки сидят вокруг стола, "
            "раскрытые характеристики остаются лежать перед ними, доступны "
            "чат, голосование и проверка микрофона.\n\n"
            "🔐 Доступ к текущей сборке закрыт админ-PIN <b>6767</b>.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="☢️ ВОЙТИ В БУНКЕР", url=link)
                ]]
            ),
        )
