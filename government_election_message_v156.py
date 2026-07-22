from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Callable

import government_election_shadow_v153 as shadow
import government_mandate_luxury_v147 as luxury
import government_v127 as gov


VERSION = "Reality 156 · Подкуп голосов"
APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "election-message-v156.js"
ASSET_CSS = APP_DIR / "election-message-v156.css"
MESSAGE_MAX_LENGTH = 300


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


async def _ensure_message_schema(core: Any) -> None:
    await shadow._ensure_schema(core)
    if getattr(core.db, "_government_election_message_v156_schema", False):
        return
    conn = core.db._require_connection()
    async with core.db.lock:
        cursor = await conn.execute("PRAGMA table_info(government_vote_bribes_v153)")
        columns = {str(row["name"]) for row in await cursor.fetchall()}
        if "secret_message" not in columns:
            await conn.execute(
                "ALTER TABLE government_vote_bribes_v153 "
                "ADD COLUMN secret_message TEXT NOT NULL DEFAULT ''"
            )
        await conn.commit()
    core.db._government_election_message_v156_schema = True


async def _save_offer_message(
    core: Any,
    election_id: str,
    buyer_id: int,
    target_id: int,
    secret_message: str,
) -> str:
    await _ensure_message_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT offer_id FROM government_vote_bribes_v153
        WHERE election_id=? AND buyer_id=? AND target_id=?
        ORDER BY created_at DESC LIMIT 1
        """,
        (str(election_id), int(buyer_id), int(target_id)),
    )
    row = await cursor.fetchone()
    if row is None:
        raise ValueError("Созданное предложение не найдено.")
    await conn.execute(
        "UPDATE government_vote_bribes_v153 SET secret_message=? WHERE offer_id=?",
        (str(secret_message), str(row["offer_id"])),
    )
    await conn.commit()
    return str(row["offer_id"])


async def _send_secret_message(bot: Any, target_id: int, secret_message: str) -> None:
    if not secret_message:
        return
    try:
        await bot.send_message(
            int(target_id),
            "😈 <b>СКРЫТОЕ СООБЩЕНИЕ КАНДИДАТА</b>\n\n"
            f"{html.escape(secret_message)}\n\n"
            "Личность отправителя скрыта до завершения выборов.",
        )
    except Exception:
        pass


def _inject_assets(previous_inject: Callable[[str], str], source: str) -> str:
    source = previous_inject(source)
    if ASSET_CSS.name not in source:
        source = source.replace(
            "</head>",
            f'  <link rel="stylesheet" href="/government-v156/{ASSET_CSS.name}?v=156">\n</head>',
        )
    if ASSET_JS.name not in source:
        source = source.replace(
            "</body>",
            f'  <script src="/government-v156/{ASSET_JS.name}?v=156"></script>\n</body>',
        )
    return source


def install_government_election_message_v156(core: Any) -> None:
    if getattr(core, "_government_election_message_v156_installed", False):
        return
    core._government_election_message_v156_installed = True
    core.GOVERNMENT_VERSION = VERSION

    original_connect = core.Database.connect

    async def connect_with_message_schema(self: Any) -> None:
        await original_connect(self)
        core.db._government_election_message_v156_schema = False
        await _ensure_message_schema(core)

    core.Database.connect = connect_with_message_schema

    original_shadow_state = shadow._shadow_state

    async def shadow_state_with_messages(
        core_arg: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        await _ensure_message_schema(core_arg)
        payload = await original_shadow_state(core_arg, chat_id, user_id)
        incoming = payload.get("incoming_offers", [])
        offer_ids = [str(item.get("offer_id") or "") for item in incoming if item.get("offer_id")]
        if offer_ids:
            conn = core_arg.db._require_connection()
            placeholders = ",".join("?" for _ in offer_ids)
            cursor = await conn.execute(
                f"SELECT offer_id,secret_message FROM government_vote_bribes_v153 "
                f"WHERE target_id=? AND offer_id IN ({placeholders})",
                (int(user_id), *offer_ids),
            )
            messages = {
                str(row["offer_id"]): str(row["secret_message"] or "")
                for row in await cursor.fetchall()
            }
            for item in incoming:
                item["secret_message"] = messages.get(str(item.get("offer_id") or ""), "")
        payload["version"] = VERSION
        payload["offer_duration_rule"] = "until_election_end"
        return payload

    shadow._shadow_state = shadow_state_with_messages

    previous_inject = luxury._inject_assets

    def inject_with_message(source: str) -> str:
        return _inject_assets(previous_inject, source)

    luxury._inject_assets = inject_with_message

    async def action_api(request: Any):
        try:
            user, chat_id, data = await gov._auth(core, request)
            action = str(data.get("action") or "")
            if action != "bribe_create_message":
                raise ValueError("Неизвестное действие Reality 156.")

            election_id = str(data.get("election_id") or "")
            target_id = int(data.get("target_user_id") or 0)
            amount = int(data.get("amount") or 0)
            secret_message = " ".join(str(data.get("secret_message") or "").split()).strip()
            if len(secret_message) > MESSAGE_MAX_LENGTH:
                raise ValueError(
                    f"Скрытое сообщение должно быть не длиннее {MESSAGE_MAX_LENGTH} символов."
                )

            bot = request.app["bot"]
            message = await shadow._create_bribe_offer(
                core,
                bot,
                chat_id,
                int(user.id),
                election_id,
                target_id,
                amount,
            )
            await _save_offer_message(
                core,
                election_id,
                int(user.id),
                target_id,
                secret_message,
            )
            await _send_secret_message(bot, target_id, secret_message)
            return core.web.json_response(
                {
                    "ok": True,
                    "message": message.replace("один час", "до завершения выборов"),
                }
            )
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    original_start = core.start_webapp_server

    async def start_with_election_message(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты подкупа голосов Reality 156")
        original_runner = core.web.AppRunner

        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            if name == ASSET_JS.name:
                path = ASSET_JS
            elif name == ASSET_CSS.name:
                path = ASSET_CSS
            else:
                raise core.web.HTTPNotFound()
            return core.web.FileResponse(
                path,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Government-Election-Message": "156",
                },
            )

        def runner_with_election_message(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/government-v156/{name}") not in keys:
                app.router.add_get("/government-v156/{name}", asset)
            if ("POST", "/government-v156/api/action") not in keys:
                app.router.add_post("/government-v156/api/action", action_api)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_election_message
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_election_message
