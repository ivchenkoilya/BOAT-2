(()=>{
  'use strict';
  const classifyLogs=()=>{
    document.querySelectorAll('.log-entry').forEach(row=>{
      row.classList.remove('log-hit','log-heal','log-shield','log-boss');
      const text=row.textContent.toLowerCase();
      if(/леч|восстанов|hp/.test(text)) row.classList.add('log-heal');
      else if(/щит|защит|блок/.test(text)) row.classList.add('log-shield');
      else if(/центр вселенной|босс|сарказм|ослаб/.test(text)) row.classList.add('log-boss');
      else if(/урон|задел|крит|удар/.test(text)) row.classList.add('log-hit');
    });
  };
  const fighters=document.getElementById('fighters');
  const logs=document.getElementById('logs');
  if(fighters)new MutationObserver(()=>{
    document.querySelectorAll('.fighter').forEach((card,i)=>card.style.setProperty('--delay',`${i*70}ms`));
  }).observe(fighters,{childList:true,subtree:true});
  if(logs)new MutationObserver(classifyLogs).observe(logs,{childList:true,subtree:true,characterData:true});
  classifyLogs();

  document.addEventListener('click',e=>{
    const button=e.target.closest('.main-action,.side-action,.ability-card,.skin-slot');
    if(!button)return;
    button.classList.remove('premium-tap');
    void button.offsetWidth;
    button.classList.add('premium-tap');
    setTimeout(()=>button.classList.remove('premium-tap'),420);
  });

  const style=document.createElement('style');
  style.textContent=`
    .fighter{animation:cardRise .45s ease both;animation-delay:var(--delay,0ms)}
    @keyframes cardRise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
    .premium-tap{animation:premiumTap .4s ease!important}
    @keyframes premiumTap{35%{filter:brightness(1.35);transform:scale(.97)}100%{filter:none;transform:none}}
  `;
  document.head.appendChild(style);
})();
