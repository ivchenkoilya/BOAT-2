(()=>{
  'use strict';
  const SKINS=[
    {name:'Фиолетовый герой',hint:'Энергия эго',color:'#c151ee'},
    {name:'Золотой избранник',hint:'Сияние лидера',color:'#f0b84f'},
    {name:'Алый разрушитель',hint:'Ярость и напор',color:'#e44e69'},
    {name:'Ледяной стратег',hint:'Холодный расчёт',color:'#4f95ee'},
    {name:'Хранитель жизни',hint:'Сила восстановления',color:'#50d687'},
    {name:'Огненный бунтарь',hint:'Неудержимый удар',color:'#ee7f40'},
    {name:'Астральный странник',hint:'Космическая аура',color:'#9c8cff'},
    {name:'Безликий герой',hint:'Таинственный образ',color:'#d3d7e5'}
  ];
  const KEY='boss-app-selected-skin';
  const getSelected=()=>Math.max(0,Math.min(7,Number(localStorage.getItem(KEY))||0));
  const markup=()=>{
    const selected=getSelected();
    return `<h2 class="skin-picker-title">ВЫБОР ГЕРОЯ</h2><p class="skin-picker-sub">Каждый участник рейда может выбрать одну из восьми иконок. Позже вместо них появятся полноценные скины.</p><div class="skin-grid">${SKINS.map((skin,i)=>`<button class="skin-slot ${i===selected?'selected':''}" type="button" data-hero-skin="${i}" style="--skin:${skin.color}"><span class="skin-icon" aria-hidden="true"></span><b>${skin.name}</b><small>${i===selected?'Используется сейчас':skin.hint}</small></button>`).join('')}</div>`;
  };
  function openPicker(){
    const modal=document.getElementById('modal');
    const content=document.getElementById('modalContent');
    if(!modal||!content)return;
    content.dataset.type='hero-skins';
    content.innerHTML=markup();
    modal.classList.add('open');
    modal.setAttribute('aria-hidden','false');
    document.body.style.overflow='hidden';
    window.Telegram?.WebApp?.BackButton?.show?.();
  }
  function applyToSelf(){
    const selected=getSelected();
    const skin=SKINS[selected];
    document.querySelectorAll('.fighter.self .fighter-avatar').forEach(avatar=>{
      avatar.dataset.selectedSkin=String(selected);
      avatar.style.setProperty('--skin-color',skin.color);
      avatar.setAttribute('title',skin.name);
    });
  }
  document.addEventListener('click',event=>{
    const open=event.target.closest('[data-modal="heroes"]');
    if(open){event.preventDefault();event.stopImmediatePropagation();openPicker();return;}
    const slot=event.target.closest('[data-hero-skin]');
    if(!slot)return;
    const selected=Number(slot.dataset.heroSkin)||0;
    localStorage.setItem(KEY,String(selected));
    document.querySelectorAll('[data-hero-skin]').forEach((node,i)=>{
      node.classList.toggle('selected',i===selected);
      const small=node.querySelector('small');
      if(small)small.textContent=i===selected?'Используется сейчас':SKINS[i].hint;
    });
    applyToSelf();
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred?.('success');
  },true);
  const fighters=document.getElementById('fighters');
  if(fighters)new MutationObserver(applyToSelf).observe(fighters,{childList:true,subtree:true});
  setInterval(applyToSelf,1200);
  applyToSelf();
})();