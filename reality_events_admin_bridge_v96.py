from __future__ import annotations

from pathlib import Path
from typing import Any

from aiohttp import web


BASE_DIR = Path(__file__).resolve().parent
ADMIN_HTML = BASE_DIR / "adminapp_v76" / "index.html"
REWARD_EDITOR = BASE_DIR / "adminapp_v96" / "reward-editor.js"
VERSION = "Reality 96 · События реальности"


def install_reality_events_admin_bridge_v96(core: Any) -> None:
    if getattr(core, "_reality_events_admin_bridge_v96_installed", False):
        return
    core._reality_events_admin_bridge_v96_installed = True

    @web.middleware
    async def admin_html_bridge(request: web.Request, handler: Any) -> web.StreamResponse:
        if request.method == "GET" and request.path == "/admin-v96/reward-editor.js":
            return web.FileResponse(
                REWARD_EDITOR,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "X-Admin-Center": VERSION,
                },
            )
        if request.method == "GET" and request.path in {"/admin-v76", "/admin-v76/"}:
            source = ADMIN_HTML.read_text(encoding="utf-8")
            source = source.replace("<title>Админ-центр Reality 89</title>", "<title>Админ-центр Reality 96</title>")
            source = source.replace(
                '<strong id="versionText">Reality 89</strong>',
                '<strong id="versionText">Reality 96</strong>',
            )
            source = source.replace(
                '<div class="loading" id="loading"><div class="spinner"></div><b>Загрузка Reality 89</b><span>Синхронизируем участников, игры и древо</span></div>',
                '<div class="loading" id="loading"><div class="spinner"></div><b>Загрузка Reality 96</b><span>Синхронизируем игроков, игры, древо и событие дня</span></div>',
            )
            source = source.replace(
                '<script src="/admin-v89/admin-v89.js?v=89"></script>\n  <script src="/admin-v76/admin.js?v=89"></script>',
                '<script src="/admin-v89/admin-v89.js?v=96"></script>\n'
                '  <script src="/admin-v95/night-hunter-admin.js?v=96"></script>\n'
                '  <script src="/admin-v96/events-admin.js?v=96"></script>\n'
                '  <script src="/admin-v96/reward-editor.js?v=96"></script>\n'
                '  <script src="/admin-v76/admin.js?v=96"></script>',
            )
            return web.Response(
                text=source,
                content_type="text/html",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Admin-Center": VERSION,
                },
            )
        return await handler(request)

    original_application = core.web.Application

    def application_with_admin_bridge(*args: Any, **kwargs: Any):
        middlewares = list(kwargs.pop("middlewares", []) or [])
        kwargs["middlewares"] = [admin_html_bridge, *middlewares]
        return original_application(*args, **kwargs)

    core.web.Application = application_with_admin_bridge
