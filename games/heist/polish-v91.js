(()=>{
  "use strict";
  const $=id=>document.getElementById(id);
  const overlay=$("crackOverlay"),stats=document.querySelector(".crackStats"),reward=$("reward"),loot=$("loot"),crackGame=$("crackGame");

  const ensureStatValues=()=>{
    if(!stats)return;
    const cards=[...stats.children];
    cards.forEach((card,index)=>{
      const label=card.querySelector(":scope > span");
      const bar=card.querySelector(".statbar > i");
      if(!label||!bar)return;
      let value=label.querySelector(".v91StatValue");
      if(!value){
        if(index===2&&$("noiseValue")){value=$("noiseValue");value.classList.add("v91StatValue");}
        else{value=document.createElement("b");value.className="v91StatValue";label.appendChild(value);}
      }
      const width=parseFloat(bar.style.width||getComputedStyle(bar).width)||0;
      const parentWidth=bar.parentElement?.getBoundingClientRect().width||100;
      const percent=bar.style.width.includes("%")?parseFloat(bar.style.width):width/Math.max(1,parentWidth)*100;
      const text=Math.round(Math.max(0,Math.min(100,percent)))+"%";
      if(value.textContent!==text)value.textContent=text;
      card.classList.toggle("danger",index===2&&percent>=65);
    });
  };

  let statTimer=0;
  const syncOverlay=()=>{
    const active=overlay&&!overlay.classList.contains("hidden");
    document.body.classList.toggle("v91-cracking",Boolean(active));
    clearInterval(statTimer);
    if(active){ensureStatValues();statTimer=setInterval(ensureStatValues,120);}
  };
  if(overlay)new MutationObserver(syncOverlay).observe(overlay,{attributes:true,attributeFilter:["class"]});
  if(stats)new MutationObserver(ensureStatValues).observe(stats,{childList:true,subtree:true});
  syncOverlay();

  if(crackGame){
    const relayTimingState=()=>{
      const shell=crackGame.querySelector(".v91PinGame");
      if(!shell)return;
      shell.classList.toggle("v91-hit",crackGame.classList.contains("v91-hit"));
      shell.classList.toggle("v91-miss",crackGame.classList.contains("v91-miss"));
    };
    new MutationObserver(relayTimingState).observe(crackGame,{attributes:true,attributeFilter:["class"],childList:true});
  }

  if(loot){
    let previous=loot.querySelector("b")?.textContent||loot.textContent;
    new MutationObserver(()=>{
      const next=loot.querySelector("b")?.textContent||loot.textContent;
      if(next===previous)return;previous=next;loot.classList.remove("v91-pop");void loot.offsetWidth;loot.classList.add("v91-pop");setTimeout(()=>loot.classList.remove("v91-pop"),480);
    }).observe(loot,{childList:true,subtree:true,characterData:true});
  }

  const prettifyReward=()=>{
    if(!reward||reward.querySelector(".rewardLine")||reward.querySelector(".error"))return;
    const values=[...reward.querySelectorAll("b")].map(node=>String(node.textContent||"").replace(/[^0-9-]/g,""));
    if(values.length<5)return;
    const message=reward.querySelector("small")?.textContent||"Вся сохранённая добыча добавлена в баланс.";
    reward.innerHTML=`
      <div class="rewardLine"><span>💰 Сохранённая добыча</span><b>+${values[0]||0}</b></div>
      <div class="rewardLine"><span>🏦 Начислено за забег</span><b>+${values[1]||0}</b></div>
      <div class="rewardLine"><span>🌳 Бонус древа</span><b>+${values[2]||0}</b></div>
      <div class="rewardLine total"><span>🏆 Получено влияния</span><b>+${values[3]||0}</b></div>
      <div class="rewardLine"><span>👑 Новый баланс</span><b>${values[4]||0}</b></div>
      <div class="rewardMessage">${message}</div>`;
  };
  if(reward)new MutationObserver(()=>requestAnimationFrame(prettifyReward)).observe(reward,{childList:true,subtree:true});
})();
