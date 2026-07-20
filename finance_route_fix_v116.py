from __future__ import annotations

from typing import Any, Callable


VERSION = "Reality 116 · Надёжные маршруты Финансового центра"


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


def _add_finance_routes(app: Any, finance_index: Callable[..., Any], state_api: Callable[..., Any], action_api: Callable[..., Any]) -> None:
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
    add_post("/finance-v114/api/action", action_api)

    # Новые адреса оставлены как постоянные алиасы для будущих карточек.
    add_get("/finance", finance_index)
    add_get("/finance/", finance_index)
    add_get("/finance/api/state", state_api)
    add_post("/finance/api/action", action_api)


def install_finance_route_fix_v116(core: Any) -> None:
    if getattr(core, "_finance_route_fix_v116_installed", False):
        return
    core._finance_route_fix_v116_installed = True
    core.FINANCE_SYSTEM_VERSION = VERSION

    found = _find_finance_wrapper(core.start_webapp_server)
    if found is None:
        raise RuntimeError("Reality 116: не найдена обёртка маршрутов Финансового центра")

    _, values = found
    finance_index = values["finance_index"]
    state_api = values["state_api"]
    action_api = values["action_api"]
    base_start_server = values["original_start_server"]

    async def start_server_with_forced_finance_routes(bot: Any):
        original_app_runner = core.web.AppRunner

        def app_runner_factory(app: Any, *args: Any, **kwargs: Any):
            _add_finance_routes(app, finance_index, state_api, action_api)
            return original_app_runner(app, *args, **kwargs)

        core.web.AppRunner = app_runner_factory
        try:
            return await base_start_server(bot)
        finally:
            core.web.AppRunner = original_app_runner

    core.start_webapp_server = start_server_with_forced_finance_routes
