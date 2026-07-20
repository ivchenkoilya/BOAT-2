(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const API_ROOT='/boss-app/api/boss/';
  const HERO_LABELS={
    1:{name:'Каблучий',title:'Узник обручального кольца'},
    2:{name:'Вайбус',title:'Призрак общей сходки'},
    3:{name:'Солёний',title:'Владыка тухлых кроссовок'},
    4:{name:'Сейфзоний',title:'Безопасная зона'},
    5:{name:'Самозваний',title:'Ложный главный герой'},
    6:{name:'Сливариус',title:'Малый дипломат'},
    7:{name:'Былогерий',title:'Наследник былой славы'}
  };
  const SKINS=Array.from({length:7},(_,index)=>({
    id:index+1,
    src:`/boss-app/assets/hero_skin_${index+1}.svg?v=102`
  }));
  const params=new URLSearchParams(location.search);
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const nativeFetch=window.fetch.bind(window);
  let bossId='';
  let latestState=null;
  let renderQueued=false;
  let loadingState=false;

  function readBossId(){
    let stored='';
    try{stored=sessionStorage.getItem('raid:last-boss-id')||'';}catch(_error){}
    return String(
      window.__raidBossId||
      tg?.initDataUnsafe?.start_param||
      params.get('boss')||
      params.get('tgWebAppStartParam')||
      stored||
      ''
    ).trim();
  }

  function rememberBossId(value){
    const id=String(value||'').trim();
    if(!id)return;
    bossId=id;
    window.__raidBossId=id;
    try{sessionStorage.setItem('raid:last-boss-id',id);}catch(_error){}
  }

  bossId=readBossId();

  function isBossStateUrl(value){
    const url=typeof value==='string'?value:String(value?.url||'');
    return url.includes('/boss-app/api/boss/session')||url.includes('/boss-app/api/boss/state')||url.includes('/boss-app/api/boss/action');
  }

  function acceptState(data){
    if(!data||!data.ok||!Array.isArray(data.fighters))return;
    rememberBossId(data?.battle?.boss_id||data?.boss_id||readBossId());
    latestState=data;
    window.__raidBossState=data;
    queueRender();
  }

  window.fetch=async function(...args){
    const response=await nativeFetch(...args);
    if(isBossStateUrl(args[0]))response.clone().json().then(acceptState).catch(()=>{});
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

  function setData(element,key,value){
    const text=String(value);
    if(element.dataset[key]!==text)element.dataset[key]=text;
  }

  function clearData(element,key){
    if(Object.prototype.hasOwnProperty.call(element.dataset,key))delete element.dataset[key];
  }

  function setCardSkin(card,fighter){
    if(!card||!fighter)return;
    const userId=Number(fighter.user_id||0);
    const skin=skinById(fighter.skin_id);
    setData(card,'userId',userId);
    const avatar=card.querySelector('.fighter-avatar');
    if(!avatar)return;

    let image=avatar.querySelector('.fighter-skin-image');
    if(!skin){
      clearData(card,'heroSkin');
      clearData(avatar,'selectedSkin');
      image?.remove();
      return;
    }

    setData(card,'heroSkin',skin.id);
    setData(avatar,'selectedSkin',skin.id);
    if(!image){
      image=document.createElement('img');
      image.className='fighter-skin-image';
      image.alt='';
      image.decoding='async';
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
    const ordered=orderedFighters();
    const byId=new Map((latestState?.fighters||[]).map(fighter=>[String(fighter.user_id),fighter]));
    document.querySelectorAll('.page-heroes-grid .fighter:not(.empty-fighter)').forEach((card,index)=>{
      const fighter=byId.get(String(card.dataset.userId||''))||ordered[index];
      if(fighter)setCardSkin(card,fighter);
    });
  }

  function selectedSkinId(){
    return Number(latestState?.self?.skin_id||latestState?.hero_skins?.selected||0);
  }

  function galleryMarkup(){
    const selected=selectedSkinId();
    const filled=SKINS.map(skin=>{
      const hero=HERO_LABELS[skin.id];
      return `
       <button class="page-skin-slot hero-skin-card ${selected===skin.id?'selected':''}" type="button" data-hero-skin="${skin.id}" aria-label="Открыть героя ${hero.name}">
         <em>${skin.id}/8</em>
         <span class="page-skin-picture"><img src="${skin.src}" alt="" decoding="async"></span>
         <span class="hero-card-copy"><strong>${hero.name}</strong><small>${hero.title}</small></span>
       </button>`;
    }).join('');
    const empty=`
      <button class="page-skin-slot hero-skin-empty" type="button" data-empty-skin="8">
        <em>8/8</em><span class="slot-orb">◇</span><b>ПУСТОЙ СЛОТ</b><small>Образ появится позже</small>
      </button>`;
    return filled+empty;
  }

  function renderGallery(){
    const page=document.getElementById('raidPage');
    if(!page?.classList.contains('open')||page.dataset.page!=='skins')return;
    const grid=page.querySelector('.page-skin-grid');
    if(!grid)return;
    const key=`${selectedSkinId()}:${SKINS.length}:107`;
    if(grid.dataset.heroSkinsKey===key&&grid.querySelector('[data-hero-skin]'))return;
    setData(grid,'heroSkinsKey',key);
    grid.innerHTML=galleryMarkup();
    const intro=page.querySelector('.page-intro');
    const text='Нажми на героя, чтобы открыть его лор, уникальную способность, особый предмет и все баффы.';
    if(intro&&intro.textContent!==text)intro.textContent=text;
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
    bossId=readBossId();
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
    bossId=readBossId();
    if(!bossId||!tg?.initData){
      const toast=document.getElementById('toast');
      if(toast){toast.textContent='Не удалось определить активный рейд. Закрой и снова открой бой.';toast.className='toast show error';}
      return false;
    }
    button?.classList.add('saving');
    try{
      const response=await nativeFetch(`${API_ROOT}action`,{
        method:'POST',headers,
        body:JSON.stringify({boss_id:bossId,action:'select_skin',skin_id:skinId})
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось выбрать образ.');
      acceptState(data);
      tg?.HapticFeedback?.notificationOccurred?.('success');
      const toast=document.getElementById('toast');
      if(toast){
        toast.textContent='Герой выбран и виден всему отряду.';
        toast.className='toast show success';
        clearTimeout(chooseSkin.toastTimer);
        chooseSkin.toastTimer=setTimeout(()=>{toast.className='toast'},2300);
      }
      return true;
    }catch(error){
      tg?.HapticFeedback?.notificationOccurred?.('error');
      const toast=document.getElementById('toast');
      if(toast){
        toast.textContent=error.message||'Не удалось выбрать героя.';
        toast.className='toast show error';
        clearTimeout(chooseSkin.toastTimer);
        chooseSkin.toastTimer=setTimeout(()=>{toast.className='toast'},2600);
      }
      return false;
    }finally{
      button?.classList.remove('saving');
    }
  }

  document.addEventListener('click',event=>{
    const button=event.target.closest('.page-skin-slot[data-hero-skin]');
    if(!button)return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const heroId=Number(button.dataset.heroSkin);
    const previewEvent=new CustomEvent('hero-preview-request',{
      cancelable:true,
      detail:{
        heroId,
        button,
        state:latestState,
        choose:()=>chooseSkin(heroId,button)
      }
    });
    const directSelection=window.dispatchEvent(previewEvent);
    if(directSelection)chooseSkin(heroId,button);
  },true);

  window.addEventListener('raid-state-updated',event=>acceptState(event.detail));
  if(window.__raidBossState)acceptState(window.__raidBossState);

  const observer=new MutationObserver(queueRender);
  observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['class','data-page']});

  SKINS.forEach(skin=>{const image=new Image();image.decoding='async';image.src=skin.src});
  setTimeout(loadState,100);
  setTimeout(loadState,500);
  setTimeout(loadState,1400);
  setInterval(loadState,12000);
  queueRender();
})();