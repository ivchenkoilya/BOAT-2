(() => {
  'use strict';

  const tg = window.Telegram?.WebApp;
  const $ = id => document.getElementById(id);
  const fmt = value => new Intl.NumberFormat('ru-RU').format(Number(value) || 0);
  const params = new URLSearchParams(location.search);
  const startParam = String(tg?.initDataUnsafe?.start_param || params.get('tgWebAppStartParam') || params.get('startapp') || '');
  const chatId = params.get('chat_id') || '';
  const headers = {'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData || ''};
  const rarityNames = {common:'ОБЫЧНЫЙ',rare:'РЕДКИЙ',epic:'ЭПИЧЕСКИЙ',legendary:'ЛЕГЕНДАРНЫЙ'};
  const reasonNames = {
    chat_activity:'Активность в беседе',chat_activity_milestone:'Награда за активность',reaction_reward:'Полученная реакция',
    duel:'Битва эго',influence_roulette:'Рулетка влияния',admin_panel_points:'Изменение администратором',
    boss_center_of_universe_victory:'Победа над Центром Вселенной',direct_rebellion_reward:'Успешный бунт',
    direct_rebellion_failure:'Провал бунта',supported_rebellion_success:'Успешный бунт',supported_rebellion_failure:'Провал бунта',
    intervention_cost:'Вмешательство в сюжет',achievement_reward:'Награда достижения',inactive_return:'Возвращение персонажа',
    shop_custom_title:'Покупка титула',shop_roast_member:'Заказ прожарки',shop_extended_stats:'Расширенная статистика',
    shop_profile_frame:'Рамка профиля',shop_sabotage_shield:'Защита от саботажа',shop_mission_boost:'Усиление задания',
    shop_chat_event:'Запуск события',shop_hide_losses:'Скрытие поражений',shop_reroll_today_type:'Переброс типажа',
    shop_story_insurance:'Сюжетная страховка'
  };

  const iconPaths = {
    custom_title:'M4 7h16v10H4z M8 11h8 M8 14h5', roast_member:'M5 5h14v10H9l-4 4z M9 9h6 M9 12h4',
    extended_stats:'M5 19V9 M10 19V5 M15 19v-7 M20 19V3', profile_frame:'M5 5h14v14H5z M9 9h6v6H9z',
    sabotage_shield:'M12 3l8 3v5c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10V6z', mission_boost:'M12 3l2.2 5.1L20 9l-4 4 .9 5.8L12 16l-4.9 2.8L8 13 4 9l5.8-.9z',
    chat_event:'M4 5h16v12H8l-4 4z M8 9h8 M8 12h6', hide_losses:'M3 12s3.4-6 9-6 9 6 9 6-3.4 6-9 6-9-6-9-6z M9 9l6 6 M15 9l-6 6',
    reroll_today_type:'M7 7h10l-2-2 M17 17H7l2 2 M18 7a7 7 0 010 10 M6 17A7 7 0 016 7', story_insurance:'M12 3l7 4v5c0 4.5-2.8 7.5-7 9-4.2-1.5-7-4.5-7-9V7z M9 12l2 2 4-5',
    badge_fire:'M12 3c2 4-1 5 1 8 2-2 4-1 4 3a5 5 0 11-10 0c0-3 2-5 5-11z', badge_lightning:'M13 2L5 13h6l-1 9 9-13h-6z',
    badge_star:'M12 3l2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z', badge_crown:'M4 7l4 4 4-7 4 7 4-4-2 11H6z',
    name_gold:'M4 18h16 M7 15l5-10 5 10 M9 12h6', name_neon:'M4 18h16 M7 15l5-10 5 10 M9 12h6',
    profile_glow:'M12 3v3 M12 18v3 M3 12h3 M18 12h3 M5.6 5.6l2.1 2.1 M16.3 16.3l2.1 2.1 M18.4 5.6l-2.1 2.1 M7.7 16.3l-2.1 2.1 M12 8a4 4 0 100 8 4 4 0 000-8z',
    background_noir:'M4 5h16v14H4z M4 15l5-5 4 4 3-3 4 4', background_crimson:'M4 5h16v14H4z M7 16l4-7 3 5 3-3', background_cosmos:'M4 5h16v14H4z M8 9h.01 M16 8h.01 M13 14h.01 M7 16h.01',
    frame_ice:'M5 5h14v14H5z M8 2v4 M16 2v4 M8 18v4 M16 18v4 M2 8h4 M18 8h4 M2 16h4 M18 16h4',
    frame_crimson:'M5 5h14v14H5z M8 8l8 8 M16 8l-8 8', frame_cosmos:'M5 5h14v14H5z M9 9h.01 M15 9h.01 M12 12h.01 M9 15h.01 M15 15h.01',
    frame_crown:'M5 7h14v12H5z M7 7l2-4 3 4 3-4 2 4 M9 12h6'
  };
  const iconTones = {
    custom_title:'violet',roast_member:'crimson',extended_stats:'cyan',profile_frame:'gold',sabotage_shield:'cyan',mission_boost:'crimson',chat_event:'cosmos',hide_losses:'noir',reroll_today_type:'violet',story_insurance:'gold',
    badge_fire:'crimson',badge_lightning:'cyan',badge_star:'violet',badge_crown:'gold',name_gold:'gold',name_neon:'violet',profile_glow:'cosmos',background_noir:'noir',background_crimson:'crimson',background_cosmos:'cosmos',frame_ice:'cyan',frame_crimson:'crimson',frame_cosmos:'cosmos',frame_crown:'gold'
  };

  let live = null;
  let lastBalance = null;
  let activePeriod = '7';
  let pollTimer = null;
  let requestActive = false;
  let requestController = null;
  let firstRequestFinished = false;
  let customSelected = null;
  let customPurchaseBusy = false;
  let baseConfirmHandler = null;
  let toastTimer = null;

  function esc(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function requestId(){return crypto?.randomUUID?.() || `v1842-${Date.now()}-${Math.random().toString(36).slice(2)}`;}
  function numberFromText(text){return Number(String(text||'').replace(/[^0-9]/g,''))||0;}
  function iconSvg(key,extraClass=''){
    const path=iconPaths[key]||'M12 3l3 6 6 3-6 3-3 6-3-6-6-3 6-3z';
    return `<span class="v1842-icon tone-${iconTones[key]||'violet'} ${extraClass}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"/></svg><i></i></span>`;
  }
  function syncStatus(text,kind='online'){
    const node=$('liveSync');if(!node)return;
    node.className=`sync-status ${kind}`;const span=node.querySelector('span');if(span)span.textContent=text;
  }
  function notify(text,type='info'){
    const node=$('toast');if(!node)return;node.textContent=text;node.className=`toast show ${type}`;
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>{node.className='toast';},2800);
  }
  function animateValue(node,from,to){
    if(!node)return;const start=performance.now(),diff=Number(to)-Number(from);
    function frame(now){const t=Math.min(1,(now-start)/520),e=1-Math.pow(1-t,3);node.textContent=fmt(Math.round(Number(from)+diff*e));if(t<1)requestAnimationFrame(frame);}
    requestAnimationFrame(frame);
  }
  function showDelta(delta){
    const node=$('liveDelta');if(!node||!delta)return;node.textContent=`${delta>0?'+':'−'}${fmt(Math.abs(delta))} влияния`;
    node.className=`live-delta ${delta<0?'loss':''}`;void node.offsetWidth;node.classList.add('show');tg?.HapticFeedback?.notificationOccurred?.(delta>0?'success':'warning');
  }
  function currentPeriod(){const active=document.querySelector('#periodTabs button.active');return String(active?.dataset.days||activePeriod||'7');}

  function applyCosmetics(){
    const cosmetics=live?.cosmetics||{},header=document.querySelector('.hero-header'),avatarWrap=$('avatarWrap'),name=$('profileName');
    if(header){header.dataset.background=cosmetics.background?.key||'';header.dataset.glow=cosmetics.glow?.key||'';}
    if(avatarWrap){avatarWrap.dataset.v1842Frame=cosmetics.frame?.key||'';}
    if(name){name.dataset.nameStyle=cosmetics.name_style?.key||'';}
    let badge=$('profileBadge1842');
    if(!badge&&name){badge=document.createElement('span');badge.id='profileBadge1842';badge.className='profile-badge-1842';name.insertAdjacentElement('afterend',badge);}
    const badgeKey=cosmetics.badge?.key||'';
    if(badge){badge.dataset.badge=badgeKey;badge.innerHTML=badgeKey?iconSvg(`badge_${badgeKey}`,'mini'):'';badge.hidden=!badgeKey;}
  }
  function applyProfile(){
    if(!live?.profile)return;const p=live.profile,balance=Number(p.balance||0),node=$('balance');
    if(lastBalance===null){if(node)node.textContent=fmt(balance);}else if(lastBalance!==balance){animateValue(node,lastBalance,balance);showDelta(balance-lastBalance);}
    lastBalance=balance;if($('roleName'))$('roleName').textContent=p.role||'Определяем роль';if($('roleEmoji'))$('roleEmoji').textContent=p.role_emoji||'🎭';
    if($('rank'))$('rank').textContent=`Место ${p.rank||0} из ${p.participants_total||0}`;applyCosmetics();
  }
  function drawChart(){
    if(!live?.series)return;activePeriod=currentPeriod();const series=live.series[activePeriod]||live.series['7']||[],svg=$('influenceChart');if(!svg)return;
    if(!series.length){svg.innerHTML='<text x="180" y="88" text-anchor="middle" class="chart-empty">История пока собирается</text>';return;}
    const values=series.map(item=>Number(item.balance||0)),min=Math.min(...values),max=Math.max(...values),range=Math.max(1,max-min),width=360,height=170,padX=12,top=16,bottom=148;
    const points=values.map((value,index)=>[values.length===1?width/2:padX+index*(width-padX*2)/(values.length-1),bottom-(value-min)/range*(bottom-top)]);
    const poly=points.map(([x,y])=>`${x.toFixed(1)},${y.toFixed(1)}`).join(' '),area=`${padX},${height} ${poly} ${width-padX},${height}`;
    svg.innerHTML=`<defs><linearGradient id="liveArea1842" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="rgba(255,210,119,.48)"/><stop offset=".65" stop-color="rgba(157,93,255,.12)"/><stop offset="1" stop-color="rgba(157,93,255,0)"/></linearGradient><filter id="liveGlow1842"><feGaussianBlur stdDeviation="2.8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><polygon points="${area}" fill="url(#liveArea1842)"/><polyline points="${poly}" fill="none" stroke="#ffd277" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" filter="url(#liveGlow1842)"/>${points.map(([x,y],i)=>{const important=Number(series[i]?.delta||0)!==0;return `<circle cx="${x}" cy="${y}" r="${important?4.4:2.1}" fill="${important?'#fff3c9':'#8f64c9'}" stroke="#17101e" stroke-width="1.5"><title>${esc(series[i]?.label||'')}: ${fmt(values[i])}${series[i]?.delta?` (${series[i].delta>0?'+':''}${fmt(series[i].delta)})`:''}</title></circle>`;}).join('')}`;
    const delta=values.at(-1)-values[0],deltaNode=$('chartDelta');if(deltaNode){deltaNode.textContent=`${delta>=0?'+':'−'}${fmt(Math.abs(delta))}`;deltaNode.className=delta>=0?'positive':'negative';}
    const axis=$('chartAxis');if(axis){const picks=[series[0],series[Math.floor((series.length-1)/2)],series.at(-1)];axis.innerHTML=picks.map(item=>`<span>${esc(item?.label||'')}</span>`).join('');}
    const overview=$('overviewDelta'),hint=$('overviewHint');if(overview){overview.textContent=`${delta>=0?'+':'−'}${fmt(Math.abs(delta))} влияния`;overview.className=delta>=0?'':'negative';}
    if(hint){const changed=series.filter(x=>Number(x.delta||0)!==0).length;hint.textContent=changed?`Изменений за период: ${changed} · обновляется автоматически`:'Баланс за период не менялся';}
  }
  function updateMetric(label,value){document.querySelectorAll('.metric-card').forEach(card=>{const name=card.querySelector('span');if(name?.textContent?.trim()===label){const target=card.querySelector('strong');if(target)target.textContent=value;}});}
  function applyStats(){const s=live?.stats||{};updateMetric('Текущее влияние',fmt(s.current_balance));updateMetric('Место в рейтинге',`${s.rank||0}/${s.participants_total||0}`);updateMetric('Заработано за неделю',`+${fmt(s.earned_week)}`);updateMetric('Потеряно за неделю',`−${fmt(s.lost_week)}`);updateMetric('Потрачено в магазине',fmt(s.shop_spent));updateMetric('Вмешательства',fmt(s.interventions));updateMetric('Сообщения',fmt(s.message_count));updateMetric('Максимальный баланс',fmt(s.max_balance));drawChart();}
  function applyHistory(){
    const list=$('historyList');if(!list||!live?.transactions)return;const rows=live.transactions.slice(0,35);
    list.innerHTML=rows.length?rows.map(item=>{const amount=Number(item.amount||0),plus=amount>=0,date=new Date(Number(item.created_at||0)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}),reason=reasonNames[item.reason]||String(item.reason||'Изменение влияния').replaceAll('_',' ');return `<div class="history-row"><i class="${plus?'plus':'minus'}">${plus?'↗':'↘'}</i><div><strong>${esc(reason)}</strong><small>${esc(date)}</small></div><b class="${plus?'positive':'negative'}">${plus?'+':'−'}${fmt(Math.abs(amount))}</b></div>`;}).join(''):'<div class="empty-state"><b>Твоя история ещё не началась</b><br>Выиграй дуэль, выполни задание или вмешайся в событие.</div>';
  }

  function decorateBaseCards(){
    const balance=Number(live?.profile?.balance ?? numberFromText($('balance')?.textContent));
    document.querySelectorAll('.product-card[data-item]').forEach(card=>{
      const key=String(card.dataset.item||''),icon=card.querySelector('.product-top i');if(icon){icon.classList.add('icon-host-1842');icon.innerHTML=iconSvg(key);}
      const price=numberFromText(card.querySelector('.product-meta strong')?.textContent);if(!price)return;updateAffordability(card,balance,price);
    });
  }
  function updateAffordability(card,balance,price){
    const progress=Math.min(100,Math.round(balance/Math.max(1,price)*100)),missing=Math.max(0,price-balance);card.classList.toggle('can-buy',missing===0);card.classList.toggle('locked',missing>0);
    let box=card.querySelector('.affordability');if(!box){box=document.createElement('div');box.className='affordability';card.appendChild(box);}
    box.innerHTML=`<div class="affordability-row"><span>${missing?`Не хватает ${fmt(missing)} ✦`:'Можно приобрести'}</span><b>${progress}%</b></div><div class="affordability-track"><i style="width:${progress}%"></i></div>`;
  }
  function customCard(item,index,balance){
    const missing=Math.max(0,Number(item.price)-balance),progress=Math.min(100,Math.round(balance/Math.max(1,Number(item.price))*100));
    return `<button class="product-card glass rarity-${esc(item.rarity)} ${missing?'locked':'can-buy'} v1842-custom" data-v1842-item="${esc(item.item_key)}" data-category-v1842="${esc(item.category)}" style="--delay:${index*35}ms"><div class="product-top"><i class="icon-host-1842">${iconSvg(item.item_key)}</i><em>${esc(rarityNames[item.rarity]||item.rarity)}</em></div><h3>${esc(item.title)}</h3><p>${esc(item.description)}</p><div class="affordability"><div class="affordability-row"><span>${missing?`Не хватает ${fmt(missing)} ✦`:'Можно приобрести'}</span><b>${progress}%</b></div><div class="affordability-track"><i style="width:${progress}%"></i></div></div><div class="product-meta"><small>Экипируется сразу</small><strong>${fmt(item.price)} <b>✦</b></strong></div></button>`;
  }
  function activeCategory(){return document.querySelector('#categoryTabs [data-category].active')?.dataset.category||'all';}
  function renderCustomCatalog(){
    const grid=$('productGrid');if(!grid||!live?.catalog_v1842)return;grid.querySelectorAll('.v1842-custom').forEach(node=>node.remove());
    const category=activeCategory(),balance=Number(live.profile?.balance||0),items=live.catalog_v1842.filter(item=>category==='all'||item.category===category);
    grid.insertAdjacentHTML('beforeend',items.map((item,i)=>customCard(item,i,balance)).join(''));grid.querySelectorAll('[data-v1842-item]').forEach(card=>{card.onclick=event=>{event.preventDefault();event.stopPropagation();openCustomPurchase(card.dataset.v1842Item);};});
  }
  function renderFeatured(){
    const slot=$('featuredProduct');if(!slot)return;const all=[...(live?.catalog_v1842||[])],legend=all.find(item=>item.rarity==='legendary')||all.at(-1);if(!legend)return;
    const balance=Number(live.profile?.balance||0),missing=Math.max(0,Number(legend.price)-balance);
    slot.innerHTML=`<button class="featured-product featured-1842" type="button"><div class="featured-art">${iconSvg(legend.item_key,'featured-icon')}</div><div class="featured-copy"><small>ПРЕДМЕТ НЕДЕЛИ · ЛЕГЕНДАРНЫЙ</small><h3>${esc(legend.title)}</h3><p>${esc(legend.description)}</p></div><div class="featured-footer"><span>${missing?`До покупки не хватает ${fmt(missing)} ✦`:'Предмет доступен для покупки'}</span><strong>${fmt(legend.price)} ✦</strong></div></button>`;
    slot.querySelector('button').onclick=()=>openCustomPurchase(legend.item_key);
  }
  function refreshCatalog(){decorateBaseCards();renderCustomCatalog();renderFeatured();}

  function restoreBaseModal(){customSelected=null;const confirm=$('confirmPurchase');if(confirm&&baseConfirmHandler)confirm.onclick=baseConfirmHandler;}
  function closeCustomModal(){restoreBaseModal();$('modalClose')?.click();}
  function openCustomPurchase(key){
    const item=(live?.catalog_v1842||[]).find(value=>value.item_key===key);if(!item)return;customSelected=item;
    const balance=Number(live.profile?.balance||0);if($('modalIcon')){$('modalIcon').classList.add('modal-icon-v1842');$('modalIcon').innerHTML=iconSvg(item.item_key,'modal-svg');}
    if($('modalRarity'))$('modalRarity').textContent=`${rarityNames[item.rarity]||item.rarity} ПРЕДМЕТ`;if($('modalTitle'))$('modalTitle').textContent=item.title;if($('modalDescription'))$('modalDescription').textContent=item.description;
    if($('payloadFields'))$('payloadFields').innerHTML='<div class="equip-note">После покупки предмет автоматически станет активным. Предыдущий предмет этого типа останется в истории, но будет заменён в профиле.</div>';
    if($('modalBalance'))$('modalBalance').textContent=fmt(balance);if($('modalPrice'))$('modalPrice').textContent=fmt(item.price);if($('modalAfter'))$('modalAfter').textContent=fmt(Math.max(0,balance-item.price));if($('confirmPrice'))$('confirmPrice').textContent=`${fmt(item.price)} ✦`;
    const confirm=$('confirmPurchase');if(confirm){confirm.disabled=balance<item.price;confirm.onclick=buyCustom;}
    $('purchaseModal')?.classList.add('open');$('purchaseModal')?.setAttribute('aria-hidden','false');tg?.HapticFeedback?.impactOccurred?.('light');
  }
  async function buyCustom(){
    if(!customSelected||customPurchaseBusy)return;customPurchaseBusy=true;const item=customSelected,confirm=$('confirmPurchase');if(confirm){confirm.disabled=true;confirm.classList.add('working');}
    try{
      const response=await fetch('/influence-shop-v184/api/buy',{method:'POST',headers,body:JSON.stringify({chat_id:Number(live.chat_id),item_key:item.item_key,request_id:requestId(),payload:{}})});
      const data=await response.json().catch(()=>null);if(!response.ok||!data?.ok)throw new Error(data?.reason||'Покупка не выполнена');
      closeCustomModal();notify(data.message||'Предмет куплен и экипирован.','success');tg?.HapticFeedback?.notificationOccurred?.('success');await fetchLive({force:true,reason:'purchase'});
    }catch(error){notify(error.message||'Покупка не выполнена','error');tg?.HapticFeedback?.notificationOccurred?.('error');}
    finally{customPurchaseBusy=false;if(confirm){confirm.classList.remove('working');confirm.disabled=false;}}
  }

  function schedulePoll(delay=8000){clearTimeout(pollTimer);pollTimer=setTimeout(()=>fetchLive({reason:'poll'}),delay);}
  async function fetchLive({force=false,reason='manual'}={}){
    if(document.hidden&&!force){schedulePoll(5000);return;}if(requestActive)return;requestActive=true;
    if(requestController)requestController.abort();requestController=new AbortController();const timeout=setTimeout(()=>requestController.abort(),8000);
    syncStatus(firstRequestFinished?'Обновляем данные…':'Подключаем живую статистику…','loading');
    try{
      const query=new URLSearchParams({start_param:startParam,chat_id:chatId});
      const response=await fetch(`/influence-shop-v184/api/live-v1842?${query}`,{headers:{'X-Telegram-Init-Data':tg?.initData||''},cache:'no-store',signal:requestController.signal});
      const data=await response.json().catch(()=>null);if(!response.ok||!data?.ok)throw new Error(data?.reason||`Ошибка ${response.status}`);
      live=data;applyProfile();applyStats();applyHistory();refreshCatalog();
      const stamp=new Date(Number(data.updated_at)*1000).toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit',second:'2-digit'});syncStatus(`В сети · обновлено ${stamp}`,'online');
    }catch(error){
      const message=error?.name==='AbortError'?'Сервер не ответил за 8 секунд':'Статистика временно недоступна';syncStatus(`${message} · повторим автоматически`,'error');console.warn('Reality 184.2 live update:',reason,error);
    }finally{clearTimeout(timeout);requestActive=false;firstRequestFinished=true;schedulePoll();}
  }
  function bind(){
    const confirm=$('confirmPurchase');if(confirm)baseConfirmHandler=confirm.onclick;
    document.addEventListener('click',event=>{
      const period=event.target.closest('#periodTabs [data-days]');if(period){activePeriod=String(period.dataset.days||'7');setTimeout(drawChart,0);}
      const category=event.target.closest('#categoryTabs [data-category]');if(category)setTimeout(()=>{renderCustomCatalog();decorateBaseCards();},20);
      const baseCard=event.target.closest('.product-card[data-item]');if(baseCard&&!baseCard.matches('[data-v1842-item]'))restoreBaseModal();
      if(event.target.closest('#modalClose'))setTimeout(restoreBaseModal,0);
    },true);
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)fetchLive({force:true,reason:'visibility'});});window.addEventListener('focus',()=>fetchLive({force:true,reason:'focus'}));
  }
  function boot(){
    bind();let attempts=0;const wait=()=>{attempts+=1;if(document.body.classList.contains('ready')||$('productGrid')?.children.length||attempts>20){fetchLive({force:true,reason:'boot'});}else{setTimeout(wait,250);}};wait();
    setTimeout(()=>{if(!firstRequestFinished)syncStatus('Статистика загружается дольше обычного…','error');},6000);
  }
  boot();
})();
