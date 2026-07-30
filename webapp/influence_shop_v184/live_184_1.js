(() => {
  'use strict';

  const tg = window.Telegram?.WebApp;
  const $ = id => document.getElementById(id);
  const fmt = value => new Intl.NumberFormat('ru-RU').format(Number(value) || 0);
  const params = new URLSearchParams(location.search);
  const startParam = String(tg?.initDataUnsafe?.start_param || params.get('tgWebAppStartParam') || params.get('startapp') || '');
  const chatId = params.get('chat_id') || '';
  const headers = {'X-Telegram-Init-Data': tg?.initData || ''};
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

  let live = null;
  let lastBalance = null;
  let activePeriod = '7';
  let pollingTimer = null;
  let requestActive = false;

  function esc(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function currentPeriod(){const active=document.querySelector('#periodTabs button.active');return String(active?.dataset.days||activePeriod||'7');}
  function syncStatus(text, kind='online'){
    const node=$('liveSync'); if(!node)return;
    node.className=`sync-status ${kind}`; const span=node.querySelector('span'); if(span)span.textContent=text;
  }
  function animateValue(node, from, to){
    if(!node)return; const start=performance.now(), diff=Number(to)-Number(from);
    function frame(now){const t=Math.min(1,(now-start)/520),e=1-Math.pow(1-t,3);node.textContent=fmt(Math.round(Number(from)+diff*e));if(t<1)requestAnimationFrame(frame);}
    requestAnimationFrame(frame);
  }
  function showDelta(delta){
    const node=$('liveDelta');if(!node||!delta)return;
    node.textContent=`${delta>0?'+':'−'}${fmt(Math.abs(delta))} влияния`;
    node.className=`live-delta ${delta<0?'loss':''}`;
    void node.offsetWidth; node.classList.add('show');
    tg?.HapticFeedback?.notificationOccurred?.(delta>0?'success':'warning');
  }
  function applyProfile(){
    if(!live?.profile)return;
    const profile=live.profile, balance=Number(profile.balance||0), node=$('balance');
    if(lastBalance===null){node.textContent=fmt(balance);}else if(lastBalance!==balance){animateValue(node,lastBalance,balance);showDelta(balance-lastBalance);}
    lastBalance=balance;
    $('roleName').textContent=profile.role||'Участник';$('roleEmoji').textContent=profile.role_emoji||'🎭';
    $('rank').textContent=`Место ${profile.rank||0} из ${profile.participants_total||0}`;
  }
  function drawChart(){
    if(!live?.series)return;
    activePeriod=currentPeriod();
    const series=live.series[activePeriod]||live.series['7']||[];
    const svg=$('influenceChart'); if(!svg||!series.length)return;
    const values=series.map(item=>Number(item.balance||0));
    const min=Math.min(...values),max=Math.max(...values),range=Math.max(1,max-min);
    const width=360,height=170,padX=10,top=16,bottom=148;
    const points=values.map((value,index)=>{
      const x=values.length===1?width/2:padX+index*(width-padX*2)/(values.length-1);
      const y=bottom-(value-min)/range*(bottom-top);
      return [x,y];
    });
    const poly=points.map(([x,y])=>`${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
    const zeroLine=range===1&&max===min;
    svg.innerHTML=`<defs><linearGradient id="liveArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="rgba(242,198,109,.45)"/><stop offset=".7" stop-color="rgba(169,104,255,.10)"/><stop offset="1" stop-color="rgba(169,104,255,0)"/></linearGradient><filter id="liveGlow"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><polygon points="${padX},${height} ${poly} ${width-padX},${height}" fill="url(#liveArea)"/><polyline points="${poly}" fill="none" stroke="#f2c66d" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" filter="url(#liveGlow)"/>${points.map(([x,y],i)=>{const important=Number(series[i]?.delta||0)!==0;return `<circle cx="${x}" cy="${y}" r="${important?4:2.2}" fill="${important?'#fff1bf':'#9d6bd7'}" stroke="#17101e" stroke-width="1.5"><title>${esc(series[i]?.label||'')}: ${fmt(values[i])}${series[i]?.delta?` (${series[i].delta>0?'+':''}${fmt(series[i].delta)})`:''}</title></circle>`}).join('')}`;
    const delta=values.at(-1)-values[0],deltaNode=$('chartDelta');
    deltaNode.textContent=`${delta>=0?'+':'−'}${fmt(Math.abs(delta))}`;deltaNode.className=delta>=0?'positive':'negative';
    const axis=$('chartAxis');if(axis){const picks=[series[0],series[Math.floor((series.length-1)/2)],series.at(-1)];axis.innerHTML=picks.map(item=>`<span>${esc(item?.label||'')}</span>`).join('');}
    const overview=$('overviewDelta'),hint=$('overviewHint');
    if(overview){overview.textContent=`${delta>=0?'+':'−'}${fmt(Math.abs(delta))} влияния`;overview.className=delta>=0?'':'negative';}
    if(hint){const changed=series.filter(x=>Number(x.delta||0)!==0).length;hint.textContent=changed?`Изменений за период: ${changed} · данные обновляются автоматически`:'Пока без изменений — текущий баланс уже зафиксирован на графике';}
  }
  function updateMetric(label,value){
    document.querySelectorAll('.metric-card').forEach(card=>{const name=card.querySelector('span');if(name?.textContent?.trim()===label){const target=card.querySelector('strong');if(target)target.textContent=value;}});
  }
  function applyStats(){
    const s=live?.stats||{};
    updateMetric('Текущее влияние',fmt(s.current_balance));
    updateMetric('Место в рейтинге',`${s.rank||0}/${s.participants_total||0}`);
    updateMetric('Заработано за неделю',`+${fmt(s.earned_week)}`);
    updateMetric('Потеряно за неделю',`−${fmt(s.lost_week)}`);
    updateMetric('Потрачено в магазине',fmt(s.shop_spent));
    updateMetric('Вмешательства',fmt(s.interventions));
    updateMetric('Сообщения',fmt(s.message_count));
    updateMetric('Максимальный баланс',fmt(s.max_balance));
    drawChart();
  }
  function applyHistory(){
    const list=$('historyList');if(!list||!live?.transactions)return;
    const rows=live.transactions.slice(0,35);
    list.innerHTML=rows.length?rows.map(item=>{const amount=Number(item.amount||0),plus=amount>=0,date=new Date(Number(item.created_at||0)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}),reason=reasonNames[item.reason]||String(item.reason||'Изменение влияния').replaceAll('_',' ');return `<div class="history-row"><i class="${plus?'plus':'minus'}">${plus?'↗':'↘'}</i><div><strong>${esc(reason)}</strong><small>${esc(date)}</small></div><b class="${plus?'positive':'negative'}">${plus?'+':'−'}${fmt(Math.abs(amount))}</b></div>`}).join(''):'<div class="empty-state"><b>Твоя история ещё не началась</b><br>Выиграй дуэль, выполни задание или вмешайся в событие.</div>';
  }
  function numberFromText(text){return Number(String(text||'').replace(/[^0-9]/g,''))||0;}
  function decorateProducts(){
    const balance=Number(live?.profile?.balance ?? numberFromText($('balance')?.textContent));
    const cards=[...document.querySelectorAll('.product-card')];
    cards.forEach(card=>{
      const icon=card.querySelector('.product-top i');if(icon&&!icon.dataset.icon){icon.dataset.icon=icon.textContent.trim();}
      const price=numberFromText(card.querySelector('.product-meta strong')?.textContent);if(!price)return;
      const progress=Math.min(100,Math.round(balance/price*100)),missing=Math.max(0,price-balance);
      card.classList.toggle('can-buy',missing===0);
      let box=card.querySelector('.affordability');if(!box){box=document.createElement('div');box.className='affordability';card.appendChild(box);}
      box.innerHTML=`<div class="affordability-row"><span>${missing?`Не хватает ${fmt(missing)} ✦`:'Можно приобрести'}</span><b>${progress}%</b></div><div class="affordability-track"><i style="width:${progress}%"></i></div>`;
    });
    renderFeatured(cards,balance);
  }
  function renderFeatured(cards,balance){
    const slot=$('featuredProduct');if(!slot||slot.dataset.ready==='1'||!cards.length)return;
    const chosen=cards.find(card=>card.classList.contains('rarity-legendary'))||cards.at(-1);
    if(!chosen)return;
    const title=chosen.querySelector('h3')?.textContent?.trim()||'Предмет недели',description=chosen.querySelector('p')?.textContent?.trim()||'',price=numberFromText(chosen.querySelector('.product-meta strong')?.textContent),icon=chosen.querySelector('.product-top i')?.dataset.icon||chosen.querySelector('.product-top i')?.textContent||'✦',missing=Math.max(0,price-balance);
    slot.innerHTML=`<button class="featured-product" type="button"><div class="featured-art">${esc(icon)}</div><div class="featured-copy"><small>ПРЕДМЕТ НЕДЕЛИ · ЛЕГЕНДАРНЫЙ</small><h3>${esc(title)}</h3><p>${esc(description)}</p></div><div class="featured-footer"><span>${missing?`До покупки не хватает ${fmt(missing)} ✦`:'Предмет доступен для покупки'}</span><strong>${fmt(price)} ✦</strong></div></button>`;
    slot.querySelector('button').onclick=()=>chosen.click();slot.dataset.ready='1';
  }
  async function fetchLive(){
    if(requestActive||document.hidden)return;requestActive=true;syncStatus('Обновляем влияние…','');
    try{
      const query=new URLSearchParams({start_param:startParam,chat_id:chatId});
      const response=await fetch(`/influence-shop-v184/api/live-v1841?${query}`,{headers,cache:'no-store'});
      const data=await response.json().catch(()=>null);
      if(!response.ok||!data?.ok)throw new Error(data?.reason||'Не удалось обновить статистику');
      live=data;applyProfile();applyStats();applyHistory();decorateProducts();
      const stamp=new Date(Number(data.updated_at)*1000).toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
      syncStatus(`Живая статистика · обновлено ${stamp}`,'online');
    }catch(error){syncStatus('Связь потеряна — повторяем автоматически','error');console.warn('Reality 184.1 live update:',error);}
    finally{requestActive=false;schedulePoll();}
  }
  function schedulePoll(delay=4500){clearTimeout(pollingTimer);pollingTimer=setTimeout(fetchLive,delay);}
  function bindLive(){
    document.addEventListener('click',event=>{const button=event.target.closest('#periodTabs [data-days]');if(!button)return;activePeriod=String(button.dataset.days||'7');setTimeout(drawChart,0);});
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)fetchLive();});
    window.addEventListener('focus',()=>fetchLive());
  }
  function boot(){bindLive();const wait=()=>{if(document.body.classList.contains('ready')||$('productGrid')?.children.length){fetchLive();}else{setTimeout(wait,250);}};wait();}
  boot();
})();
