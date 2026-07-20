(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const API_ROOT='/boss-app/api/boss/';
  const params=new URLSearchParams(location.search);
  const bossId=String(tg?.initDataUnsafe?.start_param||params.get('boss')||params.get('tgWebAppStartParam')||'').trim();
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const chainedFetch=window.fetch.bind(window);
  let state=null;
  let renderPending=false;

  function isStateUrl(input){
    const url=typeof input==='string'?input:String(input?.url||'');
    return url.includes('/boss-app/api/boss/session')||url.includes('/boss-app/api/boss/state')||url.includes('/boss-app/api/boss/action');
  }

  function accept(next){
    if(!next||!next.ok||!Array.isArray(next.fighters))return;
    state=next;
    queueRender();
  }

  window.fetch=async function(...args){
    const response=await chainedFetch(...args);
    if(isStateUrl(args[0]))response.clone().json().then(accept).catch(()=>{});
    return response;
  };

  const escapeHtml=value=>String(value??'').replace(/[&<>'"]/g,char=>({
    '&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'
  })[char]);

  function showToast(text,kind='success'){
    const toast=document.getElementById('toast');
    if(!toast)return;
    toast.textContent=text;
    toast.className=`toast show ${kind}`;
    clearTimeout(showToast.timer);
    showToast.timer=setTimeout(()=>{toast.className='toast'},2600);
  }

  function heroById(id){
    return (state?.hero_catalog||[]).find(hero=>Number(hero.id)===Number(id))||null;
  }

  function itemByKey(key){
    return (state?.shop||[]).find(item=>item.key===key)||null;
  }

  function rarityClass(rarity){
    const value=String(rarity||'').toLowerCase();
    if(value.includes('леген'))return 'legendary';
    if(value.includes('эпич'))return 'epic';
    return 'rare';
  }

  function itemCard(item,mode='shop'){
    const owned=Boolean(item.owned);
    const equipped=Boolean(item.equipped);
    const hero=heroById(item.hero_id);
    let action='';
    if(mode==='shop'&&!owned){
      action=`<button class="loadout-action buy" type="button" data-buy-item="${escapeHtml(item.key)}">КУПИТЬ · ${Number(item.price).toLocaleString('ru-RU')}</button>`;
    }else if(equipped){
      action='<button class="loadout-action equipped" type="button" data-unequip-item>СНЯТЬ</button>';
    }else{
      action=`<button class="loadout-action equip" type="button" data-equip-item="${escapeHtml(item.key)}">ЭКИПИРОВАТЬ</button>`;
    }
    return `<article class="loadout-item ${rarityClass(item.rarity)} ${equipped?'is-equipped':''}">
      <div class="loadout-art" aria-label="Будущее изображение предмета"><span>${escapeHtml(item.icon)}</span><small>АРТ ПОЯВИТСЯ ПОЗЖЕ</small></div>
      <div class="loadout-copy">
        <div class="loadout-meta"><em>${escapeHtml(item.rarity)}</em><span>${hero?escapeHtml(hero.name):'ПРЕДМЕТ ГЕРОЯ'}</span></div>
        <h3>${escapeHtml(item.name)}</h3>
        <p>${escapeHtml(item.description)}</p>
        ${action}
      </div>
    </article>`;
  }

  function shopMarkup(){
    const shop=state?.shop||[];
    return `<section class="loadout-page-head">
      <div><small>ВАШЕ ВЛИЯНИЕ</small><strong>${Number(state?.balance||0).toLocaleString('ru-RU')}</strong></div>
      <p>Предметы работают в рейде сразу после экипировки. Одновременно активен только один предмет.</p>
    </section>
    <div class="loadout-grid">${shop.map(item=>itemCard(item,'shop')).join('')}</div>`;
  }

  function inventoryMarkup(){
    const owned=(state?.shop||[]).filter(item=>item.owned);
    if(!owned.length){
      return '<div class="page-placeholder"><span class="page-placeholder-icon">🎒</span><h2>ИНВЕНТАРЬ ПУСТ</h2><p>Купи первый предмет в магазине. Генерированные изображения добавим отдельным обновлением.</p></div>';
    }
    return `<section class="loadout-page-head compact">
      <div><small>ЭКИПИРОВАНО</small><strong>${escapeHtml(itemByKey(state?.equipped_item)?.name||'НИЧЕГО')}</strong></div>
      <p>Выбери один предмет, пассивные бонусы которого будут действовать в бою.</p>
    </section>
    <div class="loadout-grid">${owned.map(item=>itemCard(item,'inventory')).join('')}</div>`;
  }

  function decorateSkins(){
    const page=document.getElementById('raidPage');
    if(!page?.classList.contains('open')||page.dataset.page!=='skins'||!state)return;
    const catalog=state.hero_catalog||[];
    catalog.forEach(hero=>{
      const card=page.querySelector(`[data-hero-skin="${hero.id}"]`);
      if(!card)return;
      if(card.dataset.loadoutHero===String(hero.id))return;
      card.dataset.loadoutHero=String(hero.id);
      const oldTitle=card.querySelector('b');
      if(oldTitle)oldTitle.remove();
      card.querySelector('.hero-card-copy')?.remove();
      const copy=document.createElement('span');
      copy.className='hero-card-copy';
      copy.innerHTML=`<strong>${escapeHtml(hero.name)}</strong><small>${escapeHtml(hero.title)}</small><em>${escapeHtml(hero.ability)}</em><p>${escapeHtml(hero.ability_hint)}</p>`;
      card.append(copy);
    });
    const intro=page.querySelector('.page-intro');
    if(intro)intro.textContent='Каждый образ теперь является отдельным героем со своим именем, характером и боевой способностью.';
  }

  function decorateFighters(){
    if(!state)return;
    const ordered=[...(state.fighters||[])].sort((a,b)=>Number(Boolean(b.is_self))-Number(Boolean(a.is_self))||Number(b.damage||0)-Number(a.damage||0));
    const cards=[...document.querySelectorAll('#fighters .fighter:not(.empty-fighter)')];
    cards.forEach((card,index)=>{
      const fighter=ordered[index];
      if(!fighter)return;
      let label=card.querySelector('.fighter-hero-name');
      if(!label){
        label=document.createElement('div');
        label.className='fighter-hero-name';
        card.append(label);
      }
      label.innerHTML=fighter.hero_name?`<b>${escapeHtml(fighter.hero_name)}</b><small>${escapeHtml(fighter.hero_title||'')}</small>`:'<b>БЕЗ ОБРАЗА</b><small>Выбери героя</small>';
      let item=card.querySelector('.fighter-equipped-item');
      if(fighter.equipped_item_name){
        if(!item){item=document.createElement('div');item.className='fighter-equipped-item';card.append(item);}
        item.textContent=`◆ ${fighter.equipped_item_name}`;
      }else item?.remove();
    });
  }

  function renderAbility(){
    const self=state?.self;
    if(!self)return;
    const label=document.querySelector('.ability-card .ability-copy>small');
    const name=document.getElementById('abilityName');
    const hint=document.getElementById('abilityHint');
    if(label)label.textContent=self.hero_name?'СПОСОБНОСТЬ ГЕРОЯ':'СПОСОБНОСТЬ РОЛИ';
    if(name&&self.ability_name)name.textContent=self.ability_name;
    if(hint&&self.ability_hint)hint.textContent=self.ability_hint;
    const card=document.querySelector('.ability-card');
    if(card){
      card.dataset.heroId=String(self.hero_id||0);
      card.classList.toggle('once-used',Boolean(self.ability_once_used));
      const battle=state?.battle||{};
      const active=battle.status==='active'&&Number(battle.hp)>0;
      if(Number(self.hero_id)===7&&!self.ability_once_used&&active){
        card.disabled=false;
        const cd=document.getElementById('abilityCooldown');
        if(cd)cd.textContent=Number(self.hp)<=0?'ВОЗРОДИТЬСЯ':'ГОТОВО';
      }
    }
  }

  function renderPage(){
    const page=document.getElementById('raidPage');
    if(!page?.classList.contains('open')||!state)return;
    const scroll=page.querySelector('.raid-page-scroll');
    if(!scroll)return;
    if(page.dataset.page==='shop'){
      const key=`shop:${state.balance}:${state.equipped_item}:${(state.inventory||[]).join(',')}`;
      if(scroll.dataset.loadoutKey!==key){scroll.dataset.loadoutKey=key;scroll.innerHTML=shopMarkup();}
    }else if(page.dataset.page==='inventory'){
      const key=`inventory:${state.equipped_item}:${(state.inventory||[]).join(',')}`;
      if(scroll.dataset.loadoutKey!==key){scroll.dataset.loadoutKey=key;scroll.innerHTML=inventoryMarkup();}
    }else if(page.dataset.page==='skins'){
      decorateSkins();
    }
  }

  function renderAll(){
    renderPending=false;
    renderAbility();
    decorateFighters();
    renderPage();
  }

  function queueRender(){
    if(renderPending)return;
    renderPending=true;
    requestAnimationFrame(renderAll);
  }

  async function action(actionName,itemKey=''){
    if(!bossId||!tg?.initData){showToast('Открой рейд через Telegram.','error');return;}
    try{
      const response=await chainedFetch(`${API_ROOT}action`,{
        method:'POST',headers,
        body:JSON.stringify({boss_id:bossId,action:actionName,item_key:itemKey})
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      accept(data);
      showToast(data.message||'Готово.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
    }catch(error){
      showToast(error.message||'Действие не выполнено.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }
  }

  document.addEventListener('click',event=>{
    const buy=event.target.closest('[data-buy-item]');
    if(buy){event.preventDefault();event.stopImmediatePropagation();action('buy_item',buy.dataset.buyItem);return;}
    const equip=event.target.closest('[data-equip-item]');
    if(equip){event.preventDefault();event.stopImmediatePropagation();action('equip_item',equip.dataset.equipItem);return;}
    const unequip=event.target.closest('[data-unequip-item]');
    if(unequip){event.preventDefault();event.stopImmediatePropagation();action('unequip_item');}
  },true);

  new MutationObserver(queueRender).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['class','data-page']});
  setInterval(()=>{renderAbility();renderPage();},700);
  queueRender();
})();
