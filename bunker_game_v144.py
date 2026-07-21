from __future__ import annotations

import secrets
import time
from pathlib import Path
from typing import Any

from aiohttp import web
from aiogram.filters import Command
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message


VERSION = "Reality 144 · Bunker Table Prototype"
GAME_PATH = Path(__file__).resolve().parent / "games" / "bunker"
ADMIN_PIN = "6767"
_UNLOCK_TOKENS: dict[str, int] = {}


def _bunker_link(core: Any, chat_id: int) -> str:
    if core.WEBAPP_PUBLIC_URL:
        return (
            f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/games/bunker/"
            f"?chat_id={int(chat_id)}&build=144-{int(time.time())}"
        )
    if core.WEBAPP_SHORT_NAME and core.BOT_PUBLIC_USERNAME:
        return (
            f"https://t.me/{core.BOT_PUBLIC_USERNAME}/"
            f"{core.WEBAPP_SHORT_NAME}?startapp=games_{int(chat_id)}"
        )
    return ""


def install_bunker_game_v144(core: Any) -> None:
    """Подключает тестовый визуальный прототип классической игры «Бункер»."""
    if getattr(core, "_bunker_game_v144_installed", False):
        return
    core._bunker_game_v144_installed = True

    def response_headers() -> dict[str, str]:
        return {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Bunker-Game": VERSION,
        }

    async def bunker_index(_: web.Request) -> web.StreamResponse:
        return core.web.FileResponse(
            GAME_PATH / "index.html",
            headers=response_headers(),
        )

    async def unlock_bunker(request: web.Request) -> web.StreamResponse:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        pin = str(payload.get("pin") or "").strip()
        if pin != ADMIN_PIN:
            return core.web.json_response(
                {"ok": False, "reason": "Неверный PIN-код."},
                status=403,
                headers=response_headers(),
            )
        token = secrets.token_urlsafe(24)
        _UNLOCK_TOKENS[token] = int(time.time()) + 12 * 60 * 60
        now = int(time.time())
        expired = [key for key, expires_at in _UNLOCK_TOKENS.items() if expires_at <= now]
        for key in expired:
            _UNLOCK_TOKENS.pop(key, None)
        return core.web.json_response(
            {"ok": True, "token": token, "version": VERSION},
            headers=response_headers(),
        )

    async def verify_bunker(request: web.Request) -> web.StreamResponse:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        token = str(payload.get("token") or "")
        valid = bool(token and _UNLOCK_TOKENS.get(token, 0) > int(time.time()))
        return core.web.json_response(
            {"ok": valid, "version": VERSION},
            status=200 if valid else 403,
            headers=response_headers(),
        )

    original_start_server = core.start_webapp_server

    async def start_server_with_bunker(bot: Any):
        previous_application = core.web.Application

        def application_factory(*args: Any, **kwargs: Any):
            app = previous_application(*args, **kwargs)
            for path in (
                "/games/bunker",
                "/games/bunker/",
                "/games/bunker/index.html",
            ):
                app.router.add_get(path, bunker_index)
            app.router.add_post("/games/bunker/api/unlock", unlock_bunker)
            app.router.add_post("/games/bunker/api/verify", verify_bunker)
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = previous_application

    core.start_webapp_server = start_server_with_bunker

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
            "🔐 Доступ к текущей сборке закрыт админ-PIN.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="☢️ ВОЙТИ В БУНКЕР", url=link)
                ]]
            ),
        )
