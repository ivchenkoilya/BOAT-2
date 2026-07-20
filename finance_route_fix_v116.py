from __future__ import annotations

from typing import Any, Callable


VERSION = "Reality 117 · История и улучшенный Финансовый центр"


def _closure_values(function: Any) -> dict[str, Any]:
    code = getattr(function, "__code__", None)
    cells = getattr(function, "__closure__", None)
    if code is None or not cells:
        return {}
    return {
        name: cell.cell_contents
        for name, cell in zip(code.co_freevars, cells)
    }


def _find_finance_wrapper(function: Any, visited: set[int] | None = None) -> tuple[Any, dict[str, Any]] | None:
    if visited is None:
        visited = set()
    marker = id(function)
    if marker in visited:
        return None
    visited.add(marker)

    values = _closure_values(function)
    required = {"finance_index", "state_api", "action_api", "original_start_server"}
    if required.issubset(values):
        return function, values

    for value in values.values():
        if callable(value):
            found = _find_finance_wrapper(value, visited)
            if found is not None:
                return found
    return None


def _route_keys(app: Any) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        canonical = str(getattr(resource, "canonical", "") or "")
        result.add((str(getattr(route, "method", "") or "").upper(), canonical))
    return result


def _parse_finance_chat_id(start_param: str | None, request: Any) -> int:
    raw = str(start_param or request.query.get("chat_id") or "").strip()
    if raw.startswith("finance_"):
        raw = raw[8:]
    try:
        chat_id = int(raw)
    except (TypeError, ValueError):
        raise ValueError("Не найдена беседа для финансовой истории.")
    if chat_id >= 0:
        raise ValueError("Финансовый центр работает только в групповой беседе.")
    return chat_id


def _history_handler(core: Any) -> Callable[..., Any]:
    async def finance_history(request: Any):
        user, start_param = core._webapp_auth(request)
        if user is None:
            return core.web.json_response(
                {"ok": False, "reason": start_param or "Нет авторизации Telegram."},
                status=401,
            )
        try:
            chat_id = _parse_finance_chat_id(start_param, request)
        except ValueError as error:
            return core.web.json_response({"ok": False, "reason": str(error)}, status=400)

        player = await core.db.get_player(chat_id, int(user.id))
        if player is None:
            return core.web.json_response(
                {"ok": False, "reason": "Сначала используй бота в нужной беседе."},
                status=403,
            )

        conn = core.db._require_connection()
        items: list[dict[str, Any]] = []
        user_id = int(user.id)

        cursor = await conn.execute(
            """
            SELECT t.*,
                   COALESCE(s.full_name,'Участник') sender_name,
                   COALESCE(r.full_name,'Участник') recipient_name
            FROM finance_transfers_v112 t
            LEFT JOIN players s ON s.chat_id=t.chat_id AND s.user_id=t.sender_id
            LEFT JOIN players r ON r.chat_id=t.chat_id AND r.user_id=t.recipient_id
            WHERE t.chat_id=? AND t.status='completed'
              AND (t.sender_id=? OR t.recipient_id=?)
            ORDER BY COALESCE(t.completed_at,t.created_at) DESC
            LIMIT 16
            """,
            (chat_id, user_id, user_id),
        )
        for row in await cursor.fetchall():
            outgoing = int(row["sender_id"]) == user_id
            items.append(
                {
                    "kind": "transfer_out" if outgoing else "transfer_in",
                    "title": "Перевод отправлен" if outgoing else "Перевод получен",
                    "other_name": str(row["recipient_name"] if outgoing else row["sender_name"]),
                    "amount": -int(row["amount"]) if outgoing else int(row["amount"]),
                    "created_at": int(row["completed_at"] or row["created_at"]),
                    "status": "completed",
                }
            )

        cursor = await conn.execute(
            """
            SELECT p.*,
                   COALESCE(a.full_name,'Участник') payer_name,
                   COALESCE(b.full_name,'Участник') receiver_name
            FROM finance_payments_v112 p
            LEFT JOIN players a ON a.chat_id=p.chat_id AND a.user_id=p.payer_id
            LEFT JOIN players b ON b.chat_id=p.chat_id AND b.user_id=p.receiver_id
            WHERE p.chat_id=? AND (p.payer_id=? OR p.receiver_id=?)
            ORDER BY p.created_at DESC
            LIMIT 16
            """,
            (chat_id, user_id, user_id),
        )
        for row in await cursor.fetchall():
            outgoing = int(row["payer_id"]) == user_id
            automatic = str(row["payment_type"]) == "automatic"
            items.append(
                {
                    "kind": "repay_out" if outgoing else "repay_in",
                    "title": (
                        "Автопогашение долга" if outgoing and automatic
                        else "Погашение долга" if outgoing
                        else "Автовозврат долга" if automatic
                        else "Получен платёж"
                    ),
                    "other_name": str(row["receiver_name"] if outgoing else row["payer_name"]),
                    "amount": -int(row["amount"]) if outgoing else int(row["amount"]),
                    "created_at": int(row["created_at"]),
                    "status": "completed",
                }
            )

        cursor = await conn.execute(
            """
            SELECT l.*,
                   COALESCE(a.full_name,'Участник') lender_name,
                   COALESCE(b.full_name,'Участник') borrower_name
            FROM finance_loans_v112 l
            LEFT JOIN players a ON a.chat_id=l.chat_id AND a.user_id=l.lender_id
            LEFT JOIN players b ON b.chat_id=l.chat_id AND b.user_id=l.borrower_id
            WHERE l.chat_id=? AND (l.lender_id=? OR l.borrower_id=?)
              AND l.status IN ('active','overdue','repaid')
            ORDER BY COALESCE(l.accepted_at,l.created_at) DESC
            LIMIT 12
            """,
            (chat_id, user_id, user_id),
        )
        for row in await cursor.fetchall():
            lender_view = int(row["lender_id"]) == user_id
            status = str(row["status"])
            items.append(
                {
                    "kind": "loan_out" if lender_view else "loan_in",
                    "title": "Заём выдан" if lender_view else "Заём получен",
                    "other_name": str(row["borrower_name"] if lender_view else row["lender_name"]),
                    "amount": -int(row["principal"]) if lender_view else int(row["principal"]),
                    "created_at": int(row["accepted_at"] or row["created_at"]),
                    "status": status,
                    "detail": f"{int(row['interest_percent'])}% · вернуть {int(row['total_due'])}",
                }
            )

        items.sort(key=lambda item: int(item["created_at"]), reverse=True)
        return core.web.json_response({"ok": True, "items": items[:14]})

    return finance_history


def _add_finance_routes(
    app: Any,
    finance_index: Callable[..., Any],
    state_api: Callable[..., Any],
    action_api: Callable[..., Any],
    history_api: Callable[..., Any],
) -> None:
    keys = _route_keys(app)

    def add_get(path: str, handler: Callable[..., Any]) -> None:
        if ("GET", path) not in keys and ("*", path) not in keys:
            app.router.add_get(path, handler)
            keys.add(("GET", path))

    def add_post(path: str, handler: Callable[..., Any]) -> None:
        if ("POST", path) not in keys and ("*", path) not in keys:
            app.router.add_post(path, handler)
            keys.add(("POST", path))

    add_get("/finance-v114", finance_index)
    add_get("/finance-v114/", finance_index)
    add_get("/finance-v114/index.html", finance_index)
    add_get("/finance-v114/api/state", state_api)
    add_get("/finance-v114/api/history", history_api)
    add_post("/finance-v114/api/action", action_api)

    add_get("/finance", finance_index)
    add_get("/finance/", finance_index)
    add_get("/finance/api/state", state_api)
    add_get("/finance/api/history", history_api)
    add_post("/finance/api/action", action_api)


def install_finance_route_fix_v116(core: Any) -> None:
    if getattr(core, "_finance_route_fix_v116_installed", False):
        return
    core._finance_route_fix_v116_installed = True
    core.FINANCE_SYSTEM_VERSION = VERSION

    found = _find_finance_wrapper(core.start_webapp_server)
    if found is None:
        raise RuntimeError("Reality 117: не найдена обёртка маршрутов Финансового центра")

    _, values = found
    finance_index = values["finance_index"]
    state_api = values["state_api"]
    action_api = values["action_api"]
    base_start_server = values["original_start_server"]
    history_api = _history_handler(core)

    async def start_server_with_forced_finance_routes(bot: Any):
        original_app_runner = core.web.AppRunner

        def app_runner_factory(app: Any, *args: Any, **kwargs: Any):
            _add_finance_routes(app, finance_index, state_api, action_api, history_api)
            return original_app_runner(app, *args, **kwargs)

        core.web.AppRunner = app_runner_factory
        try:
            return await base_start_server(bot)
        finally:
            core.web.AppRunner = original_app_runner

    core.start_webapp_server = start_server_with_forced_finance_routes
