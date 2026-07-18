(()=>{
  'use strict';

  const DEFENCE_SRC='/boss-app/assets/action_defense_v58.webp';

  function installDefenceArt(){
    const button=document.querySelector('[data-action="defend"]');
    if(!button)return;
    button.querySelectorAll('.action-card-art,.broken-action-art').forEach(node=>node.remove());
    const image=document.createElement('img');
    image.className='action-card-art action-card-art-defend';
    image.alt='';
    image.draggable=false;
    image.src=DEFENCE_SRC;
    image.addEventListener('error',()=>{
      image.classList.add('broken-action-art');
      image.style.display='none';
      button.style.setProperty('background','radial-gradient(circle at 50% 58%,#1b78d9,#07152d 58%,#030712)','important');
      const glyph=button.querySelector('.action-glyph');
      if(glyph)glyph.style.setProperty('display','grid','important');
    },{once:true});
    button.prepend(image);
    button.style.setProperty('background-image','none','important');
  }

  function patchHelp(){
    const page=document.querySelector('.raid-page-scroll');
    if(!page)return;
    const cards=[...page.querySelectorAll('.page-help-card')];
    const attack=cards.find(card=>card.querySelector('b')?.textContent.trim().toLowerCase()==='задеть эго');
    if(attack){
      attack.classList.add('damage-range');
      const text=attack.querySelector('small');
      if(text)text.textContent='Обычный удар: 200–500 урона. Критический удар: 2000–3000 урона. Перезарядка — 5 секунд. Щит ЧСВ может ослабить итоговый урон.';
    }
  }

  function keepAbilityHint(){
    const name=document.getElementById('abilityName');
    const hint=document.getElementById('abilityHint');
    if(!name||!hint)return;
    const descriptions={
      'НЕОЖИДАННО ОЖИТЬ':'Удар, лечение и блок восстановления босса.',
      'ПЫЛЬ В ГЛАЗА':'Срывает атаку и разбивает щит босса.',
      'ДАВЛЕНИЕ ТОЛПЫ':'Наносит урон и лечит весь отряд.',
      'УКРАСТЬ СЦЕНУ':'Сильный удар и защита от ответа босса.',
      'МИНУТА СЛАВЫ':'Мощный удар и мгновенный сброс атаки.',
      'УДАР ИЗ-ЗА КУЛИС':'Огромный урон с риском ответного удара.',
      'КУЛЬМИНАЦИЯ':'Гарантированный критический удар.',
      'ПРОБУЖДЕНИЕ ГЕРОЯ':'Усиленная способность вашей роли.'
    };
    const sync=()=>{
      const value=descriptions[name.textContent.trim().toUpperCase()];
      if(value&&hint.textContent!==value)hint.textContent=value;
    };
    sync();
    new MutationObserver(sync).observe(name,{childList:true,subtree:true,characterData:true});
  }

  /* Старые прозрачные зоны свайпа удаляем окончательно. Сама сцена теперь
     pointer-events:none, поэтому прокрутку обрабатывает Telegram/WebView нативно. */
  document.querySelectorAll('.boss-swipe-v23').forEach(node=>node.remove());

  installDefenceArt();
  keepAbilityHint();
  patchHelp();

  const raidPage=document.getElementById('raidPage');
  if(raidPage)new MutationObserver(patchHelp).observe(raidPage,{childList:true,subtree:true});
})();
