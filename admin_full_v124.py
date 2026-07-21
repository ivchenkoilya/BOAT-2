from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo


VERSION = "Reality 124 · Полный карьерный админ-центр"
BASE_DIR = Path(__file__).resolve().parent
LEGACY_HTML = BASE_DIR / "adminapp_v76" / "index.html"
FULL_SCRIPT = BASE_DIR / "adminapp_v124" / "full-career.js"


def _route_keys(app: Any) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        canonical = str(getattr(resource, "canonical", "") or "")
        keys.add((str(getattr(route, "method", "") or "").upper(), canonical))
    return keys


def _full_html() -> str:
    source = LEGACY_HTML.read_text(encoding="utf-8")
    source = source.replace(
        "<title>Админ-центр Reality 89</title>",
        "<title>Админ-центр Reality 124</title>",
    )
    source = source.replace(
        '<strong id="versionText">Reality 89</strong>',
        '<strong id="versionText">Reality 124</strong>',
    )
    source = source.replace(
        '<div class="loading" id="loading"><div class="spinner"></div><b>Загрузка Reality 89</b><span>Синхронизируем участников, игры и древо</span></div>',
        '<div class="loading" id="loading"><div class="spinner"></div><b>Загрузка Reality 124</b><span>Синхронизируем карьеру, игры, рейд, древо, события и финансы</span></div>',
    )
    old_scripts = (
        '<script src="/admin-v89/admin-v89.js?v=89"></script>\n'
        '  <script src="/admin-v76/admin.js?v=89"></script>'
    )
    new_scripts = (
        '<script src="/admin-v89/admin-v89.js?v=124"></script>\n'
        '  <script src="/admin-v95/night-hunter-admin.js?v=124"></script>\n'
        '  <script src="/admin-v96/events-admin.js?v=124"></script>\n'
        '  <script src="/admin-v96/reward-editor.js?v=124"></script>\n'
        '  <script src="/admin-v112/finance-admin.js?v=124"></script>\n'
        '  <script src="/admin-v124/full-career.js?v=124"></script>\n'
        '  <script src="/admin-v76/admin.js?v=124"></script>'
    )
    source = source.replace(old_scripts, new_scripts)
    return source


def install_admin_full_v124(core: Any) -> None:
    if getattr(core, "_admin_full_v124_installed", False):
        return
    core._admin_full_v124_installed = True
    core.ADMIN_CENTER_VERSION = VERSION

    original_start_server = core.start_webapp_server

    async def index(_: Any):
        return core.web.Response(
            text=_full_html(),
            content_type="text/html",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Admin-Center": "reality-124",
            },
        )

    async def full_script(_: Any):
        return core.web.FileResponse(
            FULL_SCRIPT,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "X-Admin-Center": "reality-124",
            },
        )

    async def start_server_with_admin_v124(bot: Any):
        if not LEGACY_HTML.is_file() or not FULL_SCRIPT.is_file():
            raise RuntimeError("Не найдены файлы полного админ-центра Reality 124")
        original_runner = core.web.AppRunner

        def runner_factory(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)

            def add_get(path: str, handler: Any) -> None:
                if ("GET", path) not in keys and ("*", path) not in keys:
                    app.router.add_get(path, handler)
                    keys.add(("GET", path))

            add_get("/admin-v124", index)
            add_get("/admin-v124/", index)
            add_get("/admin-v124/full-career.js", full_script)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_server_with_admin_v124

    async def open_admin_v124(message: Message, bot: Any) -> None:
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
            await message.answer(
                "⚠️ Сначала открой <code>/admin</code> в нужной групповой беседе."
            )
            return

        url = (
            f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/admin-v124/"
            f"?chat_id={chat_id}&user_id={int(target.user_id)}&build=124-{int(time.time())}"
        )
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(
                text="🛠 Открыть полный админ-центр Reality 124",
                web_app=WebAppInfo(url=url),
            )]]
        )
        try:
            await bot.send_message(
                message.from_user.id,
                "🛠 <b>ПОЛНЫЙ АДМИН-ЦЕНТР REALITY 124</b>\n\n"
                f"Беседа: <code>{chat_id}</code>\n"
                f"Участник: <b>{target.full_name}</b>\n\n"
                "Возвращены игры, рейд, Древо, события, финансы, история и все "
                "инструменты Reality 76. Карьерное влияние и постоянные роли "
                "управляются отдельно от обычного баланса.",
                reply_markup=markup,
            )
        except Exception:
            await message.answer("⚠️ Открой личку бота, нажми /start и повтори команду.")
            return

        if core.is_group(message):
            await core.ephemeral_reply(
                message,
                "🔒 Полный админ-центр Reality 124 отправлен в личные сообщения.",
                delay_seconds=3,
            )

    core.open_admin_panel = open_admin_v124
