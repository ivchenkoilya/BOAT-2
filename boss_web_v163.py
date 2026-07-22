from __future__ import annotations

import logging
from typing import Any


LOGGER = logging.getLogger(__name__)
SCRIPT_MARKER = "boss-rules-v163"


def install_boss_web_v163(core: Any) -> None:
    """Подключает финальный UI-слой к уже собранной странице рейда."""
    if getattr(core, "_boss_web_v163_installed", False):
        return
    core._boss_web_v163_installed = True

    original_index = core.webapp_index
    script_path = core.WEBAPP_DIR / "boss-rules-v163.js"

    async def webapp_index_v163(request: Any):
        response = await original_index(request)
        try:
            page = response.text
            if SCRIPT_MARKER in page:
                return response
            source = script_path.read_text(encoding="utf-8")
            page = page.replace(
                "</body>",
                f'\n<script id="{SCRIPT_MARKER}">\n{source}\n</script>\n</body>',
                1,
            )
            headers = {
                key: value
                for key, value in response.headers.items()
                if key.lower() not in {"content-length", "content-type"}
            }
            headers["X-Boss-Rules"] = "reality-163"
            return core.web.Response(
                text=page,
                status=response.status,
                content_type="text/html",
                charset="utf-8",
                headers=headers,
            )
        except Exception:
            LOGGER.exception("Не удалось подключить UI правил босса Reality 163")
            return response

    core.webapp_index = webapp_index_v163
