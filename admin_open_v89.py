from __future__ import annotations

import time
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo


VERSION = "Reality 97 · Голосование событий"


def install_admin_open_v89(core: Any) -> None:
    if getattr(core, "_admin_open_v89_installed", False):
        return
    core._admin_open_v89_installed = True

    async def open_admin(message: Message, bot: Any) -> None:
        if not message.from_user or int(message.from_user.id) != int(core.DEVELOPER_ID):
            return
        if not core.WEBAPP_PUBLIC_URL:
            await message.answer("⚠️ Для админ-центра укажи WEBAPP_PUBLIC_URL.")
            return

        parts = (message.text or "").split(maxsplit=1)
        query = parts[1].strip() if len(parts) == 2 else ""
        target = None
        chat_id = 0

        if core.is_group(message):
            chat_id = int(message.chat.id)
            replied = message.reply_to_message.from_user if message.reply_to_message else None
            if replied and not replied.is_bot:
                target = await core.db.upsert_player(chat_id, replied)
            elif query:
                target = await core.db.admin_find_player(query, chat_id)
            else:
                target = await core.db.upsert_player(chat_id, message.from_user)
        else:
            if query:
                target = await core.db.admin_find_player(query)
            if target is None:
                target = await core.db.admin_latest_group_player(message.from_user.id)
            if target is not None:
                chat_id = int(target.chat_id)

        if target is None or not chat_id:
            await message.answer("⚠️ Сначала открой <code>/admin</code> в нужной групповой беседе.")
            return

        url = (
            f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/admin-v76/"
            f"?chat_id={chat_id}&user_id={int(target.user_id)}&build=97-{int(time.time())}"
        )
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="🛠 Открыть админ-центр Reality 97",
                    web_app=WebAppInfo(url=url),
                )
            ]]
        )
        try:
            await bot.send_message(
                message.from_user.id,
                "🛠 <b>АДМИН-ЦЕНТР REALITY 97</b>\n\n"
                f"Беседа: <code>{chat_id}</code>\n"
                f"Участник: <b>{target.full_name}</b>\n\n"
                "События теперь запускаются голосованием участников. После нужного "
                "количества голосов бот случайно выбирает участника дня и событие. "
                "Прогресс начислений обновляется почти сразу.",
                reply_markup=markup,
            )
        except Exception:
            await message.answer("⚠️ Открой личку бота, нажми /start и повтори команду.")
            return
        if core.is_group(message):
            await core.ephemeral_reply(
                message,
                "🔒 Админ-центр Reality 97 отправлен в личные сообщения.",
                delay_seconds=3,
            )

    core.open_admin_panel = open_admin

    # Старый обработчик /event был зарегистрирован раньше нового голосования.
    # Переносим Reality 97 в начало, чтобы Telegram не останавливался на старом ответе.
    handlers = core.router.message.handlers
    vote_handlers = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_event_vote_v97"
    ]
    handlers[:] = vote_handlers + [handler for handler in handlers if handler not in vote_handlers]
