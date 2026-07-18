from __future__ import annotations

import logging
import re
from typing import Any


LOGGER = logging.getLogger(__name__)


def install_inline_webapp_fix(core: Any) -> None:
    """Встраивает актуальный боевой интерфейс прямо в HTML Mini App.

    Старый сервер Mini App разрешает отдельными маршрутами только style.css и
    app.js. Поэтому дополнительные CSS/JS объединяются с HTML на сервере и не
    зависят от ограничений маршрутов или кэша Telegram WebView.
    """
    if getattr(core, "_inline_webapp_fix_v20_installed", False):
        return

    core._inline_webapp_fix_v20_installed = True
    original_index = core.webapp_index
    index_path = core.WEBAPP_DIR / "index.html"
    css_paths = [
        core.WEBAPP_DIR / "fixed-combat-v18.css",
        core.WEBAPP_DIR / "raid-ux-v19.css",
        core.WEBAPP_DIR / "raid-pages-v20.css",
    ]
    js_paths = [
        core.WEBAPP_DIR / "fixed-combat-v18.js",
        core.WEBAPP_DIR / "raid-ux-v19.js",
        core.WEBAPP_DIR / "raid-pages-v20.js",
    ]

    async def webapp_index_with_inline_combat(request: Any):
        try:
            page = index_path.read_text(encoding="utf-8")
            css = "\n\n".join(path.read_text(encoding="utf-8") for path in css_paths)
            script = "\n\n".join(path.read_text(encoding="utf-8") for path in js_paths)

            # Убираем ссылки на файлы, которые старый роутер не умеет отдавать.
            page = re.sub(
                r"\s*<link[^>]+(?:fixed-combat-v18|raid-ux-v19|raid-pages-v20)\.css[^>]*>",
                "",
                page,
                flags=re.IGNORECASE,
            )
            page = re.sub(
                r"\s*<script[^>]+(?:fixed-combat-v18|raid-ux-v19|raid-pages-v20)\.js[^>]*></script>",
                "",
                page,
                flags=re.IGNORECASE,
            )

            inline_style = (
                "\n<style id=\"raid-ui-v20-inline\">\n"
                + css
                + "\n</style>\n"
            )
            inline_script = (
                "\n<script id=\"raid-ui-v20-inline-script\">\n"
                + script
                + "\n</script>\n"
            )
            page = page.replace("</head>", inline_style + "</head>", 1)
            page = page.replace("</body>", inline_script + "</body>", 1)

            return core.web.Response(
                text=page,
                content_type="text/html",
                charset="utf-8",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Mini-App-UI": "raid-ui-v20-inline",
                },
            )
        except Exception:
            LOGGER.exception("Не удалось встроить актуальный боевой интерфейс")
            return await original_index(request)

    core.webapp_index = webapp_index_with_inline_combat
