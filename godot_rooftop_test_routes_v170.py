from __future__ import annotations

import logging
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
TARGET_DIR = BASE_DIR / "games" / "rooftop-godot-test"
PRIMARY_PREFIX = "/godot-rooftop-test"
LEGACY_PREFIX = "/games/rooftop-godot-test"


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


def _content_type(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix == ".html":
        return "text/html; charset=utf-8"
    if suffix == ".js":
        return "application/javascript; charset=utf-8"
    if suffix == ".wasm":
        return "application/wasm"
    if suffix == ".pck":
        return "application/octet-stream"
    if suffix == ".png":
        return "image/png"
    if suffix == ".svg":
        return "image/svg+xml"
    if suffix == ".json":
        return "application/json; charset=utf-8"
    return "application/octet-stream"


def install_godot_rooftop_test_routes(core: Any) -> None:
    """Expose the runtime Godot build through explicit aiohttp routes.

    The existing game server only knows its original game folders, so creating a
    new directory at runtime is not sufficient. These routes serve the test build
    and all relative Godot assets from both the new stable prefix and the old
    `/games/...` prefix used by already cached game-center pages.
    """
    if getattr(core, "_godot_rooftop_test_routes_v170_installed", False):
        return
    core._godot_rooftop_test_routes_v170_installed = True

    original_start = core.start_webapp_server

    async def start_with_godot_test_routes(bot: Any):
        original_runner = core.web.AppRunner

        async def redirect_primary(request: Any):
            suffix = f"?{request.query_string}" if request.query_string else ""
            raise core.web.HTTPFound(location=f"{PRIMARY_PREFIX}/{suffix}")

        async def redirect_legacy(request: Any):
            suffix = f"?{request.query_string}" if request.query_string else ""
            raise core.web.HTTPFound(location=f"{LEGACY_PREFIX}/{suffix}")

        async def serve_asset(request: Any):
            tail = str(request.match_info.get("tail") or "").lstrip("/")
            if not tail or tail.endswith("/"):
                tail = f"{tail}index.html"

            root = TARGET_DIR.resolve()
            path = (TARGET_DIR / tail).resolve()
            if path != root and root not in path.parents:
                raise core.web.HTTPNotFound(text="Недопустимый путь.")
            if not path.is_file():
                raise core.web.HTTPNotFound(text=f"Файл Godot-теста не найден: {tail}")

            cache_control = (
                "no-store, no-cache, must-revalidate, max-age=0"
                if path.suffix.casefold() in {".html", ".js"}
                else "public, max-age=3600"
            )
            return core.web.FileResponse(
                path,
                headers={
                    "Content-Type": _content_type(path),
                    "Cache-Control": cache_control,
                    "X-Content-Type-Options": "nosniff",
                    "X-Godot-Rooftop-Test": "170",
                },
            )

        def runner_with_godot_test_routes(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            routes = (
                ("GET", PRIMARY_PREFIX, redirect_primary),
                ("GET", f"{PRIMARY_PREFIX}/{{tail:.*}}", serve_asset),
                ("GET", LEGACY_PREFIX, redirect_legacy),
                ("GET", f"{LEGACY_PREFIX}/{{tail:.*}}", serve_asset),
            )
            for method, route, handler in routes:
                if (method, route) not in keys:
                    app.router.add_get(route, handler)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_godot_test_routes
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_godot_test_routes
    LOGGER.info("Explicit Godot test routes installed: %s and %s", PRIMARY_PREFIX, LEGACY_PREFIX)
