from __future__ import annotations

import time
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

import admin_election_force_voting_v141 as force_voting
import admin_full_v124 as admin_full


VERSION = "Reality 142 · Свежий админ-центр"
ADMIN_PATHS = {
    "/admin-v76",
    "/admin-v124",
    "/admin-v126",
    "/admin-v132",
    "/admin-v142",
}


def _fresh_html() -> str:
    source = admin_full._full_html()

    # Старый интерфейс каждые 800 мс возвращал надпись Reality 132.
    # Меняем и статический текст, и встроенный таймер на актуальную версию.
    source = source.replace("REALITY 132", "REALITY 142")
    source = source.replace("Reality 132", "Reality 142")
    source = source.replace("reality-132c", "reality-142")
    source = source.replace("v=132c", "v=142")

    # Кнопка перехода к голосованию встраивается напрямую в фактический HTML,
    # даже если предыдущая цепочка обёрток admin_full._full_html не сработала.
    if "reality141ForceVotingPanel" not in source:
        source = source.replace(
            "</body>",
            f"  <script>{force_voting.PANEL_SCRIPT}</script>\n</body>",
        )

    version_script = """
<script>
(()=>{
  const apply=()=>{
    const node=document.getElementById('versionText');
    if(node)node.textContent='Reality 142 · Мгновенное голосование';
  };
  apply();
  setInterval(apply,500);
})();
</script>
""".strip()
    if "Reality 142 · Мгновенное голосование" not in source:
        source = source.replace("</body>", f"  {version_script}\n</body>")
    return source


def install_admin_fresh_v142(core: Any) -> None:
    if getattr(core, "_admin_fresh_v142_installed", False):
        return
    core._admin_fresh_v142_installed = True
    core.ADMIN_CENTER_VERSION = VERSION

    original_start = core.start_webapp_server

    async def start_with_fresh_admin(bot: Any):
        original_runner = core.web.AppRunner

        @core.web.middleware
        async def fresh_admin_index(request: Any, handler: Any):
            path = str(request.path or "").rstrip("/") or "/"
            if request.method.upper() == "GET" and path in ADMIN_PATHS:
                return core.web.Response(
                    text=_fresh_html(),
                    content_type="text/html",
                    charset="utf-8",
                    headers={
                        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                        "Pragma": "no-cache",
                        "Expires": "0",
                        "X-Admin-Center": "reality-142",
                    },
                )
            return await handler(request)

        async def index(_: Any):
            return core.web.Response(
                text=_fresh_html(),
                content_type="text/html",
                charset="utf-8",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Admin-Center": "reality-142",
                },
            )

        def runner_with_fresh_admin(app: Any, *args: Any, **kwargs: Any):
            app.middlewares.insert(0, fresh_admin_index)
            keys = {
                (
                    str(getattr(route, "method", "") or "").upper(),
                    str(getattr(getattr(route, "resource", None), "canonical", "") or ""),
                )
                for route in app.router.routes()
            }
            if ("GET", "/admin-v142") not in keys:
                app.router.add_get("/admin-v142", index)
            if ("GET", "/admin-v142/") not in keys:
                app.router.add_get("/admin-v142/", index)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_fresh_admin
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_fresh_admin

    async def open_admin_v142(message: Message, bot: Any) -> None:
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
            f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/admin-v142/"
            f"?chat_id={chat_id}&user_id={int(target.user_id)}&build=142-{int(time.time())}"
        )
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(
                text="🛠 Открыть админ-центр Reality 142",
                web_app=WebAppInfo(url=url),
            )]]
        )
        try:
            await bot.send_message(
                message.from_user.id,
                "🛠 <b>АДМИН-ЦЕНТР REALITY 142</b>\n\n"
                f"Беседа: <code>{chat_id}</code>\n"
                f"Участник: <b>{target.full_name}</b>\n\n"
                "Добавлена кнопка мгновенного перехода от выдвижения к голосованию.",
                reply_markup=markup,
            )
        except Exception:
            await message.answer("⚠️ Открой личку бота, нажми /start и повтори команду.")
            return

        if core.is_group(message):
            await core.ephemeral_reply(
                message,
                "🔒 Админ-центр Reality 142 отправлен в личные сообщения.",
                delay_seconds=3,
            )

    core.open_admin_panel = open_admin_v142
