from __future__ import annotations

from typing import Any

import government_institutions_v128 as institutions


VERSION = "Reality 128 · Защита экономической политики"


def install_government_economy_hotfix_v128(core: Any) -> None:
    if getattr(core, "_government_economy_hotfix_v128_installed", False):
        return
    core._government_economy_hotfix_v128_installed = True

    @core.web.middleware
    async def loan_request_policy(request: Any, handler: Any):
        path = str(request.path or "").casefold()
        if request.method.upper() != "POST" or "/finance-v118/api/request" not in path:
            return await handler(request)
        try:
            data = await request.json()
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
        user, start_param = core._webapp_auth(request)
        chat_id = institutions._parse_finance_chat(start_param, request, data)
        if user is None or chat_id >= 0:
            return await handler(request)
        policy = await institutions._policy(core, chat_id)
        amount = max(0, institutions._as_int(data.get("amount")))
        if amount > int(policy["loan_limit"]):
            return core.web.json_response(
                {
                    "ok": False,
                    "reason": (
                        "Центральный банк ограничил новые заявки на заём суммой "
                        f"{institutions._fmt(int(policy['loan_limit']))}."
                    ),
                },
                status=403,
            )
        return await handler(request)

    previous_application = core.web.Application

    def application_with_request_policy(*args: Any, **kwargs: Any):
        middlewares = list(kwargs.pop("middlewares", []) or [])
        kwargs["middlewares"] = [loan_request_policy, *middlewares]
        return previous_application(*args, **kwargs)

    core.web.Application = application_with_request_policy
