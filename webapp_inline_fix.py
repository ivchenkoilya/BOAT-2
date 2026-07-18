from __future__ import annotations

import logging
import re
from typing import Any


LOGGER = logging.getLogger(__name__)


def install_inline_webapp_fix(core: Any) -> None:
    """Встраивает новый боевой интерфейс в index.html при каждом запросе.

    Старый сервер Mini App разрешает отдельными маршрутами только style.css и
    app.js. Поэтому новые fixed-combat-v18.css/js возвращали 404. Встраивание
    делает обновление независимым от этого старого ограничения маршрутов.
    """
    if getattr(core, "_inline_webapp_fix_v18_installed", False):
        return

    core._inline_webapp_fix_v18_installed = True
    original_index = core.webapp_index
    css_path = core.WEBAPP_DIR / "fixed-combat-v18.css"
    js_path = core.WEBAPP_DIR / "fixed-combat-v18.js"
    index_path = core.WEBAPP_DIR / "index.html"

    async def webapp_index_with_inline_combat(request: Any):
        try:
            page = index_path.read_text(encoding="utf-8")
            css = css_path.read_text(encoding="utf-8")
            script = js_path.read_text(encoding="utf-8")

            # Убираем ссылки на файлы, которые старый роутер не умеет отдавать.
            page = re.sub(
                r"\s*<link[^>]+fixed-combat-v18\.css[^>]*>",
                "",
                page,
                flags=re.IGNORECASE,
            )
            page = re.sub(
                r"\s*<script[^>]+fixed-combat-v18\.js[^>]*></script>",
                "",
                page,
                flags=re.IGNORECASE,
            )

            inline_style = (
                "\n<style id=\"fixed-combat-v18-inline\">\n"
                + css
                + "\n</style>\n"
            )
            inline_script = (
                "\n<script id=\"fixed-combat-v18-inline-script\">\n"
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
                    "X-Mini-App-UI": "fixed-combat-v18-inline",
                },
            )
        except Exception:
            LOGGER.exception("Не удалось встроить фиксированный боевой интерфейс")
            return await original_index(request)

    core.webapp_index = webapp_index_with_inline_combat
