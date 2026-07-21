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
    if getattr(core, "_inline_webapp_fix_v149_installed", False):
        return

    core._inline_webapp_fix_v149_installed = True
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
        core.WEBAPP_DIR / "boss-combat-v149.css",
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
        core.WEBAPP_DIR / "boss-combat-v149.js",
    ]

    async def webapp_index_with_inline_combat(request: Any):
        try:
            page = index_path.read_text(encoding="utf-8")
            css = "\n\n".join(path.read_text(encoding="utf-8") for path in css_paths)

            page = re.sub(
                r"\s*<link[^>]+(?:fixed-combat-v18|raid-ux-v19|raid-pages-v20|action-card-ego-v21|action-card-defense-v21|action-card-heal-v21|action-cards-layout-v21|raid-hotfix-v22|raid-hotfix-v23|raid-stability-v24|raid-final-v25|raid-victory-v59|raid-v60|raid-v60-stability|raid-v61|raid-v65-balance-layout|hero-skins-sync-v100|action-card-defense-cutout-v102|hero-loadouts-v103|hero-preview-v104|hero-content-v105|boss-combat-v149)\.css[^>]*>",
                "",
                page,
                flags=re.IGNORECASE,
            )
            page = re.sub(
                r"\s*<script[^>]+(?:fixed-combat-v18|raid-ux-v19|raid-pages-v20|raid-hotfix-v23|raid-stability-v24|raid-final-v25|raid-victory-v59|raid-v60|raid-v60-stability|raid-v61|raid-v64-direct-tree|raid-v65-balance-layout|hero-skins-sync-v100|hero-loadouts-v103|hero-preview-v104|hero-content-v105|boss-combat-v149)\.js[^>]*></script>",
                "",
                page,
                flags=re.IGNORECASE,
            )

            prelude = """
<script id="raid-ui-v149-prelude">
(function(){
  var nativeSetInterval=window.setInterval.bind(window);
  window.setInterval=function(callback,delay){
    var args=Array.prototype.slice.call(arguments,2);
    var safeDelay=Number(delay)===200?1000:delay;
    return nativeSetInterval.apply(window,[callback,safeDelay].concat(args));
  };

  function initialBossId(){
    try{
      var tg=window.Telegram&&window.Telegram.WebApp;
      var params=new URLSearchParams(location.search);
      return String(
        (tg&&tg.initDataUnsafe&&tg.initDataUnsafe.start_param)||
        params.get('boss')||
        params.get('tgWebAppStartParam')||
        sessionStorage.getItem('raid:last-boss-id')||
        ''
      ).trim();
    }catch(_error){return '';}
  }

  function publishRaidState(data){
    if(!data||!data.ok)return;
    var battle=data.battle||{};
    var id=String(battle.boss_id||data.boss_id||window.__raidBossId||'').trim();
    if(id){
      window.__raidBossId=id;
      try{sessionStorage.setItem('raid:last-boss-id',id);}catch(_error){}
    }
    if(Array.isArray(data.fighters))window.__raidBossState=data;
    try{window.dispatchEvent(new CustomEvent('raid-state-updated',{detail:data}));}catch(_error){}
  }

  window.__raidBossId=window.__raidBossId||initialBossId();
  window.__publishRaidState=publishRaidState;

  var nativeFetch=window.fetch.bind(window);
  window.fetch=async function(){
    var args=Array.prototype.slice.call(arguments);
    var response=await nativeFetch.apply(window,args);
    var input=args[0];
    var url=typeof input==='string'?input:String(input&&input.url||'');
    if(url.indexOf('/boss-app/api/boss/')!==-1){
      response.clone().json().then(publishRaidState).catch(function(){});
    }
    return response;
  };
})();
</script>
"""
            inline_style = (
                "\n<style id=\"raid-ui-v149-inline\">\n"
                + css
                + "\n</style>\n"
            )
            script_blocks = []
            for index, path in enumerate(js_paths, start=1):
                source = path.read_text(encoding="utf-8")
                safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", path.stem)
                script_blocks.append(
                    f'\n<script id="raid-ui-v149-{index}-{safe_name}">\n{source}\n</script>\n'
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
                    "X-Mini-App-UI": "raid-ui-v149-boss-combat",
                },
            )
        except Exception:
            LOGGER.exception("Не удалось встроить актуальный боевой интерфейс")
            return await original_index(request)

    core.webapp_index = webapp_index_with_inline_combat
