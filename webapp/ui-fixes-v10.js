(()=>{
  'use strict';
  const $=id=>document.getElementById(id);
  const modal=$('modal'), content=$('modalContent');

  function scaleHpText(){
    document.querySelectorAll('.fighter').forEach(card=>{
      const hpText=card.querySelector(':scope > em');
      const bar=card.querySelector('.player-hp i');
      if(!hpText||!bar)return;
      const m=hpText.textContent.match(/(\d[\d\s]*)\s*\/\s*(\d[\d\s]*)/);
      if(!m)return;
      const hp=Number(m[1].replace(/\s/g,''))||0;
      const max=Number(m[2].replace(/\s/g,''))||1;
      const shownMax=300;
      const shownHp=Math.max(0,Math.round(hp/max*shownMax));
      hpText.textContent=`${shownHp}/${shownMax}`;
      bar.style.width=`${Math.max(0,Math.min(100,shownHp/shownMax*100))}%`;
    });
  }

  function heroSkins(){
    const names=['Текущий герой','Повелитель эго','Тёмный аристократ','Космический король','Разрушитель ЧСВ','Золотой избранник','Безликий герой','Последний образ'];
    const icons=['👑','⚡','🌑','💎','💥','✨','🎭','🔒'];
    return `<h2 class="skin-picker-title">ОБРАЗЫ ГЕРОЯ</h2><p class="skin-picker-sub">Выбери внешний вид персонажа. Полные скины добавим позже.</p><div class="skin-grid">${names.map((n,i)=>`<button class="skin-slot ${i===0?'selected':''} ${i>0?'locked':''}" type="button" data-skin-slot="${i}"><span class="skin-avatar">${icons[i]}</span><b>${n}</b><small>${i===0?'ВЫБРАН':'Скин появится позже'}</small></button>`).join('')}</div>`;
  }

  document.addEventListener('click',e=>{
    const heroBtn=e.target.closest('[data-modal="heroes"]');
    if(!heroBtn)return;
    e.preventDefault();
    e.stopImmediatePropagation();
    content.dataset.type='skins';
    content.innerHTML=heroSkins();
    modal.classList.add('open');
    modal.setAttribute('aria-hidden','false');
    document.body.style.overflow='hidden';
    window.Telegram?.WebApp?.BackButton?.show?.();
  },true);

  document.addEventListener('click',e=>{
    const slot=e.target.closest('[data-skin-slot]');
    if(!slot)return;
    if(slot.classList.contains('locked')){
      window.Telegram?.WebApp?.showAlert?.('Этот скин пока в разработке.');
      return;
    }
  });

  const fighters=$('fighters');
  if(fighters)new MutationObserver(scaleHpText).observe(fighters,{childList:true,subtree:true,characterData:true});
  setInterval(scaleHpText,1200);
  scaleHpText();
})();
