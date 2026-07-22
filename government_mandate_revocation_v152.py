from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Callable

from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import government_crisis_v131 as crisis
import government_mandate_luxury_v147 as luxury
import government_mandates_v143 as mandates
import government_v127 as gov


VERSION = "Reality 152 · Причины аннулирования мандатов"
APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "mandate-revocation-v152.js"
ASSET_CSS = APP_DIR / "mandate-revocation-v152.css"

LAW_HONEST_POWER = (1, "О честной государственной власти")
LAW_TREASURY = (7, "О государственной казне и бюджете")
LAW_CORRUPTION = (10, "О коррупции и злоупотреблении полномочиями")


def _route_keys(app: Any) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        result.add(
            (
                str(getattr(route, "method", "") or "").upper(),
                str(getattr(resource, "canonical", "") or ""),
            )
        )
    return result


def _row_value(row: Any, key: str, default: Any = "") -> Any:
    if row is None:
        return default
    try:
        keys = row.keys()
    except Exception:
        keys = []
    if key not in keys:
        return default
    value = row[key]
    return default if value is None else value


def _source_title(source: str) -> str:
    return {
        "law_violation": "Нарушение закона",
        "system": "Система",
        "impeachment": "Импичмент",
        "creator": "Решение создателя системы",
    }.get(str(source or ""), "Система")


def _meta_from_row(row: Any, status: str = "") -> dict[str, Any]:
    source = str(_row_value(row, "revocation_source", "") or "")
    reason = str(_row_value(row, "revocation_reason", "") or "")
    law_number = int(_row_value(row, "revocation_law_number", 0) or 0)
    law_title = str(_row_value(row, "revocation_law_title", "") or "")
    reference = str(_row_value(row, "revocation_reference", "") or "")
    revoked_at = int(_row_value(row, "revoked_at", 0) or 0)
    revoked_by = int(_row_value(row, "revoked_by", 0) or 0)

    if status == "annulled" and not reason:
        source = "system"
        reason = "Полномочия были досрочно прекращены государственной системой."
        law_number, law_title = LAW_HONEST_POWER

    return {
        "revocation_source": source,
        "revocation_source_title": _source_title(source),
        "revocation_reason": reason,
        "revocation_law_number": law_number,
        "revocation_law_title": law_title,
        "revocation_reference": reference,
        "revoked_at": revoked_at,
        "revoked_by": revoked_by,
    }


async def _ensure_schema(core: Any) -> None:
    if getattr(core.db, "_government_mandate_revocation_v152_schema", False):
        return
    await mandates._ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute("PRAGMA table_info(government_mandates_v143)")
    columns = {str(row["name"]) for row in await cursor.fetchall()}
    additions = {
        "revocation_source": "TEXT NOT NULL DEFAULT ''",
        "revocation_reason": "TEXT NOT NULL DEFAULT ''",
        "revocation_law_number": "INTEGER NOT NULL DEFAULT 0",
        "revocation_law_title": "TEXT NOT NULL DEFAULT ''",
        "revocation_reference": "TEXT NOT NULL DEFAULT ''",
        "revoked_by": "INTEGER NOT NULL DEFAULT 0",
    }
    async with core.db.lock:
        for name, definition in additions.items():
            if name not in columns:
                await conn.execute(
                    f"ALTER TABLE government_mandates_v143 ADD COLUMN {name} {definition}"
                )
        await conn.commit()
    core.db._government_mandate_revocation_v152_schema = True


async def _annotate_mandate(
    core: Any,
    mandate_no: int,
    *,
    revoked_at: int,
    source: str,
    reason: str,
    law_number: int,
    law_title: str,
    reference: str,
    revoked_by: int,
) -> None:
    await _ensure_schema(core)
    conn = core.db._require_connection()
    await conn.execute(
        """
        UPDATE government_mandates_v143
        SET revoked_at=CASE WHEN revoked_at>0 THEN revoked_at ELSE ? END,
            revocation_source=?,revocation_reason=?,revocation_law_number=?,
            revocation_law_title=?,revocation_reference=?,revoked_by=?
        WHERE mandate_no=?
        """,
        (
            int(revoked_at),
            str(source),
            str(reason),
            int(law_number),
            str(law_title),
            str(reference),
            int(revoked_by),
            int(mandate_no),
        ),
    )


async def _annul_for_theft(core: Any, theft: Any, investigator_id: int) -> list[int]:
    await _ensure_schema(core)
    chat_id = int(theft["chat_id"])
    thief_id = int(theft["thief_id"])
    amount = int(theft["amount"])
    percent = int(theft["percent"])
    theft_id = str(theft["theft_id"])
    caught_at = int(theft["caught_at"] or theft["resolved_at"] or crisis._now())
    conn = core.db._require_connection()

    cursor = await conn.execute(
        """
        SELECT mandate_no FROM government_mandates_v143
        WHERE chat_id=? AND user_id=?
          AND office_starts_at<=? AND office_ends_at>?
          AND NOT (revocation_source='law_violation' AND revocation_reference=?)
        """,
        (chat_id, thief_id, caught_at, caught_at, f"theft:{theft_id}"),
    )
    mandate_nos = [int(row["mandate_no"]) for row in await cursor.fetchall()]
    if not mandate_nos:
        return []

    reason = (
        f"Казнокрадство: хищение {gov._fmt(amount)} влияния "
        f"({percent}% государственной казны). Вина подтверждена расследованием. "
        f"Дополнительно нарушены требования Закона №{LAW_TREASURY[0]} "
        f"«{LAW_TREASURY[1]}»."
    )
    async with core.db.lock:
        for mandate_no in mandate_nos:
            await _annotate_mandate(
                core,
                mandate_no,
                revoked_at=caught_at,
                source="law_violation",
                reason=reason,
                law_number=LAW_CORRUPTION[0],
                law_title=LAW_CORRUPTION[1],
                reference=f"theft:{theft_id}",
                revoked_by=int(investigator_id),
            )
        await conn.commit()
    return mandate_nos


async def _backfill_annulments(core: Any, chat_id: int) -> None:
    await _ensure_schema(core)
    try:
        await crisis._ensure_schema(core)
    except Exception:
        pass
    conn = core.db._require_connection()
    now = mandates._now()
    cursor = await conn.execute(
        """
        SELECT m.* FROM government_mandates_v143 m
        WHERE m.chat_id=? AND COALESCE(m.revocation_reason,'')=''
          AND (m.revoked_at>0 OR (
            m.office_ends_at>? AND NOT EXISTS(
              SELECT 1 FROM government_offices_v127 o
              WHERE o.chat_id=m.chat_id AND o.user_id=m.user_id
                AND o.office_key=m.office_key AND o.seat_no=m.seat_no
                AND o.starts_at=m.office_starts_at AND o.ends_at>?
            )
          ))
        """,
        (int(chat_id), now, now),
    )
    rows = list(await cursor.fetchall())
    if not rows:
        return

    async with core.db.lock:
        for row in rows:
            cursor = await conn.execute(
                """
                SELECT * FROM government_thefts_v131
                WHERE chat_id=? AND thief_id=? AND status='caught'
                  AND caught_at>=? AND caught_at<=?
                ORDER BY caught_at DESC LIMIT 1
                """,
                (
                    int(row["chat_id"]),
                    int(row["user_id"]),
                    int(row["office_starts_at"]),
                    max(int(row["office_ends_at"]), now),
                ),
            )
            theft = await cursor.fetchone()
            if theft is not None:
                amount = int(theft["amount"])
                percent = int(theft["percent"])
                reason = (
                    f"Казнокрадство: хищение {gov._fmt(amount)} влияния "
                    f"({percent}% государственной казны). Вина подтверждена расследованием. "
                    f"Дополнительно нарушены требования Закона №{LAW_TREASURY[0]} "
                    f"«{LAW_TREASURY[1]}»."
                )
                await _annotate_mandate(
                    core,
                    int(row["mandate_no"]),
                    revoked_at=int(theft["caught_at"] or now),
                    source="law_violation",
                    reason=reason,
                    law_number=LAW_CORRUPTION[0],
                    law_title=LAW_CORRUPTION[1],
                    reference=f"theft:{str(theft['theft_id'])}",
                    revoked_by=int(theft["caught_by"] or 0),
                )
            else:
                await _annotate_mandate(
                    core,
                    int(row["mandate_no"]),
                    revoked_at=int(row["revoked_at"] or now),
                    source="system",
                    reason=(
                        "Досрочное прекращение государственных полномочий системой. "
                        "Мандат утратил силу до окончания первоначального срока."
                    ),
                    law_number=LAW_HONEST_POWER[0],
                    law_title=LAW_HONEST_POWER[1],
                    reference="system:auto",
                    revoked_by=0,
                )
        await conn.commit()


def _inject_assets(previous_inject: Callable[[str], str], source: str) -> str:
    source = previous_inject(source)
    if "mandate-revocation-v152.css" not in source:
        source = source.replace(
            "</head>",
            '  <link rel="stylesheet" href="/government-v152/mandate-revocation-v152.css?v=152">\n</head>',
        )
    if "mandate-revocation-v152.js" not in source:
        source = source.replace(
            "</body>",
            '  <script src="/government-v152/mandate-revocation-v152.js?v=152"></script>\n</body>',
        )
    return source


def _extend_foundation_laws() -> None:
    for law in mandates.FOUNDATION_LAWS:
        number = int(law.get("number") or 0)
        text = str(law.get("text") or "")
        if number == 4 and "причину аннулирования" not in text:
            law["text"] = (
                text
                + "\n\nАннулированный мандат обязан содержать источник решения, дату, "
                "причину прекращения полномочий и правовое основание, если аннулирование "
                "связано с нарушением закона."
            )
        if number == 10 and "Хищение средств государственной казны" not in text:
            law["text"] = (
                text
                + "\n\nХищение средств государственной казны является основанием для "
                "досрочного снятия со всех государственных должностей и аннулирования "
                "действующих мандатов виновного лица."
            )


def install_government_mandate_revocation_v152(core: Any) -> None:
    if getattr(core, "_government_mandate_revocation_v152_installed", False):
        return
    core._government_mandate_revocation_v152_installed = True
    core.GOVERNMENT_VERSION = VERSION
    _extend_foundation_laws()

    original_connect = core.Database.connect

    async def connect_with_revocation_schema(self: Any) -> None:
        await original_connect(self)
        core.db._government_mandate_revocation_v152_schema = False
        await _ensure_schema(core)

    core.Database.connect = connect_with_revocation_schema

    original_state = gov._state

    async def state_with_revocation(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        await _ensure_schema(core_arg)
        await _backfill_annulments(core_arg, chat_id)
        payload = await original_state(core_arg, bot, chat_id, user_id)
        payload["version"] = VERSION
        conn = core_arg.db._require_connection()
        for item in payload.get("mandates", []):
            mandate_id = str(item.get("mandate_id") or "")
            if not mandate_id:
                item.update(_meta_from_row(None, str(item.get("status") or "")))
                continue
            cursor = await conn.execute(
                "SELECT * FROM government_mandates_v143 WHERE mandate_id=? AND chat_id=?",
                (mandate_id, int(chat_id)),
            )
            row = await cursor.fetchone()
            item.update(_meta_from_row(row, str(item.get("status") or "")))
        return payload

    gov._state = state_with_revocation

    previous_catch = crisis._catch_theft

    async def catch_theft_with_mandate_reason(
        core_arg: Any,
        bot: Any,
        theft: Any,
        investigator_id: int,
        immediate: bool = False,
    ) -> None:
        await previous_catch(core_arg, bot, theft, investigator_id, immediate=immediate)
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            "SELECT * FROM government_thefts_v131 WHERE theft_id=?",
            (str(theft["theft_id"]),),
        )
        fresh = await cursor.fetchone()
        if fresh is None or str(fresh["status"]) != "caught":
            return
        affected = await _annul_for_theft(core_arg, fresh, investigator_id)
        if affected:
            await gov._publish(
                bot,
                int(fresh["chat_id"]),
                "📜 <b>ГОСУДАРСТВЕННЫЕ МАНДАТЫ АННУЛИРОВАНЫ</b>\n\n"
                f"Причина: <b>хищение средств государственной казны</b>.\n"
                f"Правовое основание: Закон Реальности №{LAW_CORRUPTION[0]} "
                f"«{html.escape(LAW_CORRUPTION[1])}».\n\n"
                "Причина и связанное дело внесены в государственный реестр.",
            )

    crisis._catch_theft = catch_theft_with_mandate_reason

    previous_inject = luxury._inject_assets

    def inject_with_revocation(source: str) -> str:
        return _inject_assets(previous_inject, source)

    luxury._inject_assets = inject_with_revocation

    original_start = core.start_webapp_server

    async def start_with_mandate_revocation(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты причин аннулирования Reality 152")
        original_runner = core.web.AppRunner

        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            if name == "mandate-revocation-v152.js":
                path = ASSET_JS
            elif name == "mandate-revocation-v152.css":
                path = ASSET_CSS
            else:
                raise core.web.HTTPNotFound()
            return core.web.FileResponse(
                path,
                headers={"Cache-Control": "no-store", "X-Government-Mandate-Revocation": "152"},
            )

        def runner_with_revocation(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/government-v152/{name}") not in keys:
                app.router.add_get("/government-v152/{name}", asset)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_revocation
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_mandate_revocation

    handlers = core.router.message.handlers
    obsolete = {"cmd_mandate_v143", "cmd_mandate_v147", "cmd_mandate_v152"}
    handlers[:] = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") not in obsolete
    ]

    @core.router.message(Command("mandate", "мандат"))
    async def cmd_mandate_v152(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        try:
            await core.db.upsert_player(int(message.chat.id), message.from_user)
            await _ensure_schema(core)
            target_id = await mandates._resolve_target(core, message)
            await _backfill_annulments(core, int(message.chat.id))
            row, status = await mandates._latest_mandate(
                core,
                int(message.chat.id),
                target_id,
            )
            if row is None:
                await message.answer("🏛 У этого участника нет оформленного государственного мандата.")
                return

            owner_label = await luxury._owner_label(core, int(message.chat.id), target_id)
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
            meta = _meta_from_row(row, status)
            revocation_text = ""
            if status == "annulled":
                legal = ""
                if int(meta["revocation_law_number"] or 0) > 0:
                    legal = (
                        f"\n<b>Правовое основание:</b> Закон Реальности №"
                        f"{int(meta['revocation_law_number'])} «"
                        f"{html.escape(str(meta['revocation_law_title']))}»"
                    )
                reference = ""
                if meta["revocation_reference"]:
                    reference = (
                        f"\n<b>Запись реестра:</b> <code>"
                        f"{html.escape(str(meta['revocation_reference']))}</code>"
                    )
                revoked_date = ""
                if int(meta["revoked_at"] or 0) > 0:
                    revoked_date = (
                        f"\n<b>Дата аннулирования:</b> "
                        f"{gov._date_text(int(meta['revoked_at']))}"
                    )
                revocation_text = (
                    "\n\n🚫 <b>ПРИЧИНА АННУЛИРОВАНИЯ</b>\n"
                    f"<b>Источник:</b> {html.escape(str(meta['revocation_source_title']))}\n"
                    f"<b>Причина:</b> {html.escape(str(meta['revocation_reason']))}"
                    f"{legal}{revoked_date}{reference}"
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
                f"<b>Код проверки:</b> <code>{html.escape(str(row['verification_code']))}</code>"
                f"{revocation_text}\n\n"
                f"<b>Исторически предоставленные полномочия:</b>\n{rights_text}\n\n"
                "⚖️ <b>Правовое основание выдачи</b>\n"
                "Закон Реальности №1 «О честной государственной власти». Мандат подтверждает, "
                "что полномочия были получены через установленную системой процедуру.\n\n"
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
        if getattr(handler.callback, "__name__", "") == "cmd_mandate_v152"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
