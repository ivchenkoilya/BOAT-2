from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import government_crisis_v131 as crisis
import government_institutions_v128 as institutions
import government_mandate_luxury_v147 as luxury
import government_role_permissions_v148 as role_permissions
import government_v127 as gov


VERSION = "Reality 151 · Контроль создателя"
APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "creator-control-v151.js"
ASSET_CSS = APP_DIR / "creator-control-v151.css"


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


def _with_assets(previous_inject: Callable[[str], str], source: str) -> str:
    source = previous_inject(source)
    if "creator-control-v151.css" not in source:
        source = source.replace(
            "</head>",
            '  <link rel="stylesheet" href="/government-v151/creator-control-v151.css?v=151">\n</head>',
        )
    if "creator-control-v151.js" not in source:
        source = source.replace(
            "</body>",
            '  <script src="/government-v151/creator-control-v151.js?v=151"></script>\n</body>',
        )
    return source


def _all_institution_powers() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for office_key, actions in institutions.OFFICE_ACTIONS.items():
        spec = gov.OFFICES.get(office_key, {"title": office_key})
        for action in actions:
            action_key = str(action.get("key") or "")
            marker = (str(office_key), action_key)
            if marker in seen:
                continue
            seen.add(marker)
            result.append(
                {
                    **action,
                    "office_key": str(office_key),
                    "office_title": str(spec.get("title") or office_key),
                    "available": True,
                    "creator_override": True,
                }
            )
    return result


def install_government_creator_control_v151(core: Any) -> None:
    if getattr(core, "_government_creator_control_v151_installed", False):
        return
    core._government_creator_control_v151_installed = True
    core.GOVERNMENT_VERSION = VERSION

    previous_require_roles = role_permissions._require_roles
    previous_core_check = role_permissions._check_core_action
    previous_power_check = role_permissions._check_power_action
    previous_crisis_check = role_permissions._check_crisis_action
    previous_council_member = role_permissions._strict_council_member
    previous_sanitize = role_permissions._sanitize_crisis_state
    previous_crisis_offices = crisis._offices

    async def require_roles_with_creator(
        core_arg: Any,
        chat_id: int,
        user_id: int,
        roles: tuple[str, ...],
    ) -> str:
        if int(user_id) == int(core_arg.DEVELOPER_ID):
            return str(roles[0] if roles else "creator")
        return await previous_require_roles(core_arg, chat_id, user_id, roles)

    async def check_core_with_creator(
        core_arg: Any,
        chat_id: int,
        user_id: int,
        data: dict[str, Any],
    ) -> None:
        if int(user_id) == int(core_arg.DEVELOPER_ID):
            return
        await previous_core_check(core_arg, chat_id, user_id, data)

    async def check_power_with_creator(
        core_arg: Any,
        chat_id: int,
        user_id: int,
        data: dict[str, Any],
    ) -> None:
        if int(user_id) == int(core_arg.DEVELOPER_ID):
            return
        await previous_power_check(core_arg, chat_id, user_id, data)

    async def check_crisis_with_creator(
        core_arg: Any,
        chat_id: int,
        user_id: int,
        data: dict[str, Any],
    ) -> None:
        if int(user_id) == int(core_arg.DEVELOPER_ID):
            return
        await previous_crisis_check(core_arg, chat_id, user_id, data)

    async def council_member_with_creator(core_arg: Any, chat_id: int, user_id: int) -> Any:
        if int(user_id) == int(core_arg.DEVELOPER_ID):
            council = await crisis._council(core_arg, chat_id)
            if council is None:
                raise PermissionError("Революционный совет сейчас не действует.")
            return council
        return await previous_council_member(core_arg, chat_id, user_id)

    async def crisis_offices_with_creator(core_arg: Any, chat_id: int, user_id: int) -> list[str]:
        offices = list(await previous_crisis_offices(core_arg, chat_id, user_id))
        if int(user_id) == int(core_arg.DEVELOPER_ID):
            for office_key in gov.OFFICES:
                if office_key not in offices:
                    offices.append(str(office_key))
        return offices

    def sanitize_with_creator(payload: dict[str, Any], held: set[str], user_id: int) -> None:
        owner_admin = bool((payload.get("user") or {}).get("owner_admin"))
        if not owner_admin:
            previous_sanitize(payload, held, user_id)
            return

        state = payload.get("crisis_v131")
        if not isinstance(state, dict):
            return
        state["offices"] = list(held)
        state["can_investigate"] = True
        theft = state.get("theft")
        if isinstance(theft, dict):
            for item in theft.get("items", []):
                if not isinstance(item, dict):
                    continue
                item["can_investigate"] = bool(
                    str(item.get("status") or "") == "pending"
                    and not bool(item.get("investigated"))
                )
        conflict = state.get("conflict")
        if isinstance(conflict, dict) and str(conflict.get("type") or "") == "coup":
            conflict["can_counterintel"] = True
        council = state.get("council")
        if isinstance(council, dict):
            council["is_member"] = True
            council["creator_override"] = True

    role_permissions._require_roles = require_roles_with_creator
    role_permissions._check_core_action = check_core_with_creator
    role_permissions._check_power_action = check_power_with_creator
    role_permissions._check_crisis_action = check_crisis_with_creator
    role_permissions._strict_council_member = council_member_with_creator
    role_permissions._sanitize_crisis_state = sanitize_with_creator
    institutions._require_office = role_permissions._strict_require_office
    crisis._require_council_member = council_member_with_creator
    crisis._offices = crisis_offices_with_creator

    previous_inject = luxury._inject_assets

    def inject_with_creator(source: str) -> str:
        return _with_assets(previous_inject, source)

    luxury._inject_assets = inject_with_creator

    original_state = gov._state

    async def state_with_creator_control(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        payload = await original_state(core_arg, bot, chat_id, user_id)
        payload["version"] = VERSION
        is_owner = int(user_id) == int(core_arg.DEVELOPER_ID)
        payload.setdefault("user", {})["owner_admin"] = is_owner
        payload.setdefault("role_access", {})["owner_admin"] = is_owner
        payload["role_access"]["creator_control"] = is_owner
        if not is_owner:
            return payload

        payload["user"]["is_admin"] = True
        payload["creator_control_v151"] = {
            "active": True,
            "title": "Создатель системы",
            "can_view_all": True,
            "can_intervene": True,
        }

        permissions = dict(payload.get("permissions") or {})
        permissions.update(
            {
                "can_start_president": True,
                "can_start_deputy": True,
                "can_start_chair": True,
                "can_create_bill": True,
                "can_vote_bill": True,
                "can_president": True,
                "can_chair": True,
                "can_manage_tax": True,
                "can_propose_sanction": True,
            }
        )
        payload["permissions"] = permissions

        institution_state = payload.get("institutions")
        if isinstance(institution_state, dict):
            institution_state["my_powers"] = _all_institution_powers()
            institution_state["is_admin"] = True
            institution_state["owner_admin"] = True
            institution_state["creator_control"] = True

        return payload

    gov._state = state_with_creator_control

    async def asset(request: Any):
        name = str(request.match_info.get("name") or "")
        if name == "creator-control-v151.js":
            path = ASSET_JS
        elif name == "creator-control-v151.css":
            path = ASSET_CSS
        else:
            raise core.web.HTTPNotFound()
        return core.web.FileResponse(
            path,
            headers={"Cache-Control": "no-store", "X-Government-Creator-Control": "151"},
        )

    original_start = core.start_webapp_server

    async def start_with_creator_control(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты контроля создателя Reality 151")
        original_runner = core.web.AppRunner

        def runner_with_creator_control(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/government-v151/{name}") not in keys:
                app.router.add_get("/government-v151/{name}", asset)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_creator_control
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_creator_control
