from __future__ import annotations

from typing import Any

import talent_ux

RULES_SCRIPT = r"""
<script id="talent-rules-v2">
(()=>{
 let tries=0;
 const timer=setInterval(()=>{
  tries++;
  const earn=document.querySelector('.earn');
  if(earn){
   earn.innerHTML='<b>Как получить очки таланта</b>Ты получаешь 5 стартовых очков и ещё по одному за каждые 300 очков влияния, максимум 45. Уже открытые очки не отнимаются при потере влияния.';
   clearInterval(timer);
  }else if(tries>80){clearInterval(timer)}
 },100);
})();
</script>
"""


def install_talent_rules(core: Any) -> None:
    if getattr(core, "_talent_rules_v2_installed", False):
        return
    core._talent_rules_v2_installed = True
    talent_ux.SCRIPT += RULES_SCRIPT
