from __future__ import annotations

from typing import Any

import talent_system as talents
import talent_ux


STYLE = r"""
<style id="talent-recommendations-v68-style">
/* Следующий рекомендуемый узел больше не двигается: только спокойно светится. */
.nodewrap.v67-next .node,
.nodewrap.recommended .node{
  animation:none!important;
  transform:none!important;
  filter:none!important;
  border-color:#65ffb2!important;
  box-shadow:
    0 0 0 4px #65ffb229,
    0 0 22px #65ffb273,
    0 0 48px #65ffb245,
    inset 0 0 18px #65ffb21f!important;
}
.nodewrap.v67-next:after,
.nodewrap.recommended:after{animation:none!important}
.v68-clear-build{
  width:100%;min-height:39px;margin:0 0 10px;padding:8px 11px;
  border:1px solid #ff8d9f42;border-radius:13px;
  background:linear-gradient(135deg,#4c1c2b,#24101d);
  color:#ffb7c2;font-size:9px;font-weight:950;letter-spacing:.35px;
}
.v68-clear-build:active{transform:scale(.98)}
.v68-free-note{
  display:flex;align-items:center;gap:8px;margin:0 0 10px;padding:9px 10px;
  border:1px solid #ffffff10;border-radius:13px;background:#ffffff07;
  color:#aaa0b4;font-size:9px;line-height:1.35;
}
.v68-free-note span{font-size:18px}
.v68-clear-route{
  flex:0 0 auto;min-height:31px;margin-left:6px;padding:5px 8px;
  border:1px solid #ff8d9f42;border-radius:10px;background:#401724d9;
  color:#ffb2bf;font-size:7px;font-weight:950;white-space:nowrap;
}
.v68-clear-route:active{transform:scale(.96)}
body.v68-free-mode .nodewrap.recommended .node,
body.v68-free-mode .nodewrap.v67-next .node,
body.v68-free-mode .nodewrap.v67-path .node,
body.v68-free-mode .nodewrap.v67-done .node{
  animation:none!important;box-shadow:0 15px 32px #0008!important;
}
@media(max-width:390px){.v68-clear-route{padding:4px 6px;font-size:6.5px}}
</style>
"""


SCRIPT = r"""
<script id="talent-recommendations-v68-script">
(()=>{
const wait=setInterval(()=>{
 if(typeof state!=='undefined'&&state?.points){clearInterval(wait);bootV68()}
},120);
let queued=false;
function activeKey(){return localStorage.getItem('talentRecommendedBuild')||''}
function bootV68(){
 document.addEventListener('click',event=>{
  const clear=event.target.closest?.('[data-v68-clear-build]');
  if(clear){event.preventDefault();event.stopPropagation();clearBuildV68()}
 },true);
 new MutationObserver(scheduleV68).observe(document.body,{childList:true,subtree:true});
 setInterval(scheduleV68,500);
 scheduleV68();
}
function scheduleV68(){
 if(queued)return;queued=true;
 requestAnimationFrame(()=>{queued=false;applyV68()});
}
function clearBuildV68(){
 localStorage.removeItem('talentRecommendedBuild');
 document.body.classList.add('v68-free-mode');
 clearMarksV68();
 patchCardsV68();
 patchRouteButtonV68();
 try{toastShow('Сборка убрана. Включён свободный режим.')}catch(_){ }
 try{tg?.HapticFeedback?.notificationOccurred?.('success')}catch(_){ }
}
function clearMarksV68(){
 document.querySelectorAll('.nodewrap').forEach(node=>{
  node.classList.remove('recommended','v67-path','v67-done','v67-next','v67-conflict');
 });
 document.querySelectorAll('.v67-route-chip').forEach(node=>node.remove());
}
function patchCardsV68(){
 const body=document.getElementById('v66Body');
 if(!body)return;
 const buttons=[...body.querySelectorAll('[data-build]')];
 if(!buttons.length)return;
 let clear=body.querySelector('[data-v68-clear-build]');
 const key=activeKey();
 if(key){
  if(!clear){
   clear=document.createElement('button');
   clear.type='button';
   clear.className='v68-clear-build';
   clear.dataset.v68ClearBuild='1';
   clear.textContent='✕ УБРАТЬ СБОРКУ · СВОБОДНЫЙ РЕЖИМ';
   const note=body.querySelector('.v66-note');
   note?.insertAdjacentElement('afterend',clear);
  }
 }else{
  clear?.remove();
  body.querySelectorAll('.v66-card.active').forEach(card=>card.classList.remove('active'));
  buttons.forEach(button=>{
   if(button.textContent!=='ВЫБРАТЬ И ПОКАЗАТЬ')button.textContent='ВЫБРАТЬ И ПОКАЗАТЬ';
  });
  if(!body.querySelector('.v68-free-note')){
   const note=document.createElement('div');
   note.className='v68-free-note';
   note.innerHTML='<span>👐</span><div><b>Свободный режим</b><br>Древо ничего не рекомендует — выбирай таланты самостоятельно.</div>';
   body.querySelector('.v66-note')?.insertAdjacentElement('afterend',note);
  }
 }
 if(key)body.querySelector('.v68-free-note')?.remove();
}
function patchRouteButtonV68(){
 const branchBox=document.querySelector('.branch');
 if(!branchBox)return;
 let button=document.getElementById('v68ClearRoute');
 const key=activeKey();
 if(key){
  document.body.classList.remove('v68-free-mode');
  if(!button){
   button=document.createElement('button');
   button.id='v68ClearRoute';button.type='button';
   button.className='v68-clear-route';button.dataset.v68ClearBuild='1';
   button.textContent='✕ УБРАТЬ СБОРКУ';
   branchBox.appendChild(button);
  }
 }else{
  document.body.classList.add('v68-free-mode');
  button?.remove();
  clearMarksV68();
 }
}
function applyV68(){
 patchCardsV68();
 patchRouteButtonV68();
 if(!activeKey())clearMarksV68();
}
})();
</script>
"""


def install_talent_recommendations_v68(core: Any) -> None:
    if getattr(talents, "_talent_recommendations_v68_installed", False):
        return
    talents._talent_recommendations_v68_installed = True
    talent_ux.STYLE += STYLE
    talent_ux.SCRIPT += SCRIPT
