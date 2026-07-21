from __future__ import annotations

from typing import Any

import government_crisis_v131 as crisis
import government_v127 as gov


VERSION = "Reality 131 · Надёжный вход и расследования"


async def investigate_theft_with_real_risk(
    core: Any,
    bot: Any,
    chat_id: int,
    user_id: int,
    theft_id: str,
) -> str:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_thefts_v131 WHERE theft_id=? AND chat_id=?",
        (str(theft_id), int(chat_id)),
    )
    theft = await cursor.fetchone()
    if (
        theft is None
        or str(theft["status"]) != "pending"
        or int(theft["resolve_at"]) <= crisis._now()
    ):
        raise ValueError("Эта операция уже закрыта.")

    offices = await crisis._offices(core, chat_id, user_id)
    office = next(
        (key for key in crisis.INVESTIGATOR_OFFICES if key in offices),
        "",
    )
    if int(user_id) == int(core.DEVELOPER_ID):
        office = "auditor"
    if not office:
        raise PermissionError(
            "Расследование доступно Надзору, прокуратуре, Минфину, "
            "Счётной палате, Совбезу и ЦБ."
        )

    cursor = await conn.execute(
        "SELECT 1 FROM government_theft_investigations_v131 "
        "WHERE theft_id=? AND investigator_id=?",
        (str(theft_id), int(user_id)),
    )
    if await cursor.fetchone() is not None:
        raise ValueError("Ты уже проводил проверку этой операции.")

    prior = int(theft["investigations"] or 0)
    detection_risk = int(theft["detection_risk"] or 50)
    risk_modifier = (detection_risk - 50) // 2
    chance = max(
        5,
        min(
            95,
            crisis.INVESTIGATION_CHANCES.get(office, 20)
            + prior * 5
            + risk_modifier,
        ),
    )
    roll = crisis.secrets.randbelow(100) + 1
    success = roll <= chance
    now = crisis._now()

    await conn.execute(
        "INSERT INTO government_theft_investigations_v131("
        "theft_id,investigator_id,office_key,chance,roll,success,created_at"
        ") VALUES(?,?,?,?,?,?,?)",
        (
            str(theft_id),
            int(user_id),
            office,
            chance,
            roll,
            1 if success else 0,
            now,
        ),
    )
    await conn.execute(
        "UPDATE government_thefts_v131 SET investigations=investigations+1 "
        "WHERE theft_id=?",
        (str(theft_id),),
    )
    await conn.commit()

    if success:
        await crisis._catch_theft(core, bot, theft, user_id)
        return (
            f"Следы найдены. Шанс проверки был {chance}%. "
            "Виновник раскрыт, деньги возвращены."
        )
    return (
        f"Проверка не нашла достаточных доказательств. "
        f"Шанс обнаружения был {chance}%."
    )


def install_government_crisis_hotfix_v131(core: Any) -> None:
    if getattr(core, "_government_crisis_hotfix_v131_installed", False):
        return
    core._government_crisis_hotfix_v131_installed = True

    crisis._investigate_theft = investigate_theft_with_real_risk

    original_respond = crisis._respond_coup_invite

    async def respond_coup_invite_without_deadlock(
        core_value: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
        conflict_id: str,
        accept: bool,
    ) -> str:
        message = await original_respond(
            core_value,
            bot,
            chat_id,
            user_id,
            conflict_id,
            accept,
        )
        if accept:
            return message

        conn = core_value.db._require_connection()
        cursor = await conn.execute(
            "SELECT COUNT(*) amount FROM government_conflict_members_v131 "
            "WHERE conflict_id=? AND side='conspirator' AND status='accepted'",
            (str(conflict_id),),
        )
        accepted = int((await cursor.fetchone())["amount"])
        if accepted < 2:
            await conn.execute(
                "UPDATE government_conflicts_v131 SET "
                "stage='resolved',outcome='invitation_declined',resolved_at=? "
                "WHERE conflict_id=? AND stage='recruiting'",
                (crisis._now(), str(conflict_id)),
            )
            await conn.commit()
            return (
                "Приглашение отклонено. Заговор распущен, организатор может "
                "создать новый и выбрать другого сообщника."
            )
        return message

    crisis._respond_coup_invite = respond_coup_invite_without_deadlock

    @core.web.middleware
    async def government_reality_131_entry(request: Any, handler: Any):
        if request.method.upper() == "GET":
            path = str(request.path or "")
            start_param = str(
                request.query.get("tgWebAppStartParam")
                or request.query.get("startapp")
                or ""
            )
            if (
                path in {"/government-v127", "/government-v127/"}
                or start_param.startswith(gov.GOV_PREFIX)
            ):
                source = (crisis.APP_DIR / "index.html").read_text(
                    encoding="utf-8"
                )
                if "crisis-v131.css" not in source:
                    source = source.replace(
                        '<link rel="stylesheet" '
                        'href="/government-v127/powers-v128.css?v=128">',
                        '<link rel="stylesheet" '
                        'href="/government-v127/powers-v128.css?v=128">\n'
                        '  <link rel="stylesheet" '
                        'href="/government-v131/crisis-v131.css?v=131">',
                    )
                if "crisis-v131.js" not in source:
                    source = source.replace(
                        '<script src="/government-v127/'
                        'powers-v128.js?v=128"></script>',
                        '<script src="/government-v127/'
                        'powers-v128.js?v=128"></script>\n'
                        '  <script src="/government-v131/'
                        'crisis-v131.js?v=131"></script>',
                    )
                source = source.replace("REALITY 128", "REALITY 131")
                return core.web.Response(
                    text=source,
                    content_type="text/html",
                    charset="utf-8",
                    headers={
                        "Cache-Control": (
                            "no-store, no-cache, must-revalidate, max-age=0"
                        ),
                        "Pragma": "no-cache",
                        "Expires": "0",
                        "X-Government": "reality-131-hotfix",
                    },
                )
        return await handler(request)

    previous_application = core.web.Application

    def application_with_reality_131_entry(*args: Any, **kwargs: Any):
        application = previous_application(*args, **kwargs)
        application.middlewares.insert(0, government_reality_131_entry)
        return application

    core.web.Application = application_with_reality_131_entry
