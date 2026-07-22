from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import government_institutions_v128 as institutions
import government_mandate_luxury_v147 as luxury
import government_v127 as gov

from government_oversight_deputy_v167_data import OFFICE_KEY, OFFICE_SPEC, _access, _person, _routes


VERSION = "Reality 173 · Прямое назначение заместителя Президентом"
ASSET_JS = Path(__file__).resolve().parent / "governmentapp_v127" / "president-direct-deputy-v173.js"


async def _direct_appointment(
    core: Any,
    bot: Any,
    chat_id: int,
    actor_id: int,
    target_id: int,
    reason: str,
) -> dict[str, Any]:
    access = await _access(core, chat_id, actor_id)
    if not (access["is_admin"] or "president" in access["offices"]):
        raise PermissionError("Назначить заместителя напрямую может только Президент реальности.")

    candidate = await _person(core, chat_id, target_id)
    clean_reason = str(reason or "").strip()[:600] or "Личное кадровое решение Президента реальности."

    # Президент назначает напрямую и вправе обойти карьерный порог и санкционные ограничения.
    await gov._assign_office(
        core,
        chat_id,
        OFFICE_KEY,
        target_id,
        1,
        actor_id,
        term_seconds=gov.TERM_SECONDS,
    )
    await gov._publish(
        bot,
        chat_id,
        "🦅 <b>ПРЕЗИДЕНТСКОЕ НАЗНАЧЕНИЕ</b>\n\n"
        f"{OFFICE_SPEC['emoji']} <b>{html.escape(OFFICE_SPEC['title'])}</b>\n"
        f"Назначен: <b>{html.escape(str(candidate['name']))}</b>\n\n"
        f"Основание: {html.escape(clean_reason)}\n\n"
        "Назначение вступило в силу немедленно и не требует голосования Госдумы.",
    )
    return candidate


def install_government_president_direct_deputy_v173(core: Any) -> None:
    if getattr(core, "_government_president_direct_deputy_v173_installed", False):
        return
    core._government_president_direct_deputy_v173_installed = True
    core.GOVERNMENT_VERSION = VERSION

    previous_create_bill = gov._create_bill

    async def create_bill_with_presidential_appointment(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        author_id: int,
        bill_type: str,
        title: str,
        description: str,
        payload: dict[str, Any],
    ) -> str:
        office_key = str((payload or {}).get("office_key") or "")
        if bill_type == "appointment" and office_key == OFFICE_KEY:
            access = await _access(core_arg, chat_id, author_id)
            if access["is_admin"] or "president" in access["offices"]:
                target_id = gov._as_int((payload or {}).get("target_user_id"))
                await _direct_appointment(core_arg, bot, chat_id, author_id, target_id, description)
                return f"direct:{target_id}"
        return await previous_create_bill(
            core_arg,
            bot,
            chat_id,
            author_id,
            bill_type,
            title,
            description,
            payload,
        )

    gov._create_bill = create_bill_with_presidential_appointment

    previous_inject = luxury._inject_assets

    def inject(source: str) -> str:
        source = previous_inject(source)
        if ASSET_JS.name not in source:
            source = source.replace(
                "</body>",
                f'  <script src="/government-v173/{ASSET_JS.name}?v=173"></script>\n</body>',
            )
        return source

    luxury._inject_assets = inject

    async def direct_appointment_api(request: Any):
        try:
            user, chat_id, data = await gov._auth(core, request)
            actor_id = int(user.id)
            target_id = gov._as_int(data.get("target_user_id"))
            reason = str(data.get("reason") or "")
            candidate = await _direct_appointment(
                core,
                request.app["bot"],
                chat_id,
                actor_id,
                target_id,
                reason,
            )
            await institutions._log(
                core,
                chat_id,
                actor_id,
                "president",
                "direct_oversight_deputy_appointment",
                "Президентское назначение заместителя Надзора",
                reason or "Личное кадровое решение Президента",
                target_id,
                payload={"office_key": OFFICE_KEY, "direct": True},
            )
            return core.web.json_response(
                {
                    "ok": True,
                    "message": f"{candidate['name']} назначен заместителем главы Надзора без голосования Госдумы.",
                }
            )
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    original_start = core.start_webapp_server

    async def start(bot: Any):
        if not ASSET_JS.is_file():
            raise RuntimeError("Не найден интерфейс прямого президентского назначения Reality 173")
        original_runner = core.web.AppRunner

        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            if name != ASSET_JS.name:
                raise core.web.HTTPNotFound()
            return core.web.FileResponse(
                ASSET_JS,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Content-Type": "application/javascript; charset=utf-8",
                    "X-Government-President-Appointment": "173",
                },
            )

        def runner(app: Any, *args: Any, **kwargs: Any):
            keys = _routes(app)
            if ("GET", "/government-v173/{name}") not in keys:
                app.router.add_get("/government-v173/{name}", asset)
            if ("POST", "/government-v173/api/direct-appointment") not in keys:
                app.router.add_post(
                    "/government-v173/api/direct-appointment",
                    direct_appointment_api,
                )
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start
