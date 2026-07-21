from __future__ import annotations

from pathlib import Path
from typing import Any

import government_crisis_v131 as crisis
import government_institutions_v128 as institutions
import government_mandate_luxury_v147 as luxury
import government_v127 as gov


VERSION = "Reality 148 · Строгие полномочия должностей"
ASSET_JS = Path(__file__).resolve().parent / "governmentapp_v127" / "role-permissions-v148.js"
ASSET_CSS = Path(__file__).resolve().parent / "governmentapp_v127" / "role-permissions-v148.css"
_ORIGINAL_LUXURY_INJECT = luxury._inject_assets

POWER_ACTION_ROLES: dict[str, tuple[str, ...]] = {
    "decree": ("president",),
    "amnesty": ("president",),
    "appointment": ("president",),
    "extend_bill": ("chair",),
    "return_bill": ("chair",),
    "no_confidence": ("chair",),
    "amendment": ("deputy",),
    "inspection_request": ("deputy", "oversight"),
    "budget_report": ("finance",),
    "tax_refund": ("finance",),
    "debtors_report": ("finance",),
    "warning": ("oversight",),
    "open_case": ("oversight",),
    "court_case": ("supreme_court",),
    "court_ruling": ("supreme_court",),
    "court_compensation": ("supreme_court",),
    "investigation": ("prosecutor",),
    "suspend_official": ("prosecutor",),
    "treasury_audit": ("prosecutor", "auditor"),
    "tax_audit": ("prosecutor", "auditor"),
    "budget_audit": ("prosecutor", "auditor"),
    "economic_policy": ("central_bank",),
    "economic_mode": ("central_bank",),
    "economic_report": ("central_bank",),
    "cec_election": ("cec",),
    "recount": ("cec",),
    "disqualify": ("cec",),
    "case_refer": ("ombudsman", "prosecutor", "supreme_court"),
    "protection": ("ombudsman",),
    "public_appeal": ("ombudsman",),
    "security_meeting": ("security", "president"),
    "emergency": ("security", "president"),
    "security_report": ("security",),
    "statement": ("press",),
    "poll": ("press",),
    "daily_brief": ("press",),
}

BILL_TYPE_ROLES: dict[str, tuple[str, ...]] = {
    "general": ("president", "chair", "deputy", "finance", "oversight"),
    "tax_policy": ("president", "finance", "deputy"),
    "budget": ("president", "finance", "deputy"),
    "appointment": ("president",),
    "sanction": ("president", "oversight", "deputy"),
    "win_tax": ("president", "finance", "deputy"),
}

CRISIS_COUNTERINTEL_ROLES = ("president", "security", "prosecutor", "oversight")


def _role_titles(roles: tuple[str, ...]) -> str:
    return ", ".join(str(gov.OFFICES.get(role, {"title": role})["title"]) for role in roles)


async def _held_roles(core: Any, chat_id: int, user_id: int) -> set[str]:
    return set(await gov._user_offices(core, int(chat_id), int(user_id)))


async def _require_roles(
    core: Any,
    chat_id: int,
    user_id: int,
    roles: tuple[str, ...],
) -> str:
    held = await _held_roles(core, chat_id, user_id)
    for role in roles:
        if role in held:
            return role
    raise PermissionError(
        f"Это полномочие доступно только должности: {_role_titles(roles)}. "
        "Административный статус владельца бота не заменяет государственную должность."
    )


async def _strict_require_office(
    core: Any,
    chat_id: int,
    user_id: int,
    *offices: str,
) -> str:
    return await _require_roles(core, chat_id, user_id, tuple(offices))


async def _strict_council_member(core: Any, chat_id: int, user_id: int) -> Any:
    council = await crisis._council(core, chat_id)
    if council is None:
        raise PermissionError("Революционный совет сейчас не действует.")
    members = [int(value) for value in crisis._json(council["members_json"], [])]
    if int(user_id) not in members:
        raise PermissionError("Это действие доступно только участникам Революционного совета.")
    return council


def _inject_assets(source: str) -> str:
    source = _ORIGINAL_LUXURY_INJECT(source)
    if "role-permissions-v148.css" not in source:
        source = source.replace(
            "</head>",
            '  <link rel="stylesheet" href="/government-v127/role-permissions-v148.css?v=148">\n</head>',
        )
    if "role-permissions-v148.js" not in source:
        source = source.replace(
            "</body>",
            '  <script src="/government-v127/role-permissions-v148.js?v=148"></script>\n</body>',
        )
    return source


async def _check_core_action(
    core: Any,
    chat_id: int,
    user_id: int,
    data: dict[str, Any],
) -> None:
    action = str(data.get("action") or "")
    if action == "create_bill":
        bill_type = str(data.get("bill_type") or "general")
        roles = BILL_TYPE_ROLES.get(bill_type, BILL_TYPE_ROLES["general"])
        await _require_roles(core, chat_id, user_id, roles)
        return
    if action == "president_decision":
        await _require_roles(core, chat_id, user_id, ("president",))
        return
    if action == "override_veto":
        await _require_roles(core, chat_id, user_id, ("chair",))
        return
    if action in {"tax_toggle", "tax_run"}:
        await _require_roles(core, chat_id, user_id, ("president", "finance"))
        return
    if action == "vote_bill":
        await _require_roles(core, chat_id, user_id, ("deputy",))
        return
    if action == "start_election":
        office_key = str(data.get("office_key") or "")
        if office_key == "chair":
            await _require_roles(core, chat_id, user_id, ("deputy", "chair"))
            return
        if office_key in {"president", "deputy"}:
            current = await gov._office_rows(core, chat_id)
            if any(str(row["office_key"]) == office_key for row in current):
                raise PermissionError(
                    "Досрочные выборы нельзя запускать из обычной панели государства. "
                    "Для административного запуска используется отдельный админ-центр."
                )


async def _check_power_action(
    core: Any,
    chat_id: int,
    user_id: int,
    data: dict[str, Any],
) -> None:
    action = str(data.get("action") or "")
    if action == "submit_complaint":
        return
    roles = POWER_ACTION_ROLES.get(action)
    if roles:
        await _require_roles(core, chat_id, user_id, roles)


async def _check_crisis_action(
    core: Any,
    chat_id: int,
    user_id: int,
    data: dict[str, Any],
) -> None:
    action = str(data.get("action") or "")
    if action == "investigate_theft":
        await _require_roles(core, chat_id, user_id, tuple(crisis.INVESTIGATOR_OFFICES))
    elif action == "counterintel":
        await _require_roles(core, chat_id, user_id, CRISIS_COUNTERINTEL_ROLES)
    elif action.startswith("council_"):
        await _strict_council_member(core, chat_id, user_id)


def _sanitize_crisis_state(payload: dict[str, Any], held: set[str], user_id: int) -> None:
    state = payload.get("crisis_v131")
    if not isinstance(state, dict):
        return

    state["offices"] = list(held)
    can_investigate = bool(held & set(crisis.INVESTIGATOR_OFFICES))
    state["can_investigate"] = can_investigate

    theft = state.get("theft")
    if isinstance(theft, dict):
        for item in theft.get("items", []):
            if not isinstance(item, dict):
                continue
            item["can_investigate"] = bool(
                can_investigate
                and str(item.get("status") or "") == "pending"
                and not bool(item.get("investigated"))
            )
            if not bool(item.get("own")) and str(item.get("status") or "") != "caught":
                item["thief_id"] = 0
                item["thief_name"] = "Неизвестен"

    conflict = state.get("conflict")
    if isinstance(conflict, dict) and str(conflict.get("type") or "") == "coup":
        conspirator = bool(conflict.get("is_conspirator"))
        counterintel = bool(held & set(CRISIS_COUNTERINTEL_ROLES))
        if not conspirator and not counterintel:
            state["conflict"] = None
        else:
            conflict["can_counterintel"] = bool(counterintel and not conspirator)
            if not conspirator:
                conflict["members"] = []
                conflict["reason"] = "Засекречено"
                conflict["plot_score"] = 0

    council = state.get("council")
    if isinstance(council, dict):
        member_ids = {
            int(item.get("user_id"))
            for item in council.get("members", [])
            if isinstance(item, dict) and item.get("user_id") is not None
        }
        council["is_member"] = int(user_id) in member_ids


def install_government_role_permissions_v148(core: Any) -> None:
    if getattr(core, "_government_role_permissions_v148_installed", False):
        return
    core._government_role_permissions_v148_installed = True
    core.GOVERNMENT_VERSION = VERSION

    institutions._require_office = _strict_require_office
    crisis._require_council_member = _strict_council_member
    luxury._inject_assets = _inject_assets

    original_state = gov._state

    async def state_with_strict_roles(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        payload = await original_state(core_arg, bot, chat_id, user_id)
        roles = list(await gov._user_offices(core_arg, chat_id, user_id))
        held = set(roles)
        offices = payload.get("offices", [])

        payload["version"] = VERSION
        payload.setdefault("user", {})["offices"] = roles
        payload["user"]["is_admin"] = False
        payload["user"]["owner_admin"] = int(user_id) == int(core_arg.DEVELOPER_ID)
        payload["role_access"] = {
            "strict": True,
            "offices": roles,
            "owner_admin": int(user_id) == int(core_arg.DEVELOPER_ID),
        }
        permissions = dict(payload.get("permissions") or {})
        permissions.update(
            {
                "can_start_president": not any(item.get("office_key") == "president" for item in offices),
                "can_start_deputy": not any(item.get("office_key") == "deputy" for item in offices),
                "can_start_chair": bool(held & {"deputy", "chair"}),
                "can_create_bill": bool(held & {"president", "chair", "deputy", "finance", "oversight"}),
                "can_vote_bill": "deputy" in held,
                "can_president": "president" in held,
                "can_chair": "chair" in held,
                "can_manage_tax": bool(held & {"president", "finance"}),
                "can_propose_sanction": bool(held & {"president", "oversight", "deputy"}),
            }
        )
        payload["permissions"] = permissions

        institution_state = payload.get("institutions")
        if isinstance(institution_state, dict):
            powers: list[dict[str, Any]] = []
            for office in roles:
                spec = gov.OFFICES.get(office, {"title": office})
                for action in institutions.OFFICE_ACTIONS.get(office, []):
                    powers.append(
                        {
                            **action,
                            "office_key": office,
                            "office_title": str(spec["title"]),
                            "available": True,
                        }
                    )
            institution_state["version"] = VERSION
            institution_state["my_offices"] = roles
            institution_state["my_powers"] = powers
            institution_state["is_admin"] = False
            institution_state["owner_admin"] = int(user_id) == int(core_arg.DEVELOPER_ID)

        _sanitize_crisis_state(payload, held, user_id)
        return payload

    gov._state = state_with_strict_roles

    original_start = core.start_webapp_server

    async def start_with_strict_role_permissions(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты строгих полномочий Reality 148")
        original_runner = core.web.AppRunner

        @core.web.middleware
        async def strict_role_middleware(request: Any, handler: Any):
            path = str(request.path or "").rstrip("/") or "/"
            if request.method.upper() == "GET":
                if path == "/government-v127/role-permissions-v148.js":
                    return core.web.FileResponse(
                        ASSET_JS,
                        headers={"Cache-Control": "no-store", "X-Government-Roles": "strict-148"},
                    )
                if path == "/government-v127/role-permissions-v148.css":
                    return core.web.FileResponse(
                        ASSET_CSS,
                        headers={"Cache-Control": "no-store", "X-Government-Roles": "strict-148"},
                    )
            if request.method.upper() == "POST" and path in {
                "/government-v127/api/action",
                "/government-v128/api/action",
                "/government-v131/api/action",
            }:
                try:
                    user, chat_id, data = await gov._auth(core, request)
                    if path == "/government-v127/api/action":
                        await _check_core_action(core, chat_id, int(user.id), data)
                    elif path == "/government-v128/api/action":
                        await _check_power_action(core, chat_id, int(user.id), data)
                    else:
                        await _check_crisis_action(core, chat_id, int(user.id), data)
                except PermissionError as exc:
                    return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
                except Exception as exc:
                    return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)
            return await handler(request)

        def runner_with_strict_roles(app: Any, *args: Any, **kwargs: Any):
            app.middlewares.insert(0, strict_role_middleware)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_strict_roles
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_strict_role_permissions
