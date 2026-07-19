(()=>{
  "use strict";
  const interact=document.getElementById("interact");
  const smoke=document.getElementById("smoke");
  if(!interact||!smoke)return;

  const compactAction=()=>{
    const text=(interact.textContent||"").trim();
    let next=text;
    if(/ПОДОЙДИ К СЕЙФУ|ИЩИ ЦЕЛЬ/i.test(text)) next="🔎 ИЩИ ЦЕЛЬ";
    else if(/ВСКРЫТЬ.*ХРАНИЛИЩ/i.test(text)) next="🏛 ХРАНИЛИЩЕ";
    else if(/ЭЛИТН/i.test(text)&&/СЕЙФ|ВЗЛОМ/i.test(text)) next="💎 ЭЛИТНЫЙ СЕЙФ";
    else if(/ВСКРЫТЬ.*СЕЙФ|ВЗЛОМАТЬ.*СЕЙФ/i.test(text)) next="🔓 ВСКРЫТЬ";
    else if(/ПОКИНУТЬ|УЙТИ/i.test(text)) next="🚪 ВЫЙТИ";
    if(next!==text) interact.textContent=next;
  };

  const compactSmoke=()=>{
    if((smoke.textContent||"").trim()!=="🌫 ДЫМ") smoke.textContent="🌫 ДЫМ";
  };

  compactAction();
  compactSmoke();
  new MutationObserver(compactAction).observe(interact,{childList:true,subtree:true,characterData:true});
  new MutationObserver(compactSmoke).observe(smoke,{childList:true,subtree:true,characterData:true});
})();
