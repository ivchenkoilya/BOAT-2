from __future__ import annotations

from pathlib import Path
from typing import Any

import talent_improvements_v66 as improvements
import talent_system as talents
import talent_ux


FINISH_STYLE = r"""
<style id="talent-v66-finish-style">
.v66-title-chip{display:inline-flex;align-items:center;gap:4px;max-width:150px;margin-top:4px;padding:3px 7px;border:1px solid #ffd36d45;border-radius:99px;background:#ffd36d0d;color:#ffe29a;font-size:7px;font-weight:950;letter-spacing:.35px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
body[data-talent-cosmetic="damage"] .points{box-shadow:0 0 28px #ff526c45}
body[data-talent-cosmetic="influence"] .points{box-shadow:0 0 28px #ffd36d45}
body[data-talent-cosmetic="defense"] .points{box-shadow:0 0 28px #63dfff45}
body[data-talent-cosmetic="rewards"] .points{box-shadow:0 0 28px #d46cff45}
</style>
"""


FINISH_SCRIPT = r"""
<script id="talent-v66-finish-script">
(()=>{
const wait=setInterval(()=>{if(typeof state!=='undefined'&&state?.points){clearInterval(wait);bootFinish()}},120);
let lastSignature='';
function bootFinish(){applyFinish();setInterval(applyFinish,500)}
function applyFinish(){
 const unlocked=(state.cosmetics||[]).filter(x=>x.unlocked).sort((a,b)=>Number(b.unlocked_at||0)-Number(a.unlocked_at||0));
 const latest=unlocked[0];
 const signature=JSON.stringify({build:state.builds?.reset_mode,cosmetic:latest?.branch,points:state.points?.available});
 if(signature===lastSignature)return;lastSignature=signature;
 const brand=document.querySelector('.brand');
 let chip=document.getElementById('v66TitleChip');
 if(latest){
  if(!chip){chip=document.createElement('div');chip.id='v66TitleChip';chip.className='v66-title-chip';brand?.appendChild(chip)}
  chip.textContent=`${latest.emoji||'🏆'} ${latest.title||'Герой'}`;
  document.body.dataset.talentCosmetic=latest.branch||'';
 }else{chip?.remove();delete document.body.dataset.talentCosmetic}
 const overlay=document.querySelector('.master-overlay.show');
 const title=overlay?.querySelector('#masterTitle')?.textContent||'';
 if(title.includes('Билды')){
  const note=overlay.querySelector('.master-note');
  if(note){
   const resetNote=state.builds?.reset_note||'Первый сброс бесплатный. Затем каждую неделю доступен ещё один бесплатный сброс.';
   note.textContent=`Сохрани до трёх вариантов прокачки. ${resetNote} Между переключениями билдов действует часовой откат.`
  }
 }
}
})();
</script>
"""


async def _cosmetic_branches(db: Any, chat_id: int, user_id: int) -> set[str]:
    conn = talents._conn(db)
    cursor = await conn.execute(
        "SELECT branch FROM talent_cosmetics_v66 WHERE chat_id=? AND user_id=?",
        (chat_id, user_id),
    )
    return {str(row["branch"]) for row in await cursor.fetchall()}


def install_talent_v66_finish(core: Any) -> None:
    if getattr(talents, "_talent_v66_finish_installed", False):
        return
    talents._talent_v66_finish_installed = True

    original_upgrade = talents.upgrade_skill

    async def upgrade_skill(
        db: Any,
        chat_id: int,
        user_id: int,
        skill_id: str,
    ) -> dict[str, Any]:
        before = await _cosmetic_branches(db, chat_id, user_id)
        result = await original_upgrade(db, chat_id, user_id, skill_id)
        after = await _cosmetic_branches(db, chat_id, user_id)
        newly_unlocked = sorted(after - before)
        if newly_unlocked:
            result["new_cosmetics"] = [
                {"branch": branch, **improvements.COSMETICS[branch]}
                for branch in newly_unlocked
                if branch in improvements.COSMETICS
            ]
        return result

    talents.upgrade_skill = upgrade_skill

    talent_ux.STYLE += FINISH_STYLE
    talent_ux.SCRIPT += FINISH_SCRIPT

    original_file_response = core.web.FileResponse

    def file_response(path: Any, *args: Any, **kwargs: Any):
        response = original_file_response(path, *args, **kwargs)
        file_path = Path(path)
        if file_path.name == "index.html" and file_path.parent.name == "talent_app":
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, max-age=0"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            response.headers["X-Talent-UI"] = "reality-66"
        return response

    core.web.FileResponse = file_response
