from __future__ import annotations

from typing import Any

import government_institutions_v128 as institutions
import government_reform_v129 as reform


VERSION = "Reality 129 · Интерфейс реформы власти"


def install_government_reform_assets_v129(core: Any) -> None:
    if getattr(core, "_government_reform_assets_v129_installed", False):
        return
    core._government_reform_assets_v129_installed = True

    @core.web.middleware
    async def combined_government_script(request: Any, handler: Any):
        if request.method.upper() == "GET" and str(request.path or "") == "/government-v127/powers-v128.js":
            if not institutions.ASSET_JS.is_file() or not reform.ASSET_JS.is_file():
                return core.web.Response(
                    text="console.error('Reality 129 assets missing');",
                    content_type="application/javascript",
                    charset="utf-8",
                    status=500,
                )
            source = (
                institutions.ASSET_JS.read_text(encoding="utf-8")
                + "\n\n/* Reality 129 */\n"
                + reform.ASSET_JS.read_text(encoding="utf-8")
            )
            return core.web.Response(
                text=source,
                content_type="application/javascript",
                charset="utf-8",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Government-Reform": "129",
                },
            )
        return await handler(request)

    previous_application = core.web.Application

    def application_with_combined_assets(*args: Any, **kwargs: Any):
        middlewares = list(kwargs.pop("middlewares", []) or [])
        kwargs["middlewares"] = [combined_government_script, *middlewares]
        return previous_application(*args, **kwargs)

    core.web.Application = application_with_combined_assets
