(()=>{
  'use strict';

  const combat=document.querySelector('.combat');
  const ability=document.querySelector('.ability-card');
  const battleLog=document.getElementById('battleLog');
  const logs=document.getElementById('logs');
  const fullLog=battleLog?.querySelector('.full-log');
  const attack=document.querySelector('[data-action="hit"]');
  const defend=document.querySelector('[data-action="defend"]');
  const heal=document.querySelector('[data-action="heal"]');

  document.documentElement.classList.add('fixed-combat-v18');
  document.body.classList.add('fixed-combat-v18');

  function syncReadyState(){
    [attack,defend,heal,ability].forEach(button=>{
      if(!button)return;
      button.classList.toggle('is-ready',!button.disabled);
      button.setAttribute('aria-disabled',String(Boolean(button.disabled)));
    });
    if(combat){
      combat.classList.toggle('attack-ready',Boolean(attack&&!attack.disabled));
    }
  }

  function visibleLogCount(){
    if(!logs)return 0;
    return [...logs.children].filter(node=>node.nodeType===1).length;
  }

  function syncLogButton(){
    if(!fullLog||!battleLog)return;
    const count=visibleLogCount();
    const expanded=battleLog.classList.contains('expanded');
    fullLog.textContent=expanded?'СВЕРНУТЬ ХРОНИКУ':count>3?`ПОЛНАЯ ХРОНИКА · ${count}`:'ХРОНИКА БОЯ';
    fullLog.setAttribute('aria-expanded',String(expanded));
    fullLog.hidden=count<=3&&!expanded;
  }

  if(fullLog&&battleLog){
    fullLog.removeAttribute('data-scroll');
    fullLog.addEventListener('click',event=>{
      event.preventDefault();
      event.stopImmediatePropagation();
      battleLog.classList.toggle('expanded');
      syncLogButton();
      if(!battleLog.classList.contains('expanded')){
        battleLog.scrollIntoView({behavior:'smooth',block:'nearest'});
      }
      try{window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.('light')}catch(_error){}
    },true);
  }

  const observer=new MutationObserver(()=>{
    syncReadyState();
    syncLogButton();
  });

  if(combat)observer.observe(combat,{subtree:true,attributes:true,attributeFilter:['disabled','class'],childList:true,characterData:true});
  if(ability)observer.observe(ability,{subtree:true,attributes:true,attributeFilter:['disabled','class'],childList:true,characterData:true});
  if(logs)observer.observe(logs,{subtree:true,childList:true,characterData:true});

  syncReadyState();
  syncLogButton();
})();
