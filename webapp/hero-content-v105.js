(()=>{
  'use strict';

  const BUFF_LABELS={
    permission_ring:'+12% защита · аварийный щит',
    lost_cross:'+8–20% дополнительный крит',
    developer_sock:'+5% урон · −7% урон босса',
    trust_scanner:'+10% уклон · +8% защита',
    false_crown:'+10–20% урон',
    diplomat_boots:'+12% уклон · +8% восстановление',
    faded_cloak:'+8–23% урон · спасение на 1 HP'
  };

  const chainedFetch=window.fetch.bind(window);
  let state=null;
  let queued=false;

  function isBossStateUrl(input){
    const url=typeof input==='string'?input:String(input?.url||'');
    return url.includes('/boss-app/api/boss/session')||url.includes('/boss-app/api/boss/state')||url.includes('/boss-app/api/boss/action');
  }

  function accept(next){
    if(!next||!next.ok||!Array.isArray(next.fighters))return;
    state=next;
    queueRender();
  }

  window.fetch=async function(...args){
    const response=await chainedFetch(...args);
    if(isBossStateUrl(args[0]))response.clone().json().then(accept).catch(()=>{});
    return response;
  };

  function orderedFighters(){
    return [...(state?.fighters||[])].sort((a,b)=>
      Number(Boolean(b.is_self))-Number(Boolean(a.is_self))||
      Number(b.damage||0)-Number(a.damage||0)
    );
  }

  function shortBuff(itemKey){
    if(BUFF_LABELS[itemKey])return BUFF_LABELS[itemKey];
    const item=(state?.shop||[]).find(entry=>entry.key===itemKey);
    return String(item?.description||'').trim();
  }

  function decorateSquad(){
    if(!state)return;
    const cards=[...document.querySelectorAll('#fighters .fighter:not(.empty-fighter)')];
    const fighters=orderedFighters();
    cards.forEach((card,index)=>{
      const fighter=fighters[index];
      if(!fighter)return;
      const itemKey=String(fighter.equipped_item||'');
      let buff=card.querySelector('.fighter-item-buff');
      if(!itemKey){
        buff?.remove();
        delete card.dataset.equippedBuff;
        return;
      }
      const text=shortBuff(itemKey);
      if(!text){
        buff?.remove();
        return;
      }
      if(!buff){
        buff=document.createElement('div');
        buff.className='fighter-item-buff';
        card.appendChild(buff);
      }
      if(buff.textContent!==text)buff.textContent=text;
      card.dataset.equippedBuff=itemKey;
      buff.title=text;
    });
  }

  function updateWelcomeText(){
    const text=document.querySelector('#welcomeOverlay .welcome-text');
    if(!text)return;
    const html=text.innerHTML.replace(/2[–-]3\s*дн(?:я|ей)/g,'1–2 дня');
    if(text.innerHTML!==html)text.innerHTML=html;
  }

  function render(){
    queued=false;
    updateWelcomeText();
    decorateSquad();
  }

  function queueRender(){
    if(queued)return;
    queued=true;
    requestAnimationFrame(render);
  }

  new MutationObserver(queueRender).observe(document.body,{
    childList:true,
    subtree:true,
    attributes:true,
    attributeFilter:['class','data-page']
  });

  setInterval(render,900);
  queueRender();
})();
