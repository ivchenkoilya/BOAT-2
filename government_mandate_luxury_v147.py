from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import government_mandates_v143 as mandates
import government_v127 as gov


VERSION = "Reality 147 · Премиальные государственные мандаты"
ASSET_JS = Path(__file__).resolve().parent / "governmentapp_v127" / "mandate-luxury-v147.js"
ASSET_CSS = Path(__file__).resolve().parent / "governmentapp_v127" / "mandate-luxury-v147.css"


async def _owner_label(core: Any, chat_id: int, user_id: int) -> str:
    """Return the current Telegram display name stored for this chat.

    The stable Telegram ID remains in the database and verification code, but the
    public face of the mandate shows the human-readable current Telegram name.
    """
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT full_name,username
        FROM players
        WHERE chat_id=? AND user_id=?
        LIMIT 1
        """,
        (int(chat_id), int(user_id)),
    )
    row = await cursor.fetchone()
    if row is not None:
        full_name = str(row["full_name"] or "").strip()
        if full_name:
            return full_name
        username = str(row["username"] or "").strip().lstrip("@")
        if username:
            return f"@{username}"
    return "Пользователь Telegram"


def _inject_assets(source: str) -> str:
    if "mandates-v143.css" not in source:
        source = source.replace(
            "</head>",
            '  <link rel="stylesheet" href="/government-v127/mandates-v143.css?v=143">\n</head>',
        )
    if "mandate-luxury-v147.css" not in source:
        source = source.replace(
            "</head>",
            '  <link rel="stylesheet" href="/government-v127/mandate-luxury-v147.css?v=147">\n</head>',
        )
    if "mandates-v143.js" not in source:
        source = source.replace(
            "</body>",
            '  <script src="/government-v127/mandates-v143.js?v=143"></script>\n</body>',
        )
    if "mandate-luxury-v147.js" not in source:
        source = source.replace(
            "</body>",
            '  <script src="/government-v127/mandate-luxury-v147.js?v=147"></script>\n</body>',
        )
    return source


def install_government_mandate_luxury_v147(core: Any) -> None:
    if getattr(core, "_government_mandate_luxury_v147_installed", False):
        return
    core._government_mandate_luxury_v147_installed = True
    core.GOVERNMENT_VERSION = VERSION

    original_state = gov._state

    async def state_with_owner_name(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        payload = await original_state(core_arg, bot, chat_id, user_id)
        owner_label = await _owner_label(core_arg, chat_id, user_id)
        payload["version"] = VERSION
        payload["mandate_owner_label"] = owner_label
        for item in payload.get("mandates", []):
            item["owner_label"] = owner_label
        return payload

    gov._state = state_with_owner_name

    original_start = core.start_webapp_server

    async def start_with_luxury_mandate(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены премиальные ассеты мандата Reality 147")

        original_runner = core.web.AppRunner

        @core.web.middleware
        async def luxury_mandate_middleware(request: Any, handler: Any):
            path = str(request.path or "").rstrip("/") or "/"
            if request.method.upper() == "GET":
                start_param = str(
                    request.query.get("tgWebAppStartParam")
                    or request.query.get("startapp")
                    or ""
                )
                if path == "/government-v127" or start_param.startswith(gov.GOV_PREFIX):
                    source = (gov.APP_DIR / "index.html").read_text(encoding="utf-8")
                    source = _inject_assets(source)
                    return core.web.Response(
                        text=source,
                        content_type="text/html",
                        charset="utf-8",
                        headers={
                            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                            "Pragma": "no-cache",
                            "Expires": "0",
                            "X-Government-Mandate": "luxury-147",
                        },
                    )
                if path == "/government-v127/mandate-luxury-v147.js":
                    return core.web.FileResponse(
                        ASSET_JS,
                        headers={"Cache-Control": "no-store", "X-Government-Mandate": "luxury-147"},
                    )
                if path == "/government-v127/mandate-luxury-v147.css":
                    return core.web.FileResponse(
                        ASSET_CSS,
                        headers={"Cache-Control": "no-store", "X-Government-Mandate": "luxury-147"},
                    )
            return await handler(request)

        def runner_with_luxury_mandate(app: Any, *args: Any, **kwargs: Any):
            app.middlewares.insert(0, luxury_mandate_middleware)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_luxury_mandate
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_luxury_mandate

    handlers = core.router.message.handlers
    obsolete = {"cmd_mandate_v143", "cmd_mandate_v147"}
    handlers[:] = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") not in obsolete
    ]

    @core.router.message(Command("mandate", "мандат"))
    async def cmd_mandate_v147(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        try:
            await core.db.upsert_player(int(message.chat.id), message.from_user)
            target_id = await mandates._resolve_target(core, message)
            row, status = await mandates._latest_mandate(
                core,
                int(message.chat.id),
                target_id,
            )
            if row is None:
                await message.answer("🏛 У этого участника нет оформленного государственного мандата.")
                return

            owner_label = await _owner_label(core, int(message.chat.id), target_id)
            spec = mandates._office_spec(str(row["office_key"]))
            powers = mandates.MANDATE_POWERS.get(str(row["office_key"]), [])
            status_line = {
                "active": "🟢 Действующий",
                "expired": "⚪ Срок полномочий завершён",
                "annulled": "🔴 Аннулирован",
            }.get(status, status)
            rights_text = "\n".join(f"— {html.escape(item)};" for item in powers)
            validity = (
                "Все перечисленные полномочия действуют в полном объёме."
                if status == "active"
                else "Полномочия больше не действуют. Документ сохранён только в государственном архиве."
            )
            link = mandates._mandate_link(core, int(message.chat.id))
            markup = None
            if link:
                markup = InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(
                            text="📜 Открыть государственный реестр",
                            url=link,
                        )
                    ]]
                )

            await message.answer(
                f"🏛 <b>МАНДАТ ГОСУДАРСТВА №{int(row['mandate_no']):06d}</b>\n\n"
                f"<b>Владелец:</b> {html.escape(owner_label)}\n"
                f"<b>Должность:</b> {spec['emoji']} {html.escape(str(spec['title']))}\n"
                f"<b>Срок:</b> {gov._date_text(int(row['office_starts_at']))} — "
                f"{gov._date_text(int(row['office_ends_at']))}\n"
                f"<b>Статус:</b> {status_line}\n"
                f"<b>Подпись:</b> 🔏 подтверждена\n"
                f"<b>Код проверки:</b> <code>{html.escape(str(row['verification_code']))}</code>\n\n"
                f"<b>Мандат предоставляет право:</b>\n{rights_text}\n\n"
                "⚖️ <b>Правовое основание</b>\n"
                "Закон Реальности №1 «О честной государственной власти». Мандат подтверждает, "
                "что полномочия получены через установленную системой процедуру и принадлежат "
                "указанному владельцу.\n\n"
                f"{validity}\n\n"
                "🔏 <b>Подлинность подтверждена государственным реестром системы «Главный Герой».</b>",
                reply_markup=markup,
            )
        except Exception as exc:
            await message.answer(f"⚠️ {html.escape(str(exc))}")

    handlers = core.router.message.handlers
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_mandate_v147"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
