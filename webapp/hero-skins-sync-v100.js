(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const API_ROOT='/boss-app/api/boss/';
  const SKINS=Array.from({length:6},(_,index)=>({
    id:index+1,
    src:`/boss-app/assets/hero_skin_${index+1}.svg`
  }));
  const params=new URLSearchParams(location.search);
  const bossId=String(tg?.initDataUnsafe?.start_param||params.get('boss')||params.get('tgWebAppStartParam')||'').trim();
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const nativeFetch=window.fetch.bind(window);
  let latestState=null;
  let renderQueued=false;
  let loadingState=false;

  function isBossStateUrl(value){
    const url=typeof value==='string'?value:String(value?.url||'');
    return url.includes('/boss-app/api/boss/session')||url.includes('/boss-app/api/boss/state');
  }

  function acceptState(data){
    if(!data||!data.ok||!Array.isArray(data.fighters))return;
    latestState=data;
    queueRender();
  }

  window.fetch=async function(...args){
    const response=await nativeFetch(...args);
    if(isBossStateUrl(args[0])){
      response.clone().json().then(acceptState).catch(()=>{});
    }
    return response;
  };

  function orderedFighters(){
    return [...(latestState?.fighters||[])].sort((a,b)=>
      Number(Boolean(b.is_self))-Number(Boolean(a.is_self))||
      Number(b.damage||0)-Number(a.damage||0)
    );
  }

  function skinById(value){
    const id=Number(value||0);
    return SKINS.find(skin=>skin.id===id)||null;
  }

  function setCardSkin(card,fighter){
    if(!card||!fighter)return;
    const userId=Number(fighter.user_id||0);
    const skin=skinById(fighter.skin_id);
    card.dataset.userId=String(userId);
    const avatar=card.querySelector('.fighter-avatar');
    if(!avatar)return;

    let image=avatar.querySelector('.fighter-skin-image');
    if(!skin){
      delete card.dataset.heroSkin;
      delete avatar.dataset.selectedSkin;
      image?.remove();
      return;
    }

    card.dataset.heroSkin=String(skin.id);
    avatar.dataset.selectedSkin=String(skin.id);
    if(!image){
      image=document.createElement('img');
      image.className='fighter-skin-image';
      image.alt='';
      avatar.prepend(image);
    }
    if(image.getAttribute('src')!==skin.src)image.setAttribute('src',skin.src);
  }

  function decorateMainFighters(){
    const fighters=orderedFighters();
    const cards=[...document.querySelectorAll('#fighters .fighter:not(.empty-fighter)')];
    cards.forEach((card,index)=>setCardSkin(card,fighters[index]));
  }

  function decorateHeroesPage(){
    const byId=new Map((latestState?.fighters||[]).map(fighter=>[String(fighter.user_id),fighter]));
    document.querySelectorAll('.page-heroes-grid .fighter:not(.empty-fighter)').forEach((card,index)=>{
      const fighter=byId.get(String(card.dataset.userId||''))||orderedFighters()[index];
      if(fighter)setCardSkin(card,fighter);
    });
  }

  function selectedSkinId(){
    return Number(latestState?.self?.skin_id||latestState?.hero_skins?.selected||0);
  }

  function galleryMarkup(){
    const selected=selectedSkinId();
    const filled=SKINS.map(skin=>`
      <button class="page-skin-slot hero-skin-card ${selected===skin.id?'selected':''}" type="button" data-hero-skin="${skin.id}" aria-label="Выбрать образ ${skin.id}">
        <em>${skin.id}/8</em>
        <span class="page-skin-picture"><img src="${skin.src}" alt=""></span>
        <b>ОБРАЗ</b>
      </button>`).join('');
    const empty=[7,8].map(number=>`
      <button class="page-skin-slot hero-skin-empty" type="button" data-empty-skin="${number}">
        <em>${number}/8</em><span class="slot-orb">◇</span><b>ПУСТОЙ СЛОТ</b><small>Образ появится позже</small>
      </button>`).join('');
    return filled+empty;
  }

  function renderGallery(){
    const page=document.getElementById('raidPage');
    if(!page?.classList.contains('open')||page.dataset.page!=='skins')return;
    const grid=page.querySelector('.page-skin-grid');
    if(!grid)return;
    const key=`${selectedSkinId()}:${SKINS.length}`;
    if(grid.dataset.heroSkinsKey===key&&grid.querySelector('[data-hero-skin]'))return;
    grid.dataset.heroSkinsKey=key;
    grid.innerHTML=galleryMarkup();
    const intro=page.querySelector('.page-intro');
    if(intro)intro.textContent='Выбери образ героя. Выбранный портрет будет виден в карточке отряда у тебя и у остальных участников рейда.';
  }

  function renderAll(){
    renderQueued=false;
    decorateMainFighters();
    decorateHeroesPage();
    renderGallery();
  }

  function queueRender(){
    if(renderQueued)return;
    renderQueued=true;
    requestAnimationFrame(renderAll);
  }

  async function loadState(){
    if(loadingState||!bossId||!tg?.initData)return;
    loadingState=true;
    try{
      const response=await nativeFetch(`${API_ROOT}state?boss_id=${encodeURIComponent(bossId)}`,{headers});
      const data=await response.json().catch(()=>null);
      acceptState(data);
    }catch(_error){}finally{
      loadingState=false;
    }
  }

  async function chooseSkin(skinId,button){
    if(!bossId||!tg?.initData){
      window.dispatchEvent(new CustomEvent('hero-skin-error',{detail:'Открой рейд через Telegram, чтобы сохранить образ.'}));
      return;
    }
    button?.classList.add('saving');
    try{
      const response=await nativeFetch(`${API_ROOT}action`,{
        method:'POST',
        headers,
        body:JSON.stringify({boss_id:bossId,action:'select_skin',skin_id:skinId})
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось выбрать образ.');
      acceptState(data);
      tg?.HapticFeedback?.notificationOccurred?.('success');
      const toast=document.getElementById('toast');
      if(toast){
        toast.textContent='Образ сохранён и виден всему отряду.';
        toast.className='toast show success';
        clearTimeout(chooseSkin.toastTimer);
        chooseSkin.toastTimer=setTimeout(()=>{toast.className='toast'},2300);
      }
    }catch(error){
      tg?.HapticFeedback?.notificationOccurred?.('error');
      const toast=document.getElementById('toast');
      if(toast){
        toast.textContent=error.message||'Не удалось выбрать образ.';
        toast.className='toast show error';
        clearTimeout(chooseSkin.toastTimer);
        chooseSkin.toastTimer=setTimeout(()=>{toast.className='toast'},2600);
      }
    }finally{
      button?.classList.remove('saving');
    }
  }

  document.addEventListener('click',event=>{
    const button=event.target.closest('.page-skin-slot[data-hero-skin]');
    if(!button)return;
    event.preventDefault();
    event.stopImmediatePropagation();
    chooseSkin(Number(button.dataset.heroSkin),button);
  },true);

  const observer=new MutationObserver(queueRender);
  observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['class','data-page']});

  SKINS.forEach(skin=>{const image=new Image();image.src=skin.src});
  setTimeout(loadState,350);
  setTimeout(loadState,1400);
  setInterval(loadState,12000);
  queueRender();
})();