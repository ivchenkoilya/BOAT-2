(()=>{
  "use strict";
  const $=id=>document.getElementById(id),stage=$("stage"),action=$("interact"),loot=$("loot"),alarmText=$("alarmText"),alarmCard=document.querySelector(".alarmCard");
  const classify=()=>{if(!action)return;const t=(action.textContent||"").toUpperCase();action.classList.toggle("v87-elite",t.includes("ЭЛИТ"));action.classList.toggle("v87-vault",t.includes("ХРАНИЛИЩ"));action.classList.toggle("v87-exit",t.includes("ВЫЙТИ")||t.includes("УЙТИ"));};
  classify();if(action)new MutationObserver(classify).observe(action,{childList:true,subtree:true,characterData:true});
  if(loot){let old=Number(loot.textContent)||0;new MutationObserver(()=>{const next=Number(loot.textContent)||0;if(next>old){loot.classList.remove("v87-pop");void loot.offsetWidth;loot.classList.add("v87-pop");setTimeout(()=>loot.classList.remove("v87-pop"),450)}old=next}).observe(loot,{childList:true,subtree:true,characterData:true});}
  if(alarmText){let old=0;new MutationObserver(()=>{const v=parseInt(alarmText.textContent)||0;stage?.classList.toggle("v87-threat",v>=25);stage?.classList.toggle("v87-critical",v>=75);if(v>old+1&&alarmCard){alarmCard.classList.remove("v87-pulse");void alarmCard.offsetWidth;alarmCard.classList.add("v87-pulse");setTimeout(()=>alarmCard.classList.remove("v87-pulse"),380)}old=v}).observe(alarmText,{childList:true,subtree:true,characterData:true});}
})();
