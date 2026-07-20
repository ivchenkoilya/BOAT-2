(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const API_ROOT='/boss-app/api/boss/';
  const params=new URLSearchParams(location.search);
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  let bossId='';

  const HERO_LABELS={
    1:{name:'Каблучий',title:'Узник обручального кольца'},
    2:{name:'Вайбус',title:'Призрак общей сходки'},
    3:{name:'Солёний',title:'Владыка тухлых кроссовок'},
    4:{name:'Сейфзоний',title:'Безопасная зона'},
    5:{name:'Самозваний',title:'Ложный главный герой'},
    6:{name:'Сливариус',title:'Малый дипломат'},
    7:{name:'Былогерий',title:'Наследник былой славы'}
  };

  const BUFF_LABELS={
    permission_ring:'+12% защита · аварийный щит',
    lost_cross:'+8–20% дополнительный крит',
    developer_sock:'+5% урон · −7% урон босса',
    trust_scanner:'+10% уклон · +8% защита',
    false_crown:'+10–20% урон',
    diplomat_boots:'+12% уклон · +8% восстановление',
    faded_cloak:'+8–23% урон · спасение на 1 HP'
  };

  let state=null;
  let loading=false;
  let queued=false;

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

  function acceptState(next){
    if(!next||!next.ok||!Array.isArray(next.fighters))return;
    rememberBossId(next?.battle?.boss_id||next?.boss_id||readBossId());
    state=next;
    window.__raidBossState=next;
    const scroll=document.querySelector('#raidPage .raid-page-scroll');
    if(scroll){
      scroll.removeAttribute('data-v105-key');
      scroll.removeAttribute('data-loadout-key');
    }
    queueRender();
  }

  bossId=readBossId();

  const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,char=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[char]);

  function showToast(text,kind='success'){
    const toast=document.getElementById('toast');
    if(!toast)return;
    toast.textContent=text;
    toast.className=`toast show ${kind}`;
    clearTimeout(showToast.timer);
    showToast.timer=setTimeout(()=>{toast.className='toast'},2600);
  }

  function rarityClass(rarity){
    const value=String(rarity||'').toLowerCase();
    if(value.includes('леген'))return 'legendary';
    if(value.includes('эпич'))return 'epic';
    return 'rare';
  }

  function heroById(id){
    return (state?.hero_catalog||[]).find(hero=>Number(hero.id)===Number(id))||HERO_LABELS[Number(id)]||null;
  }

  function itemByKey(key){
    return (state?.shop||[]).find(item=>item.key===key)||null;
  }

  function itemCard(item,mode='shop'){
    const owned=Boolean(item.owned);
    const equipped=Boolean(item.equipped);
    const hero=heroById(item.hero_id);
    let action='';
    if(mode==='shop'&&!owned){
      action=`<button class="loadout-action buy" type="button" data-v105-action="buy_item" data-v105-item="${escapeHtml(item.key)}">КУПИТЬ · ${Number(item.price||0).toLocaleString('ru-RU')}</button>`;
    }else if(equipped){
      action='<button class="loadout-action equipped" type="button" data-v105-action="unequip_item">СНЯТЬ</button>';
    }else{
      action=`<button class="loadout-action equip" type="button" data-v105-action="equip_item" data-v105-item="${escapeHtml(item.key)}">ЭКИПИРОВАТЬ</button>`;
    }
    return `<article class="loadout-item ${rarityClass(item.rarity)} ${equipped?'is-equipped':''}">
      <div class="loadout-art" aria-label="Будущее изображение предмета"><span>${escapeHtml(item.icon||'◇')}</span><small>АРТ ПОЯВИТСЯ ПОЗЖЕ</small></div>
      <div class="loadout-copy">
        <div class="loadout-meta"><em>${escapeHtml(item.rarity||'ПРЕДМЕТ')}</em><span>${escapeHtml(hero?.name||'ПРЕДМЕТ ГЕРОЯ')}</span></div>
        <h3>${escapeHtml(item.name||'Особый предмет')}</h3>
        <p>${escapeHtml(item.description||'')}</p>
        ${action}
      </div>
    </article>`;
  }

  function shopMarkup(){
    const shop=state?.shop||[];
    if(!shop.length)return '<div class="page-placeholder"><span class="page-placeholder-icon">🏪</span><h2>МАГАЗИН ЗАГРУЖАЕТСЯ</h2><p>Обновляем список особых предметов героев.</p></div>';
    return `<section class="loadout-page-head">
      <div><small>ВАШЕ ВЛИЯНИЕ</small><strong>${Number(state?.balance||0).toLocaleString('ru-RU')}</strong></div>
      <p>Предметы работают в рейде сразу после экипировки. Одновременно активен только один предмет.</p>
    </section><div class="loadout-grid">${shop.map(item=>itemCard(item,'shop')).join('')}</div>`;
  }

  function inventoryMarkup(){
    const owned=(state?.shop||[]).filter(item=>item.owned);
    if(!owned.length){
      return '<div class="page-placeholder"><span class="page-placeholder-icon">🎒</span><h2>ИНВЕНТАРЬ ПУСТ</h2><p>Купи первый предмет в магазине.</p></div>';
    }
    return `<section class="loadout-page-head compact">
      <div><small>ЭКИПИРОВАНО</small><strong>${escapeHtml(itemByKey(state?.equipped_item)?.name||'НИЧЕГО')}</strong></div>
      <p>Выбери один предмет, пассивные бонусы которого будут действовать в бою.</p>
    </section><div class="loadout-grid">${owned.map(item=>itemCard(item,'inventory')).join('')}</div>`;
  }

  function decorateGallery(){
    const page=document.getElementById('raidPage');
    if(!page?.classList.contains('open')||page.dataset.page!=='skins')return;

    Object.entries(HERO_LABELS).forEach(([id,hero])=>{
      const card=page.querySelector(`[data-hero-skin="${id}"]`);
      if(!card)return;
      const fallback=[...card.children].find(element=>element.tagName==='B');
      if(fallback)fallback.remove();
      let copy=card.querySelector('.hero-card-copy');
      if(!copy){
        copy=document.createElement('span');
        copy.className='hero-card-copy';
        card.appendChild(copy);
      }
      const markup=`<strong>${escapeHtml(hero.name)}</strong><small>${escapeHtml(hero.title)}</small>`;
      if(copy.innerHTML!==markup)copy.innerHTML=markup;
    });
  }

  function orderedFighters(){
    return [...(state?.fighters||[])].sort((a,b)=>
      Number(Boolean(b.is_self))-Number(Boolean(a.is_self))||
      Number(b.damage||0)-Number(a.damage||0)
    );
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
      if(!itemKey){buff?.remove();return;}
      const text=BUFF_LABELS[itemKey]||String(itemByKey(itemKey)?.description||'').trim();
      if(!text){buff?.remove();return;}
      if(!buff){buff=document.createElement('div');buff.className='fighter-item-buff';card.appendChild(buff);}
      if(buff.textContent!==text)buff.textContent=text;
      buff.title=text;
    });
  }

  function renderPage(){
    const page=document.getElementById('raidPage');
    if(!page?.classList.contains('open'))return;
    const scroll=page.querySelector('.raid-page-scroll');
    if(!scroll)return;
    if(page.dataset.page==='skins'){
      decorateGallery();
      return;
    }
    if(!state)return;
    if(page.dataset.page==='shop'){
      const key=`v107-shop:${state.balance}:${state.equipped_item}:${(state.inventory||[]).join(',')}`;
      if(scroll.dataset.v105Key!==key){scroll.dataset.v105Key=key;scroll.innerHTML=shopMarkup();}
    }else if(page.dataset.page==='inventory'){
      const key=`v107-inventory:${state.equipped_item}:${(state.inventory||[]).join(',')}`;
      if(scroll.dataset.v105Key!==key){scroll.dataset.v105Key=key;scroll.innerHTML=inventoryMarkup();}
    }
  }

  async function loadState(force=false){
    bossId=readBossId();
    if(loading||!bossId||!tg?.initData)return;
    if(state&&!force){queueRender();return;}
    loading=true;
    try{
      const response=await fetch(`${API_ROOT}state?boss_id=${encodeURIComponent(bossId)}`,{headers});
      const data=await response.json().catch(()=>null);
      acceptState(data);
    }catch(_error){}finally{loading=false;}
  }

  async function perform(actionName,itemKey=''){
    bossId=readBossId();
    if(!bossId||!tg?.initData){showToast('Не удалось определить активный рейд. Закрой и снова открой бой.','error');return;}
    try{
      const response=await fetch(`${API_ROOT}action`,{
        method:'POST',headers,
        body:JSON.stringify({boss_id:bossId,action:actionName,item_key:itemKey})
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      acceptState(data);
      showToast(data.message||'Готово.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
    }catch(error){
      showToast(error.message||'Действие не выполнено.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }
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
    decorateGallery();
    decorateSquad();
    renderPage();
  }

  function queueRender(){
    if(queued)return;
    queued=true;
    requestAnimationFrame(render);
  }

  document.addEventListener('click',event=>{
    const action=event.target.closest('[data-v105-action]');
    if(action){
      event.preventDefault();
      event.stopImmediatePropagation();
      perform(action.dataset.v105Action,action.dataset.v105Item||'');
      return;
    }
    const nav=event.target.closest('[data-modal="shop"],[data-modal="inventory"],[data-modal="heroes"]');
    if(nav)setTimeout(()=>{loadState(true);queueRender();},60);
  },true);

  window.addEventListener('raid-state-updated',event=>acceptState(event.detail));
  if(window.__raidBossState)acceptState(window.__raidBossState);

  new MutationObserver(queueRender).observe(document.body,{
    childList:true,subtree:true,attributes:true,attributeFilter:['class','data-page']
  });

  setTimeout(()=>loadState(true),100);
  setTimeout(()=>loadState(true),500);
  setTimeout(()=>loadState(true),1200);
  setInterval(()=>loadState(true),10000);
  setInterval(render,700);
  queueRender();
})();
