(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const modal=document.getElementById('modal');
  const modalContent=document.getElementById('modalContent');
  const toast=document.getElementById('toast');
  const fighters=document.getElementById('fighters');
  const navButtons=[...document.querySelectorAll('.bottom-nav button')];
  const skinsButton=navButtons.at(-1);
  const chooseHero=document.querySelector('.squad-section .section-head>button');
  const userId=String(tg?.initDataUnsafe?.user?.id||'guest');
  const storageKey=`bossHeroSkin:${userId}`;
  const SKINS=Array.from({length:6},(_,index)=>({
    id:index+1,
    src:`/boss-app/assets/hero_skin_${index+1}.svg`
  }));

  function selectedSkin(){
    const value=Number(localStorage.getItem(storageKey)||1);
    return value>=1&&value<=SKINS.length?value:1;
  }

  function showToast(text,type='success'){
    if(!toast)return;
    toast.textContent=text;
    toast.className=`toast show ${type}`;
    clearTimeout(showToast.timer);
    showToast.timer=setTimeout(()=>{toast.className='toast'},2200);
  }

  function skinsMarkup(){
    const selected=selectedSkin();
    const filled=SKINS.map((skin,index)=>{
      const number=index+1;
      return `<button class="skin-slot ${selected===number?'selected':''}" type="button" data-hero-skin="${number}" aria-label="Выбрать образ ${number}">
        <span class="skin-number">${number}/8</span>
        <span class="skin-picture"><img src="${skin.src}" alt=""></span>
        <b>ОБРАЗ</b>
      </button>`;
    }).join('');
    const empty=[7,8].map(number=>`<button class="skin-slot skin-empty" type="button" data-empty-skin="${number}">
      <span class="skin-number">${number}/8</span>
      <span class="skin-placeholder">◇</span>
      <b>ПУСТОЙ СЛОТ</b>
      <small>Образ появится позже</small>
    </button>`).join('');
    return `<h2 class="skin-picker-title">ОБРАЗЫ ГЕРОЯ</h2><div class="skin-grid">${filled}${empty}</div>`;
  }

  function setActiveNav(button){
    if(!button)return;
    navButtons.forEach(item=>item.classList.toggle('active',item===button));
  }

  function openSkins(){
    if(!modal||!modalContent)return;
    modalContent.dataset.type='skins';
    modalContent.innerHTML=skinsMarkup();
    modal.classList.add('open');
    modal.setAttribute('aria-hidden','false');
    document.body.style.overflow='hidden';
    setActiveNav(skinsButton);
    tg?.BackButton?.show?.();
    tg?.HapticFeedback?.impactOccurred?.('light');
  }

  function decorateSelfFighter(){
    const card=document.querySelector('.fighter.self');
    const avatar=card?.querySelector('.fighter-avatar');
    if(!card||!avatar)return;
    const index=selectedSkin();
    const skin=SKINS[index-1];
    if(!skin)return;
    card.dataset.heroSkin=String(index);
    avatar.dataset.selectedSkin=String(index);
    let image=avatar.querySelector('.fighter-skin-image');
    if(!image){
      image=document.createElement('img');
      image.className='fighter-skin-image';
      image.alt='';
      avatar.appendChild(image);
    }
    if(image.getAttribute('src')!==skin.src)image.setAttribute('src',skin.src);
  }

  function chooseSkin(index){
    if(!SKINS[index-1])return;
    localStorage.setItem(storageKey,String(index));
    document.querySelectorAll('[data-hero-skin]').forEach(button=>{
      button.classList.toggle('selected',Number(button.dataset.heroSkin)===index);
    });
    decorateSelfFighter();
    tg?.HapticFeedback?.notificationOccurred?.('success');
    showToast('Образ героя выбран.');
  }

  if(skinsButton){
    skinsButton.dataset.modal='skins';
    skinsButton.setAttribute('aria-label','Образы героя');
  }
  if(chooseHero)chooseHero.dataset.modal='skins';

  document.addEventListener('click',event=>{
    const opener=event.target.closest('[data-modal="skins"]');
    if(opener){
      event.preventDefault();
      event.stopImmediatePropagation();
      openSkins();
      return;
    }

    const skinButton=event.target.closest('[data-hero-skin]');
    if(skinButton){
      event.preventDefault();
      event.stopImmediatePropagation();
      chooseSkin(Number(skinButton.dataset.heroSkin));
      return;
    }

    const emptyButton=event.target.closest('[data-empty-skin]');
    if(emptyButton){
      event.preventDefault();
      event.stopImmediatePropagation();
      showToast(`Слот ${emptyButton.dataset.emptySkin} пока пуст.`,'info');
      tg?.HapticFeedback?.notificationOccurred?.('warning');
    }
  },true);

  if(fighters){
    new MutationObserver(decorateSelfFighter).observe(fighters,{childList:true,subtree:true});
  }
  SKINS.forEach(skin=>{const image=new Image();image.src=skin.src});
  decorateSelfFighter();
})();