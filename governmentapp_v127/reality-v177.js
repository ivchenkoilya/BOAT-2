(()=>{
  'use strict';
  if(window.__governmentRealityV177)return;
  window.__governmentRealityV177=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
  const duration=value=>{
    let seconds=Math.max(0,Number(value)||0);
    if(!seconds)return 'сразу';
    const days=Math.floor(seconds/86400);seconds%=86400;
    const hours=Math.floor(seconds/3600);const minutes=Math.floor((seconds%3600)/60);
    if(days)return `${days} д. ${hours} ч.`;
    if(hours)return `${hours} ч. ${minutes} мин.`;
    return `${Math.max(1,minutes)} мин.`;
  };
  const requestId=()=>crypto?.randomUUID?.()||`r177-${Date.now()}-${Math.random().toString(36).slice(2)}`;

  let state=null;
  let loading=false;
  let busy=false;
  let propertyTab='mine';
  let renderTimers=[];

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=String(text||'Готово.');
    node.className=`toast show ${type}`;
    clearTimeout(node.__r177Toast);
    node.__r177Toast=setTimeout(()=>node.className='toast',4200);
  }

  function scheduleRender(){
    renderTimers.forEach(clearTimeout);renderTimers=[];
    [0,100,300].forEach(delay=>renderTimers.push(setTimeout(render,delay)));
  }

  async function api(payload,button=null){
    if(busy)return null;
    busy=true;
    const oldText=button?.textContent||'';
    if(button){button.disabled=true;button.textContent='⌛ ВЫПОЛНЯЕМ…'}
    try{
      const response=await fetch('/government-v177/api/extended-action',{
        method:'POST',cache:'no-store',headers,
        body:JSON.stringify({chat_id:chatId,...payload}),
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      toast(data.message||'Готово.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      closeModal();
      await load(true);
      window.__governmentTreasuryState=null;
      window.__governmentTreasuryStateAt=0;
      return data;
    }catch(error){
      toast(error.message||'Действие не выполнено.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
      return null;
    }finally{
      busy=false;
      if(button&&button.isConnected){button.disabled=false;button.textContent=oldText}
    }
  }

  async function load(force=false){
    if(!chatId||loading)return;
    loading=true;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_r177=${Date.now()}`,{
        cache:'no-store',headers:{'X-Telegram-Init-Data':tg?.initData||''},
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось загрузить Reality 177.');
      state=data;
      scheduleRender();
    }catch(error){toast(error.message||'Не удалось загрузить Reality 177.','error')}
    finally{loading=false}
  }

  function ensureLayout(){
    document.getElementById('r176Programs')?.setAttribute('hidden','');
    document.getElementById('r176PropertyQuick')?.setAttribute('hidden','');
    const stack=document.querySelector('.screen-stack');
    const nav=document.getElementById('bottomNav');
    if(stack&&!document.querySelector('.screen[data-screen="ratings177"]')){
      stack.insertAdjacentHTML('beforeend',`
        <section class="screen r177-screen" data-screen="ratings177">
          <div class="section-head"><div><small>ОБЩЕСТВЕННАЯ ОЦЕНКА ВЛАСТИ</small><h2>Рейтинг государственных служащих</h2></div></div>
          <div id="r177Ratings"></div>
        </section>
        <section class="screen r177-screen" data-screen="property177">
          <div class="section-head"><div><small>ЛИЧНЫЕ АКТИВЫ И ДЕКЛАРАЦИИ</small><h2>Имущество</h2></div></div>
          <div id="r177Property"></div>
        </section>`);
    }
    if(nav&&!nav.querySelector('[data-tab="ratings177"]')){
      const treasury=nav.querySelector('[data-tab="treasury"]');
      const rating=document.createElement('button');
      rating.type='button';rating.dataset.tab='ratings177';rating.innerHTML='<span>📊</span><small>Рейтинг</small>';
      const property=document.createElement('button');
      property.type='button';property.dataset.tab='property177';property.innerHTML='<span>🏘</span><small>Имущество</small>';
      nav.insertBefore(rating,treasury||null);nav.insertBefore(property,treasury||null);
    }
    const treasuryScreen=document.querySelector('.screen[data-screen="treasury"]');
    if(treasuryScreen&&!document.getElementById('r177Programs')){
      const mount=document.createElement('section');mount.id='r177Programs';mount.className='r177-section';
      const anchor=document.getElementById('treasuryManagementV164')||document.getElementById('taxPolicy')||document.getElementById('treasuryHero');
      anchor?.insertAdjacentElement('afterend',mount);
    }
    if(!document.getElementById('r177Modal')){
      document.body.insertAdjacentHTML('beforeend',`
        <div class="r177-modal" id="r177Modal" aria-hidden="true">
          <section class="r177-sheet">
            <header><div><small id="r177ModalKicker">REALITY 177</small><h3 id="r177ModalTitle">Действие</h3></div><button type="button" data-r177-close>×</button></header>
            <div class="r177-modal-body" id="r177ModalBody"></div>
          </section>
        </div>`);
    }
  }

  function openModal(title,kicker,content){
    ensureLayout();
    document.getElementById('r177ModalTitle').textContent=String(title||'Действие');
    document.getElementById('r177ModalKicker').textContent=String(kicker||'REALITY 177');
    document.getElementById('r177ModalBody').innerHTML=content;
    const modal=document.getElementById('r177Modal');
    modal.classList.add('open');modal.setAttribute('aria-hidden','false');
    document.body.classList.add('r177-modal-open');
  }
  function closeModal(){
    const modal=document.getElementById('r177Modal');
    modal?.classList.remove('open');modal?.setAttribute('aria-hidden','true');
    document.body.classList.remove('r177-modal-open');
  }

  function userOptions(selected=0){
    return (state?.eligible_users||[]).map(user=>`<option value="${Number(user.user_id)}" ${Number(selected)===Number(user.user_id)?'selected':''}>${esc(user.name)} · 💰 ${fmt(user.points)} · ⭐ ${fmt(user.career_points)}</option>`).join('');
  }

  function programForm(program){
    let fields='';
    if(program.manual_amount){
      fields+=`<div class="field"><label>СУММА ИЗ ФОНДА</label><input name="amount" type="number" min="${Number(program.min_cost)}" max="${Math.max(Number(program.min_cost),Math.min(Number(program.max_cost),Number(program.fund_balance)))}" value="${Number(program.calculated_cost)}"><small class="hint">Доступно: ${fmt(program.fund_balance)}</small></div>`;
    }
    if(program.key==='social_help')fields+='<div class="field"><label>ПОЛУЧАТЕЛЕЙ</label><select name="recipient_count"><option value="3">3 участника</option><option value="4">4 участника</option><option value="5" selected>5 участников</option></select></div>';
    if(program.requires_symbol)fields+='<div class="field"><label>АКЦИЯ</label><select name="symbol"><option value="EGO">👑 EGO</option><option value="HERO">⚡ HERO</option><option value="NPC">🎭 NPC</option><option value="CORV">🐦‍⬛ CORV</option><option value="CENTER">🌌 CENTER</option></select></div>';
    if(program.requires_target)fields+=`<div class="field"><label>ПОЛУЧАТЕЛЬ СУБСИДИИ</label><select name="target_user_id">${userOptions()}</select></div>`;
    openModal(program.title,`${program.emoji} ГОСУДАРСТВЕННАЯ ПРОГРАММА`,`
      <article class="r177-info"><p>${esc(program.effect)}</p><div><span>Фонд: <b>${esc(program.fund_title)}</b></span><span>Баланс: <b>${fmt(program.fund_balance)}</b></span><span>Цена: <b>${fmt(program.calculated_cost)}</b></span><span>Кулдаун: <b>${duration(program.cooldown)}</b></span></div></article>
      <form id="r177ProgramForm" data-key="${esc(program.key)}">${fields}<button class="action wide" type="submit">${program.emoji} ЗАПУСТИТЬ ПРОГРАММУ</button></form>`);
  }

  function renderPrograms(){
    const mount=document.getElementById('r177Programs');
    const data=state?.reality177?.programs;
    if(!mount||!data)return;
    const cards=(data.programs||[]).map(program=>{
      const blocked=String(program.unavailable_reason||'');
      const label=program.active?'✓ ДЕЙСТВУЕТ':blocked?'НЕДОСТУПНО':'▶ ЗАПУСТИТЬ';
      return `<article class="r177-program ${program.active?'active':''}">
        <div class="r177-title"><span>${esc(program.emoji)}</span><div><b>${esc(program.title)}</b><small>${esc(program.fund_title)} · баланс ${fmt(program.fund_balance)}</small></div></div>
        <p>${esc(program.effect)}</p>
        <div class="r177-meta"><span>Стоимость <b>${fmt(program.calculated_cost)}</b></span><span>${program.duration?`Действует ${duration(program.duration)}`:'Эффект сразу'}</span></div>
        ${blocked?`<div class="r177-reason">${esc(blocked)}</div>`:''}
        <button type="button" class="action wide" data-r177-program="${esc(program.key)}" ${blocked?'disabled':''}>${label}</button>
      </article>`;
    }).join('');
    const structures=(data.structures||[]).map(item=>`<article class="r177-structure">
      <div class="r177-title"><span>${esc(item.emoji)}</span><div><b>${esc(item.title)}</b><small>${Number(item.balance)>0?esc(item.source||'Государственный фонд'):esc(item.empty_hint||'Финансирование не выделено')}</small></div><strong>${fmt(item.balance)}</strong></div>
      <div class="r177-structure-actions"><button type="button" class="secondary" data-r177-fund-history="${esc(item.key)}">📋 История</button><button type="button" class="secondary" data-r177-fund-transfer="${esc(item.key)}">💸 Пополнить</button></div>
    </article>`).join('');
    const effects=(data.active_effects||[]).map(effect=>{
      const program=(data.programs||[]).find(item=>item.key===effect.effect_key);
      return `<div class="r177-log"><span><b>${esc(program?.emoji||'🏛')} ${esc(program?.title||effect.effect_key)}</b><small>до ${date(effect.ends_at)}</small></span><strong>АКТИВНО</strong></div>`;
    }).join('');
    const history=(data.history||[]).slice(0,20).map(item=>{
      const program=(data.programs||[]).find(row=>row.key===item.program_key);
      return `<div class="r177-log"><span><b>${esc(program?.emoji||'🏛')} ${esc(program?.title||item.program_key)}</b><small>${date(item.started_at)} · ${esc(item.status)}</small></span><strong>−${fmt(item.cost)}</strong></div>`;
    }).join('');
    const offices=state?.user?.offices||[];
    const canReport=offices.includes('oversight')||offices.includes('oversight_deputy')||state?.user?.is_admin;
    const oversightActive=(data.active_effects||[]).some(item=>item.effect_key==='oversight_operation');
    mount.innerHTML=`
      <div class="section-head"><div><small>REALITY 177</small><h2>Государственные программы</h2></div></div>
      <div class="r177-program-grid">${cards}</div>
      ${canReport&&oversightActive?'<button class="secondary wide" type="button" data-r177-expanded-report>📊 ОПУБЛИКОВАТЬ РАСШИРЕННЫЙ ОТЧЁТ НАДЗОРА</button>':''}
      ${state?.reality177?.emergency_action?'<button class="danger wide r177-emergency" type="button" data-r177-emergency>🚑 ЭКСТРЕННО ПОПОЛНИТЬ СВОБОДНУЮ КАЗНУ</button>':''}
      <details class="r177-details"><summary>Активные эффекты и история запусков</summary><div class="r177-log-list">${effects||'<div class="empty">Активных эффектов нет.</div>'}${history||'<div class="empty">Запусков пока нет.</div>'}</div></details>
      <div class="section-head"><div><small>ЕДИНЫЙ ИСТОЧНИК ДЕНЕГ</small><h2>Балансы государственных структур</h2></div></div>
      <div class="r177-structures">${structures}</div>`;
  }

  function renderRatings(){
    const mount=document.getElementById('r177Ratings');
    const data=state?.reality177?.ratings;
    if(!mount||!data)return;
    const officials=(data.officials||[]).map((item,index)=>`<article class="r177-rating ${item.office_key==='president'?'president':''}">
      <div class="r177-rating-head"><strong>${index+1}</strong><div><b>${esc(item.name)}</b><small>${esc(item.office_title)}${Number(item.delta_7d)?` · 7 дней: ${Number(item.delta_7d)>0?'+':''}${Number(item.delta_7d)}`:''}</small></div><em>${fmt(item.rating)}</em></div>
      <div class="r177-rating-bar"><i style="width:${Math.max(0,Math.min(100,Number(item.rating)||0))}%"></i></div>
      <div class="r177-meta"><span>👍 ${fmt(item.approvals)}</span><span>👎 ${fmt(item.disapprovals)}</span><span>Срок до ${date(item.ends_at)}</span></div>
      <div class="r177-actions"><button type="button" class="positive" data-r177-rate="1" data-user="${Number(item.user_id)}" ${item.can_rate?'':'disabled'}>👍 Одобрить</button><button type="button" class="danger" data-r177-rate="-1" data-user="${Number(item.user_id)}" ${item.can_rate?'':'disabled'}>👎 Не одобрить</button><button type="button" class="secondary" data-r177-rating-history="${Number(item.user_id)}">📊 История</button></div>
      ${!item.can_rate&&Number(item.user_id)!==Number(state?.user?.user_id)&&item.next_vote_at?`<small class="r177-next">Следующая оценка: ${date(item.next_vote_at)}</small>`:''}
    </article>`).join('');
    const archive=(data.archive||[]).map(item=>`<div class="r177-log"><span><b>${esc(item.name)}</b><small>${esc(item.office_title)} · ${date(item.starts_at)} — ${date(item.ends_at)}</small></span><strong>${fmt(item.final_rating)}</strong></div>`).join('');
    mount.innerHTML=`<div class="r177-rating-list">${officials||'<div class="empty">Действующих чиновников нет.</div>'}</div><details class="r177-details"><summary>Архив завершённых сроков</summary><div class="r177-log-list">${archive||'<div class="empty">Архив пока пуст.</div>'}</div></details>`;
  }

  function statusLabel(status){
    return ({owned:'Активно',seized_debt:'Арестовано за долг',seized_investigation:'Временно арестовано',auction:'На аукционе',state_owned:'Государственная собственность',open:'Открыта',referred:'Передана прокурору',bill_pending:'Решение в Госдуме',resolved:'Завершена',cleared:'Оправдан',warning:'Предупреждение'})[status]||String(status||'—');
  }
  function propertyTabs(){
    const data=state?.reality177?.property||{};
    const tabs=[['mine','💼 Моё'],['store','🏛 Магазин'],['auctions','🔨 Аукционы'],['declarations','📄 Декларации'],['ranking','🏆 Рейтинг'],['operations','📋 История']];
    if(data.can_investigate)tabs.push(['investigations','🔎 Проверки']);
    return `<nav class="r177-tabs">${tabs.map(([key,title])=>`<button type="button" class="${propertyTab===key?'active':''}" data-r177-property-tab="${key}">${title}</button>`).join('')}</nav>`;
  }
  function catalogMap(data){return Object.fromEntries((data.catalog||[]).map(item=>[String(item.key),item]))}

  function mineContent(data){
    const items=data.my_items||[];
    if(!items.length)return '<div class="empty">Имущество пока не приобретено.</div>';
    return items.map(item=>{
      const sellBlocked=item.status!=='owned'||Number(item.debt)>0||Number(data.treasury_balance)<Number(item.sell_price);
      return `<article class="r177-property ${item.is_primary?'primary':''}">
        <div class="r177-title"><span>${esc(item.emoji)}</span><div><b>${esc(item.title)}${item.upgrade_level?` · улучшение ${item.upgrade_level}/3`:''}</b><small>${esc(statusLabel(item.status))}${item.is_primary?' · ⭐ главный актив':''}</small></div><strong>${fmt(item.prestige_value||item.purchase_price)}</strong></div>
        <div class="r177-meta"><span>Содержание <b>${fmt(item.maintenance_amount)}</b></span><span>следующее ${date(item.next_maintenance_at)}</span><span>${item.insurance_until>Date.now()/1000&&!item.insurance_used?`🛡 страховка до ${date(item.insurance_until)}`:'без страховки'}</span></div>
        ${item.debt?`<div class="r177-reason">Долг по содержанию: ${fmt(item.debt)}</div>`:''}
        <div class="r177-actions">
          ${item.debt?`<button type="button" class="positive" data-r177-debt="${esc(item.property_id)}">🧾 Оплатить долг</button>`:''}
          <button type="button" class="secondary" data-r177-primary="${esc(item.property_id)}" ${item.status==='owned'?'':'disabled'}>⭐ Главный актив</button>
          <button type="button" class="secondary" data-r177-upgrade="${esc(item.property_id)}" ${item.status==='owned'&&Number(item.debt)===0&&Number(item.upgrade_level)<3?'':'disabled'}>🛠 Улучшить · ${fmt(item.upgrade_cost)}</button>
          <button type="button" class="secondary" data-r177-insure="${esc(item.property_id)}" ${item.status==='owned'?'':'disabled'}>🛡 Страховка · ${fmt(item.insurance_cost)}</button>
          <button type="button" class="action" data-r177-auction-start="${esc(item.property_id)}" ${item.status==='owned'&&Number(item.debt)===0?'':'disabled'}>🔨 На аукцион</button>
          <button type="button" class="positive" data-r177-sell="${esc(item.property_id)}" data-price="${Number(item.sell_price)}" ${sellBlocked?'disabled':''}>💰 ПРОДАТЬ ИМУЩЕСТВО · ${fmt(item.sell_price)}</button>
        </div>
        ${Number(data.treasury_balance)<Number(item.sell_price)?`<small class="r177-next">Казне не хватает ${fmt(Number(item.sell_price)-Number(data.treasury_balance))} для выкупа.</small>`:''}
      </article>`;
    }).join('');
  }

  function storeContent(data){
    if(!data.is_official)return '<div class="empty">Новое имущество могут покупать только действующие государственные служащие.</div>';
    return `<div class="r177-shop">${(data.catalog||[]).map(item=>`<article class="r177-property ${item.owned?'owned':''}"><div class="r177-title"><span>${esc(item.emoji)}</span><div><b>${esc(item.title)}</b><small>Цена ${fmt(item.price)} · налог ${fmt(item.luxury_tax)}</small></div></div><div class="r177-meta"><span>Всего <b>${fmt(item.total_cost)}</b></span><span>Содержание ${(Number(item.maintenance_bp)/100).toLocaleString('ru-RU')}% / 7 дней</span></div><button type="button" class="action wide" data-r177-buy="${esc(item.key)}" ${item.allowed&&!item.owned?'':'disabled'}>${item.owned?'✓ УЖЕ ЕСТЬ':item.allowed?'КУПИТЬ':'НЕДОСТУПНО ДЛЯ ДОЛЖНОСТИ'}</button></article>`).join('')}</div>`;
  }

  function auctionCard(item,type,data){
    const catalog=catalogMap(data);const spec=catalog[String(item.item_key)]||{};
    const title=item.title||spec.title||item.item_key;const emoji=item.emoji||spec.emoji||'🏛';
    const seller=item.seller_name||item.former_owner_name||'Государство';
    return `<article class="r177-property"><div class="r177-title"><span>${esc(emoji)}</span><div><b>${esc(title)}</b><small>${type==='voluntary'?'Продавец':'Бывший владелец'}: ${esc(seller)} · до ${date(item.ends_at)}</small></div></div><div class="r177-meta"><span>Текущая цена <b>${fmt(item.current_price||item.start_price)}</b></span><span>Минимум <b>${fmt(item.minimum_bid)}</b></span></div>${item.bidder_name||item.current_bidder_name?`<p>Лидирует: <b>${esc(item.bidder_name||item.current_bidder_name)}</b></p>`:''}<form class="r177BidForm" data-auction="${esc(item.auction_id)}" data-type="${type}"><div class="field"><label>ВАША СТАВКА</label><input name="amount" type="number" min="${Number(item.minimum_bid)}" value="${Number(item.minimum_bid)}"></div><button class="action wide" type="submit" ${item.can_bid?'':'disabled'}>${item.can_bid?'СДЕЛАТЬ СТАВКУ':'СТАВКА НЕДОСТУПНА'}</button></form></article>`;
  }
  function auctionsContent(data){
    const voluntary=(data.voluntary_auctions||[]).map(item=>auctionCard(item,'voluntary',data)).join('');
    const stateAuctions=(data.auctions||[]).map(item=>auctionCard(item,'state',data)).join('');
    return `<div class="r177-subhead">Добровольные аукционы</div>${voluntary||'<div class="empty">Добровольных аукционов нет.</div>'}<div class="r177-subhead">Государственные аукционы</div>${stateAuctions||'<div class="empty">Конфискованного имущества на торгах нет.</div>'}`;
  }
  function declarationsContent(data){
    const refresh='<button type="button" class="secondary wide" data-r177-declaration-refresh>📄 ОБНОВИТЬ МОЮ ДЕКЛАРАЦИЮ</button>';
    return refresh+((data.declarations||[]).map(person=>`<details class="r177-details"><summary><span><b>${esc(person.name)}</b><small>${(person.offices||[]).map(key=>esc(state?.office_specs?.[key]?.title||key)).join(' · ')}</small></span><strong>${fmt(person.total_value)}</strong></summary><div class="r177-metrics"><div><small>БАЛАНС</small><b>${fmt(person.balance)}</b></div><div><small>ОБЪЕКТОВ</small><b>${(person.items||[]).length}</b></div><div><small>НАЛОГИ</small><b>${fmt(person.luxury_tax_paid)}</b></div><div><small>СОДЕРЖАНИЕ</small><b>${fmt(person.maintenance_paid)}</b></div></div>${person.primary_asset?`<div class="r177-reason">⭐ Главный актив: ${esc(person.primary_asset.emoji)} ${esc(person.primary_asset.title)}</div>`:''}<div class="r177-log-list">${(person.items||[]).map(item=>`<div class="r177-log"><span><b>${esc(item.emoji)} ${esc(item.title)}${item.upgrade_level?` · ур. ${item.upgrade_level}`:''}</b><small>${esc(statusLabel(item.status))}</small></span><strong>${fmt(item.prestige_value||item.value)}</strong></div>`).join('')||'<div class="empty">Имущества нет.</div>'}</div></details>`).join('')||'<div class="empty">Деклараций нет.</div>');
  }
  function rankingContent(data){
    return (data.ranking||[]).map((person,index)=>`<div class="r177-rank"><strong>${index+1}</strong><span><b>${esc(person.name)}</b><small>${person.count} объектов${person.primary_asset?` · ⭐ ${esc(person.primary_asset.emoji)} ${esc(person.primary_asset.title)}`:''}</small></span><b>${fmt(person.total_value)}</b></div>`).join('')||'<div class="empty">Рейтинг имущества пока пуст.</div>';
  }
  function operationsContent(data){
    return `<div class="r177-log-list">${(data.operations||[]).map(item=>`<div class="r177-log"><span><b>${esc(item.detail)}</b><small>${date(item.created_at)} · ${esc(item.operation_type)}</small></span><strong>${Number(item.amount)?fmt(item.amount):'—'}</strong></div>`).join('')||'<div class="empty">Операций с имуществом пока нет.</div>'}</div>`;
  }
  function investigationsContent(data){
    const props=(data.declarations||[]).flatMap(person=>(person.items||[]).map(item=>`<option value="${esc(item.property_id)}">${esc(person.name)} · ${esc(item.emoji)} ${esc(item.title)}</option>`)).join('');
    const rows=(data.investigations||[]).map(item=>`<article class="r177-property"><div class="r177-title"><span>🔎</span><div><b>${esc(item.target_name)}</b><small>${esc(statusLabel(item.status))} · ${date(item.created_at)}</small></div></div><p>${esc(item.reason)}</p>${item.result?`<div class="r177-reason">${esc(item.result)}</div>`:''}${['open','referred'].includes(item.status)?`<div class="r177-actions"><button class="secondary" data-r177-invest="clear" data-id="${esc(item.investigation_id)}">Оправдать</button><button class="secondary" data-r177-invest="warning" data-id="${esc(item.investigation_id)}">Предупредить</button><button class="secondary" data-r177-invest="refer" data-id="${esc(item.investigation_id)}">Прокурору</button><button class="danger" data-r177-invest="seize" data-id="${esc(item.investigation_id)}" ${item.property_id?'':'disabled'}>Арест</button><button class="danger" data-r177-invest="confiscate" data-id="${esc(item.investigation_id)}" ${item.property_id?'':'disabled'}>Конфискация</button></div>`:''}</article>`).join('');
    return `<details class="r177-details"><summary>Открыть имущественную проверку</summary><form id="r177InvestigationForm"><div class="field"><label>ПРОВЕРЯЕМЫЙ</label><select name="target_user_id">${userOptions()}</select></div><div class="field"><label>ОБЪЕКТ</label><select name="property_id"><option value="">Без конкретного объекта</option>${props}</select></div><div class="field"><label>ОСНОВАНИЕ</label><textarea name="reason" minlength="10" maxlength="800"></textarea></div><button class="action wide" type="submit">🔎 ОТКРЫТЬ ПРОВЕРКУ</button></form></details>${rows||'<div class="empty">Проверок пока нет.</div>'}`;
  }

  function renderProperty(){
    const mount=document.getElementById('r177Property');
    const data=state?.reality177?.property;
    if(!mount||!data)return;
    let content='';
    if(propertyTab==='mine')content=mineContent(data);
    else if(propertyTab==='store')content=storeContent(data);
    else if(propertyTab==='auctions')content=auctionsContent(data);
    else if(propertyTab==='declarations')content=declarationsContent(data);
    else if(propertyTab==='ranking')content=rankingContent(data);
    else if(propertyTab==='operations')content=operationsContent(data);
    else if(propertyTab==='investigations')content=investigationsContent(data);
    mount.innerHTML=`<article class="r177-property-hero"><div><small>ЛИЧНЫЙ БАЛАНС</small><b>${fmt(state?.user?.points)}</b></div><div><small>СВОБОДНАЯ КАЗНА</small><b>${fmt(data.treasury_balance)}</b></div><div><small>МОИ ОБЪЕКТЫ</small><b>${(data.my_items||[]).length}</b></div></article>${propertyTabs()}<div class="r177-property-content">${content}</div>`;
  }

  function render(){
    if(!state)return;
    ensureLayout();
    renderPrograms();renderRatings();renderProperty();
  }

  function showFundHistory(key){
    const item=state?.reality177?.programs?.structures?.find(row=>String(row.key)===String(key));
    if(!item)return;
    const entry=(title,value)=>value?`<div class="r177-log"><span><b>${title}</b><small>${esc(value.detail||'Операция фонда')} · ${date(value.created_at)}</small></span><strong>${fmt(value.amount)}</strong></div>`:`<div class="empty">${title}: операций пока нет.</div>`;
    openModal(item.title,'🏦 ИСТОРИЯ ФОНДА',`<article class="r177-info"><div><span>Текущий баланс <b>${fmt(item.balance)}</b></span><span>${esc(item.source||'Единый государственный баланс')}</span></div></article><div class="r177-log-list">${entry('Последнее пополнение',item.last_income)}${entry('Последний расход',item.last_expense)}</div>`);
  }
  function prepareFundTransfer(key){
    const form=document.getElementById('treasuryManagementFormV164');
    if(!form){toast('Форма управления казной сейчас недоступна.','error');return}
    form.elements.target_type.value='structure';
    form.dispatchEvent(new Event('change',{bubbles:true}));
    if(form.elements.structure_key)form.elements.structure_key.value=key;
    form.scrollIntoView({behavior:'smooth',block:'center'});
  }
  function showRatingHistory(userId){
    const item=state?.reality177?.ratings?.officials?.find(row=>Number(row.user_id)===Number(userId));
    if(!item)return;
    const rows=(item.history||[]).map(row=>`<div class="r177-log"><span><b>${esc(row.reason)}</b><small>${date(row.created_at)} · ${esc(row.source)}</small></span><strong class="${Number(row.delta)>=0?'plus':'minus'}">${Number(row.delta)>0?'+':''}${Number(row.delta)}</strong></div>`).join('');
    openModal(item.name,'📊 ИСТОРИЯ РЕЙТИНГА',`<article class="r177-info"><div><span>${esc(item.office_title)}</span><span>Рейтинг <b>${fmt(item.rating)}/100</b></span></div></article><div class="r177-log-list">${rows||'<div class="empty">Изменений рейтинга пока нет.</div>'}</div>`);
  }
  function openAuctionForm(propertyId){
    const item=state?.reality177?.property?.my_items?.find(row=>String(row.property_id)===String(propertyId));
    if(!item)return;
    const low=Math.floor(Number(item.purchase_price)*.5),high=Number(item.purchase_price);
    openModal(item.title,'🔨 ДОБРОВОЛЬНЫЙ АУКЦИОН',`<form id="r177AuctionStartForm" data-property="${esc(propertyId)}"><div class="field"><label>СТАРТОВАЯ ЦЕНА</label><input name="start_price" type="number" min="${low}" max="${high}" value="${low}"><small class="hint">Допустимо от ${fmt(low)} до ${fmt(high)}. Аукцион длится 24 часа, комиссия государства — 5%.</small></div><button class="action wide" type="submit">🔨 ВЫСТАВИТЬ НА АУКЦИОН</button></form>`);
  }
  function openInvestigationDecision(id,decision){
    const titles={clear:'Оправдать',warning:'Выдать предупреждение',refer:'Передать прокурору',seize:'Предложить арест',confiscate:'Предложить конфискацию'};
    openModal(titles[decision]||'Решение','🔎 ИМУЩЕСТВЕННАЯ ПРОВЕРКА',`<form id="r177InvestigationActionForm" data-id="${esc(id)}" data-decision="${esc(decision)}"><div class="field"><label>ЗАКЛЮЧЕНИЕ</label><textarea name="note" minlength="5" maxlength="800"></textarea></div><button class="${['seize','confiscate'].includes(decision)?'danger':'action'} wide" type="submit">ПОДТВЕРДИТЬ</button></form>`);
  }

  document.addEventListener('click',event=>{
    if(event.target.closest?.('[data-r177-close]')||event.target===document.getElementById('r177Modal')){closeModal();return}
    const programButton=event.target.closest?.('[data-r177-program]');
    if(programButton){const program=state?.reality177?.programs?.programs?.find(item=>item.key===programButton.dataset.r177Program);if(program)programForm(program);return}
    const tab=event.target.closest?.('[data-r177-property-tab]');if(tab){propertyTab=tab.dataset.r177PropertyTab;renderProperty();return}
    const rate=event.target.closest?.('[data-r177-rate]');if(rate){api({action:'official_rate',target_user_id:Number(rate.dataset.user),value:Number(rate.dataset.r177Rate)},rate);return}
    const ratingHistory=event.target.closest?.('[data-r177-rating-history]');if(ratingHistory){showRatingHistory(ratingHistory.dataset.r177RatingHistory);return}
    const history=event.target.closest?.('[data-r177-fund-history]');if(history){showFundHistory(history.dataset.r177FundHistory);return}
    const transfer=event.target.closest?.('[data-r177-fund-transfer]');if(transfer){prepareFundTransfer(transfer.dataset.r177FundTransfer);return}
    const buy=event.target.closest?.('[data-r177-buy]');if(buy&&confirm('Купить имущество с личного баланса вместе с налогом на роскошь?')){api({action:'property_buy',item_key:buy.dataset.r177Buy},buy);return}
    const sell=event.target.closest?.('[data-r177-sell]');if(sell&&confirm(`Вы получите 70% стоимости: ${fmt(sell.dataset.price)} влияния. Продажу нельзя отменить.`)){api({action:'property_sell',property_id:sell.dataset.r177Sell,request_id:requestId()},sell);return}
    const upgrade=event.target.closest?.('[data-r177-upgrade]');if(upgrade&&confirm('Оплатить улучшение имущества?')){api({action:'property_upgrade',property_id:upgrade.dataset.r177Upgrade},upgrade);return}
    const insure=event.target.closest?.('[data-r177-insure]');if(insure&&confirm('Купить страховку на 7 дней?')){api({action:'property_insure',property_id:insure.dataset.r177Insure},insure);return}
    const primary=event.target.closest?.('[data-r177-primary]');if(primary){api({action:'property_primary',property_id:primary.dataset.r177Primary},primary);return}
    const debt=event.target.closest?.('[data-r177-debt]');if(debt&&confirm('Погасить задолженность по содержанию?')){api({action:'property_debt_pay',property_id:debt.dataset.r177Debt},debt);return}
    const auction=event.target.closest?.('[data-r177-auction-start]');if(auction){openAuctionForm(auction.dataset.r177AuctionStart);return}
    const invest=event.target.closest?.('[data-r177-invest]');if(invest){openInvestigationDecision(invest.dataset.id,invest.dataset.r177Invest);return}
    const report=event.target.closest?.('[data-r177-expanded-report]');if(report&&confirm('Опубликовать расширенный отчёт Надзора в беседе?')){api({action:'oversight_expanded_report'},report);return}
    const declaration=event.target.closest?.('[data-r177-declaration-refresh]');if(declaration){api({action:'declaration_refresh'},declaration);return}
    const emergency=event.target.closest?.('[data-r177-emergency]');if(emergency&&confirm('Перевести 10% Резервного фонда в свободную казну?')){api({action:'emergency_transfer'},emergency);return}
    if(event.target.closest?.('#refreshButton'))setTimeout(()=>load(true),180);
    if(event.target.closest?.('[data-tab="treasury"],[data-tab="ratings177"],[data-tab="property177"]'))setTimeout(()=>load(true),120);
  },true);

  document.addEventListener('submit',event=>{
    const form=event.target;
    if(form.id==='r177ProgramForm'){
      event.preventDefault();const values=Object.fromEntries(new FormData(form).entries());const button=form.querySelector('button[type="submit"]');
      api({action:'program_start',program_key:form.dataset.key,request_id:requestId(),...values},button);return;
    }
    if(form.id==='r177AuctionStartForm'){
      event.preventDefault();const values=Object.fromEntries(new FormData(form).entries());
      api({action:'property_auction_start',property_id:form.dataset.property,start_price:Number(values.start_price),request_id:requestId()},form.querySelector('button[type="submit"]'));return;
    }
    if(form.classList?.contains('r177BidForm')){
      event.preventDefault();const values=Object.fromEntries(new FormData(form).entries());
      api({action:'property_auction_bid',auction_id:form.dataset.auction,auction_type:form.dataset.type,amount:Number(values.amount)},form.querySelector('button[type="submit"]'));return;
    }
    if(form.id==='r177InvestigationForm'){
      event.preventDefault();const values=Object.fromEntries(new FormData(form).entries());
      api({action:'property_investigation_open',...values},form.querySelector('button[type="submit"]'));return;
    }
    if(form.id==='r177InvestigationActionForm'){
      event.preventDefault();const values=Object.fromEntries(new FormData(form).entries());
      api({action:'property_investigation_action',investigation_id:form.dataset.id,decision:form.dataset.decision,note:values.note},form.querySelector('button[type="submit"]'));return;
    }
  },true);

  window.addEventListener('pageshow',()=>setTimeout(()=>load(true),80));
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(()=>load(true),100)});
  ensureLayout();
  load(true);
})();