(()=>{
  'use strict';

  const MAX_SHIELDS=3;
  let latest=window.__raidBossState||null;
  let receivedAt=performance.now();
  let patchQueued=false;

  function serverNow(){
    return Number(latest?.now||Date.now()/1000)+(performance.now()-receivedAt)/1000;
  }

  function secondsLabel(value){
    const seconds=Math.max(0,Math.ceil(Number(value)||0));
    return seconds<10?`0${seconds}`:String(seconds);
  }

  function setText(node,value){
    if(node&&node.textContent!==value)node.textContent=value;
  }

  function setData(node,key,value){
    if(node&&node.dataset[key]!==value)node.dataset[key]=value;
  }

  function acceptState(data){
    if(!data?.ok)return;
    latest=data;
    receivedAt=performance.now();
    const battle=data.battle;
    if(battle){
      battle.shield_hits=Math.max(0,Math.min(MAX_SHIELDS,Number(battle.shield_hits)||0));
      battle.shield_max=MAX_SHIELDS;
    }
    schedulePatch();
  }

  function patchShield(){
    const label=document.getElementById('shieldText');
    const battle=latest?.battle;
    if(!label||!battle)return;

    const shields=Math.max(0,Math.min(MAX_SHIELDS,Number(battle.shield_hits)||0));
    const readyAt=Number(battle.shield_refill_ready_at)||0;
    const left=shields<=0?Math.max(0,readyAt-serverNow()):0;
    let text='разбит · можно восстановить';

    if(shields>0)text=`${shields}/${MAX_SHIELDS} заряда`;
    else if(left>0)text=`новые щиты через 0:${secondsLabel(left)}`;

    setText(label,text);
  }

  function patchHeroPreview(){
    const overlay=document.getElementById('heroPreviewOverlay');
    if(!overlay)return;

    const heroId=Number(overlay.dataset.heroId)||0;
    const title=overlay.querySelector('.hero-preview-ability-title');
    const cooldown=title?.querySelector('em');
    if(heroId>=1&&heroId<=7)setText(cooldown,'5 минут');

    if(heroId!==7)return;
    setText(title?.querySelector('strong'),'Возвращение в сюжет');
    setData(overlay.querySelector('.hero-preview-section.ability'),'repeatable','true');
  }

  function patchAbilityCard(){
    const me=latest?.self;
    const heroId=Number(me?.hero_id||me?.skin_id||0);
    if(heroId!==7)return;
    setText(document.getElementById('abilityName'),'ВОЗВРАЩЕНИЕ В СЮЖЕТ');
    setText(document.getElementById('abilityHint'),'Повторное применение доступно каждые 5 минут');
  }

  function patch(){
    patchShield();
    patchHeroPreview();
    patchAbilityCard();
  }

  function schedulePatch(){
    if(patchQueued)return;
    patchQueued=true;
    requestAnimationFrame(()=>{
      patchQueued=false;
      patch();
    });
  }

  window.addEventListener('raid-state-updated',event=>acceptState(event.detail));
  document.addEventListener('click',()=>setTimeout(schedulePatch,0),true);

  const observer=new MutationObserver(schedulePatch);
  observer.observe(document.body,{
    childList:true,
    subtree:true,
    attributes:true,
    attributeFilter:['class','data-hero-id']
  });

  if(latest)acceptState(latest);
  setInterval(patchShield,1000);
})();
