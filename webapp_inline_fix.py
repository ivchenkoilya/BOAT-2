from __future__ import annotations

import logging
import re
from typing import Any


LOGGER = logging.getLogger(__name__)


def install_inline_webapp_fix(core: Any) -> None:
    """Встраивает актуальный боевой интерфейс прямо в HTML Mini App.

    Каждый JS-файл помещается в отдельный script-блок. Ошибка в новом слое
    больше не может остановить магазин, инвентарь и карточки героев целиком.
    """
    if getattr(core, "_inline_webapp_fix_v65_installed", False):
        return

    core._inline_webapp_fix_v65_installed = True
    original_index = core.webapp_index
    index_path = core.WEBAPP_DIR / "index.html"
    css_paths = [
        core.WEBAPP_DIR / "fixed-combat-v18.css",
        core.WEBAPP_DIR / "raid-ux-v19.css",
        core.WEBAPP_DIR / "raid-pages-v20.css",
        core.WEBAPP_DIR / "action-card-ego-v21.css",
        core.WEBAPP_DIR / "action-card-defense-v21.css",
        core.WEBAPP_DIR / "action-card-heal-v21.css",
        core.WEBAPP_DIR / "action-cards-layout-v21.css",
        core.WEBAPP_DIR / "raid-hotfix-v22.css",
        core.WEBAPP_DIR / "raid-hotfix-v23.css",
        core.WEBAPP_DIR / "raid-stability-v24.css",
        core.WEBAPP_DIR / "raid-final-v25.css",
        core.WEBAPP_DIR / "raid-victory-v59.css",
        core.WEBAPP_DIR / "raid-v61.css",
        core.WEBAPP_DIR / "raid-v65-balance-layout.css",
        core.WEBAPP_DIR / "hero-skins-sync-v100.css",
        core.WEBAPP_DIR / "action-card-defense-cutout-v102.css",
        core.WEBAPP_DIR / "hero-loadouts-v103.css",
        core.WEBAPP_DIR / "hero-preview-v104.css",
        core.WEBAPP_DIR / "hero-content-v105.css",
    ]
    js_paths = [
        core.WEBAPP_DIR / "fixed-combat-v18.js",
        core.WEBAPP_DIR / "raid-ux-v19.js",
        core.WEBAPP_DIR / "raid-pages-v20.js",
        core.WEBAPP_DIR / "raid-hotfix-v23.js",
        core.WEBAPP_DIR / "raid-stability-v24.js",
        core.WEBAPP_DIR / "raid-final-v25.js",
        core.WEBAPP_DIR / "raid-victory-v59.js",
        core.WEBAPP_DIR / "raid-v61.js",
        core.WEBAPP_DIR / "raid-v64-direct-tree.js",
        core.WEBAPP_DIR / "raid-v65-balance-layout.js",
        core.WEBAPP_DIR / "hero-skins-sync-v100.js",
        core.WEBAPP_DIR / "hero-loadouts-v103.js",
        core.WEBAPP_DIR / "hero-preview-v104.js",
        core.WEBAPP_DIR / "hero-content-v105.js",
    ]

    async def webapp_index_with_inline_combat(request: Any):
        try:
            page = index_path.read_text(encoding="utf-8")
            css = "\n\n".join(path.read_text(encoding="utf-8") for path in css_paths)

            page = re.sub(
                r"\s*<link[^>]+(?:fixed-combat-v18|raid-ux-v19|raid-pages-v20|action-card-ego-v21|action-card-defense-v21|action-card-heal-v21|action-cards-layout-v21|raid-hotfix-v22|raid-hotfix-v23|raid-stability-v24|raid-final-v25|raid-victory-v59|raid-v60|raid-v60-stability|raid-v61|raid-v65-balance-layout|hero-skins-sync-v100|action-card-defense-cutout-v102|hero-loadouts-v103|hero-preview-v104|hero-content-v105)\.css[^>]*>",
                "",
                page,
                flags=re.IGNORECASE,
            )
            page = re.sub(
                r"\s*<script[^>]+(?:fixed-combat-v18|raid-ux-v19|raid-pages-v20|raid-hotfix-v23|raid-stability-v24|raid-final-v25|raid-victory-v59|raid-v60|raid-v60-stability|raid-v61|raid-v64-direct-tree|raid-v65-balance-layout|hero-skins-sync-v100|hero-loadouts-v103|hero-preview-v104|hero-content-v105)\.js[^>]*></script>",
                "",
                page,
                flags=re.IGNORECASE,
            )

            prelude = """
<script id="raid-ui-v65-prelude">
(function(){
  var nativeSetInterval=window.setInterval.bind(window);
  window.setInterval=function(callback,delay){
    var args=Array.prototype.slice.call(arguments,2);
    var safeDelay=Number(delay)===200?1000:delay;
    return nativeSetInterval.apply(window,[callback,safeDelay].concat(args));
  };
})();
</script>
"""
            inline_style = (
                "\n<style id=\"raid-ui-v105-inline\">\n"
                + css
                + "\n</style>\n"
            )
            script_blocks = []
            for index, path in enumerate(js_paths, start=1):
                source = path.read_text(encoding="utf-8")
                safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", path.stem)
                script_blocks.append(
                    f'\n<script id="raid-ui-v105-{index}-{safe_name}">\n{source}\n</script>\n'
                )
            inline_scripts = "".join(script_blocks)

            page = page.replace("</head>", prelude + inline_style + "</head>", 1)
            page = page.replace("</body>", inline_scripts + "</body>", 1)

            return core.web.Response(
                text=page,
                content_type="text/html",
                charset="utf-8",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Mini-App-UI": "raid-ui-v105-isolated",
                },
            )
        except Exception:
            LOGGER.exception("Не удалось встроить актуальный боевой интерфейс")
            return await original_index(request)

    core.webapp_index = webapp_index_with_inline_combat
