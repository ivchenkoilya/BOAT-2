(()=>{
  "use strict";
  const $=id=>document.getElementById(id),stage=$("stage"),loot=$("loot"),crack=$("crackOverlay");
  if(loot&&!loot.querySelector(".bagWeight")){const b=document.createElement("small");b.className="bagWeight";b.textContent="МЕШОК ЛЁГКИЙ";loot.appendChild(b);const sync=()=>{const n=parseInt(loot.querySelector("b")?.textContent||loot.textContent)||0;b.textContent=n>=650?"МЕШОК ПЕРЕГРУЖЕН":n>=320?"МЕШОК ТЯЖЁЛЫЙ":"МЕШОК ЛЁГКИЙ";b.classList.toggle("heavy",n>=320&&n<650);b.classList.toggle("overloaded",n>=650)};sync();new MutationObserver(sync).observe(loot,{childList:true,subtree:true,characterData:true});}
  const badge=document.createElement("div");badge.className="escapeBadge hidden";badge.textContent="🚨 ПОБЕГ — КАМЕРЫ УСИЛЕНЫ";stage?.appendChild(badge);
  const watchEscape=()=>badge.classList.toggle("hidden",!stage?.classList.contains("escape-mode"));if(stage)new MutationObserver(watchEscape).observe(stage,{attributes:true,attributeFilter:["class"]});watchEscape();
  if(crack)new MutationObserver(()=>{if(crack.classList.contains("hidden"))return;requestAnimationFrame(()=>{const game=$("crackGame");if(game?.querySelector(".v88Circuit"))$("crackType").textContent="ЭЛЕКТРОННЫЙ СЕЙФ";});}).observe(crack,{attributes:true,attributeFilter:["class"]});
})();
