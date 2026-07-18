from __future__ import annotations

import re
import secrets
from typing import Any

from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup

from talent_system import TALENT_PREFIX, sync_profile


TALENT_MENU_MARKER = re.compile(r"#TALENT_MENU_(\d+)")


def install_menu(core: Any) -> None:
    """Добавляет древо в slash-команды и основное inline-меню бота."""
    if getattr(core, "_talent_menu_installed", False):
        return
    core._talent_menu_installed = True

    original_group_commands = core.group_bot_commands

    def group_commands_with_talent_entry() -> list[BotCommand]:
        commands = original_group_commands()
        if any(command.command == "talents" for command in commands):
            return commands
        insert_at = next(
            (
                index + 1
                for index, command in enumerate(commands)
                if command.command == "boss"
            ),
            len(commands),
        )
        commands.insert(
            insert_at,
            BotCommand(
                command="talents",
                description="Открыть древо развития",
            ),
        )
        return commands

    core.group_bot_commands = group_commands_with_talent_entry

    original_inline_menu_specs = core.inline_menu_specs

    def inline_menu_specs_with_talents(user: Any) -> list[dict[str, Any]]:
        specs = original_inline_menu_specs(user)
        if any(str(spec.get("result_id", "")).startswith("talent_menu:") for spec in specs):
            return specs

        specs.append(
            {
                "kind": "static",
                "result_id": f"talent_menu:{user.id}:{secrets.token_hex(3)}",
                "title": "🌳 Древо развития 🌳",
                "description": "Прокачка урона, влияния, защиты и наград",
                "message_text": (
                    "🌳 <b>ДРЕВО РАЗВИТИЯ</b> 🌳\n\n"
                    "Прокачивай урон по боссу, получение влияния, "
                    "защиту от штрафов и редкие награды.\n\n"
                    "Бот определяет беседу и готовит персональную кнопку…\n"
                    f"<tg-spoiler>#TALENT_MENU_{user.id}</tg-spoiler>"
                ),
            }
        )
        return specs

    core.inline_menu_specs = inline_menu_specs_with_talents

    original_dispatch = core.maybe_handle_inline_dispatch

    def talent_link(chat_id: int) -> str:
        if core.WEBAPP_SHORT_NAME:
            return (
                f"https://t.me/{core.BOT_PUBLIC_USERNAME}/"
                f"{core.WEBAPP_SHORT_NAME}?startapp={TALENT_PREFIX}{chat_id}"
            )
        if core.WEBAPP_PUBLIC_URL:
            return f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/talents/?chat_id={chat_id}"
        return ""

    async def dispatch_with_talent_menu(message: Any, bot: Any) -> bool:
        body = message.text or message.caption or ""
        match = TALENT_MENU_MARKER.search(body)
        if match is None:
            return await original_dispatch(message, bot)

        owner_id = int(match.group(1))
        if message.from_user is None or message.from_user.id != owner_id:
            return False

        chat_id = int(message.chat.id)
        await core.db.upsert_player(chat_id, message.from_user)
        await sync_profile(core.db, chat_id, owner_id)

        link = talent_link(chat_id)
        if not link:
            result_text = (
                "⚠️ <b>ДРЕВО РАЗВИТИЯ НЕ НАСТРОЕНО</b>\n\n"
                "Не указан адрес Telegram Mini App."
            )
            markup = None
        else:
            result_text = (
                "🌳 <b>ДРЕВО РАЗВИТИЯ</b> 🌳\n\n"
                "Прокачивай четыре направления:\n"
                "⚔️ урон по боссу;\n"
                "📈 получение влияния;\n"
                "🛡️ защиту от потерь;\n"
                "🎁 удачу и награды.\n\n"
                "Навыки сохраняются отдельно для этой беседы "
                "и сразу применяются ботом."
            )
            markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🌳 ОТКРЫТЬ ДРЕВО РАЗВИТИЯ",
                            url=link,
                        )
                    ]
                ]
            )

        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message.message_id,
                text=result_text,
                reply_markup=markup,
            )
        except Exception:
            await message.answer(result_text, reply_markup=markup)
        return True

    core.maybe_handle_inline_dispatch = dispatch_with_talent_menu
