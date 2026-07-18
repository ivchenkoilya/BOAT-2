(()=>{
  'use strict';

  const fighters=document.getElementById('fighters');
  const logs=document.getElementById('logs');
  const stage=document.getElementById('bossStage');
  const bossImage=document.getElementById('bossImage');

  /* Full innerHTML replacement restarted every glow animation. Skip identical markup. */
  function stabilizeHtml(element){
    if(!element)return;
    const descriptor=Object.getOwnPropertyDescriptor(Element.prototype,'innerHTML');
    if(!descriptor?.get||!descriptor?.set)return;
    let last=descriptor.get.call(element);
    Object.defineProperty(element,'innerHTML',{
      configurable:true,
      get(){return descriptor.get.call(this)},
      set(value){
        const next=String(value);
        if(next===last)return;
        const scrollLeft=this.scrollLeft;
        last=next;
        descriptor.set.call(this,next);
        this.scrollLeft=scrollLeft;
      }
    });
  }
  stabilizeHtml(fighters);
  stabilizeHtml(logs);

  /* Turn generated backgrounds into real images, so no later background rule can hide them. */
  function installActionArt(selector,kind){
    const button=document.querySelector(selector);
    if(!button||button.querySelector('.action-card-art'))return;
    const computed=getComputedStyle(button).backgroundImage;
    if(!computed||computed==='none'){
      button.classList.add('action-art-fallback',`action-art-${kind}`);
      return;
    }
    const match=computed.match(/^url\((['"]?)(.*)\1\)$/s);
    if(!match?.[2])return;
    const image=document.createElement('img');
    image.className=`action-card-art action-card-art-${kind}`;
    image.alt='';
    image.draggable=false;
    image.src=match[2];
    button.prepend(image);
    button.style.setProperty('background-image','none','important');
  }
  installActionArt('[data-action="defend"]','defend');
  installActionArt('[data-action="hit"]','hit');
  installActionArt('[data-action="heal"]','heal');

  /* Concise ability descriptions. */
  const descriptions={
    'НЕОЖИДАННО ОЖИТЬ':'Удар, лечение и блок восстановления босса.',
    'ПЫЛЬ В ГЛАЗА':'Срывает атаку и разбивает щит босса.',
    'ДАВЛЕНИЕ ТОЛПЫ':'Наносит урон и лечит весь отряд.',
    'УКРАСТЬ СЦЕНУ':'Сильный удар и защита от ответа босса.',
    'МИНУТА СЛАВЫ':'Мощный удар и сброс обычной атаки.',
    'УДАР ИЗ-ЗА КУЛИС':'Огромный урон с риском ответного удара.',
    'КУЛЬМИНАЦИЯ':'Гарантированный сокрушительный критический удар.',
    'ПРОБУЖДЕНИЕ ГЕРОЯ':'Особая усиленная способность вашей роли.'
  };
  const abilityName=document.getElementById('abilityName');
  const abilityHint=document.getElementById('abilityHint');
  function syncAbilityDescription(){
    if(!abilityName||!abilityHint)return;
    const name=abilityName.textContent.trim().toUpperCase();
    const text=descriptions[name];
    if(text&&abilityHint.textContent!==text)abilityHint.textContent=text;
  }
  syncAbilityDescription();
  if(abilityName)new MutationObserver(()=>queueMicrotask(syncAbilityDescription)).observe(abilityName,{childList:true,subtree:true,characterData:true});

  /* Remove the blocking overlay and use the actual scroll root as a manual fallback. */
  document.querySelectorAll('.boss-swipe-v23').forEach(node=>node.remove());
  if(bossImage){bossImage.draggable=false;bossImage.setAttribute('draggable','false')}

  function scrollRoot(){
    const candidates=[document.scrollingElement,document.documentElement,document.body,document.querySelector('.app')].filter(Boolean);
    return candidates.find(node=>node.scrollHeight>node.clientHeight+4)||document.scrollingElement||document.documentElement;
  }

  if(stage){
    let gesture=null;
    stage.addEventListener('touchstart',event=>{
      if(event.touches.length!==1)return;
      const touch=event.touches[0];
      gesture={x:touch.clientX,y:touch.clientY};
    },{capture:true,passive:true});

    stage.addEventListener('touchmove',event=>{
      if(!gesture||event.touches.length!==1)return;
      const touch=event.touches[0];
      const dx=touch.clientX-gesture.x;
      const dy=touch.clientY-gesture.y;
      if(Math.abs(dy)<2||Math.abs(dx)>Math.abs(dy)*1.2)return;
      const root=scrollRoot();
      const before=root.scrollTop;
      root.scrollTop=before-dy;
      if(root.scrollTop===before)window.scrollBy(0,-dy);
      gesture.x=touch.clientX;
      gesture.y=touch.clientY;
      event.preventDefault();
      event.stopPropagation();
    },{capture:true,passive:false});

    const clear=()=>{gesture=null};
    stage.addEventListener('touchend',clear,{capture:true,passive:true});
    stage.addEventListener('touchcancel',clear,{capture:true,passive:true});
  }
})();
