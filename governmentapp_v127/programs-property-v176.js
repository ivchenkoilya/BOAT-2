(()=>{
  'use strict';
  if(window.__governmentProgramsPropertyV176)return;
  window.__governmentProgramsPropertyV176=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
  let state=null;
  let loading=false;
  let busy=false;
  let activePropertyTab='store';
  let renderTimers=[];

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=String(text||'Готово.');
    node.className=`toast show ${type}`;
    clearTimeout(node.__r176Toast);
    node.__r176Toast=setTimeout(()=>node.className='toast',3800);
  }

  function scheduleRender(){
    renderTimers.forEach(clearTimeout);renderTimers=[];
    [0,140,420,900].forEach(delay=>renderTimers.push(setTimeout(render,delay)));
  }

  async function load(){
    if(!chatId||loading)return;
    loading=true;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_r176=${Date.now()}`,{
        cache:'no-store',headers:{'X-Telegram-Init-Data':tg?.initData||''},
      });
      const data=await response.json();
      if(!response.ok||!data?.ok)throw new Error(data?.reason||'Не удалось загрузить Reality 176.');
      state=data;
      scheduleRender();
    }catch(error){toast(error.message||'Не удалось загрузить обновление.','error')}
    finally{loading=false}
  }

  async function action(payload,confirmText=''){
    if(busy)return false;
    if(confirmText&&!confirm(confirmText))return false;
    busy=true;
    try{
      const response=await fetch('/government-v176/api/action',{
        method:'POST',cache:'no-store',headers,
        body:JSON.stringify({chat_id:chatId,...payload}),
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      toast(data.message||'Готово.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      closeModal();
      await load();
      setTimeout(()=>document.getElementById('refreshButton')?.click(),120);
      setTimeout(load,700);
      return true;
    }catch(error){
      toast(error.message||'Действие не выполнено.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
      return false;
    }finally{busy=false}
  }

  function ensureContainers(){
    const treasury=document.querySelector('.screen[data-screen="treasury"]');
    if(treasury&&!document.getElementById('r176Programs')){
      const holder=document.createElement('section');
      holder.id='r176Programs';
      holder.className='r176-section';
      const anchor=document.getElementById('taxPolicy')||document.getElementById('treasuryHero');
      anchor?.insertAdjacentElement('afterend',holder);
    }
    const powers=document.querySelector('.screen[data-screen="powers"]');
    if(powers&&!document.getElementById('r176PropertyQuick')){
      const holder=document.createElement('section');
      holder.id='r176PropertyQuick';
      holder.className='r176-section';
      const anchor=document.getElementById('powerHero');
      anchor?.insertAdjacentElement('afterend',holder);
    }
    if(!document.getElementById('r176Modal')){
      document.body.insertAdjacentHTML('beforeend',`
        <div class="r176-modal" id="r176Modal" aria-hidden="true">
          <section class="r176-sheet">
            <header class="r176-sheet-head"><div><small id="r176ModalKicker">REALITY 176</small><h3 id="r176ModalTitle">Действие</h3></div><button type="button" data-r176-close>×</button></header>
            <div class="r176-modal-body" id="r176ModalBody"></div>
          </section>
        </div>`);
    }
  }

  function statusLabel(value){return ({owned:'Активно',seized_debt:'Арестовано за долги',seized_investigation:'Временно арестовано',auction:'На аукционе',state_owned:'Государственная собственность',open:'Открыта',referred:'Передана прокурору',bill_pending:'Решение в Госдуме',resolved:'Завершена',cleared:'Оправдан',warning:'Предупреждение'})[value]||String(value||'—')}

  function prestigeTitle(value,count=0){
    const total=Number(value)||0;
    if(total>=25000000)return 'Дворцовый магнат';
    if(total>=10000000)return 'Олигарх реальности';
    if(total>=5000000)return 'Авиационный магнат';
    if(total>=2000000)return 'Владелец империи роскоши';
    if(total>=500000)return 'Элитный собственник';
    if(total>0)return count>1?'Коллекционер статуса':'Солидный чиновник';
    return 'Имущество ещё не приобретено';
  }

  function renderPrograms(){
    const holder=document.getElementById('r176Programs');
    const data=state?.reality176?.programs;
    if(!holder||!data)return;
    const cards=(data.programs||[]).map(program=>{
      const disabled=!program.can_start||program.cooldown_remaining||Number(program.fund_balance)<Number(program.calculated_cost);
      const stateLine=program.active?`Активна до ${date(program.ends_at)}`:program.cooldown_remaining?`Перезарядка: ${esc(program.cooldown_remaining)}`:'Готова к запуску';
      return `<article class="r176-card program ${program.active?'active':''}">
        <div class="r176-card-title"><span>${esc(program.emoji)}</span><div><b>${esc(program.title)}</b><small>${esc(program.fund_title)} · баланс ${fmt(program.fund_balance)}</small></div></div>
        <p>${esc(program.effect)}</p>
        <div class="r176-meta"><span>Стоимость: <b>${fmt(program.calculated_cost)}</b></span><span>${stateLine}</span></div>
        <button class="action wide" type="button" data-r176-program="${esc(program.key)}" ${disabled?'disabled':''}>${program.active?'✓ ДЕЙСТВУЕТ':program.cooldown_remaining?'⌛ НЕДОСТУПНО':'▶ ЗАПУСТИТЬ'}</button>
      </article>`;
    }).join('');
    const effects=(data.active_effects||[]).map(item=>`<div class="r176-log"><span><b>${esc((data.programs||[]).find(p=>p.key===item.effect_key)?.title||item.effect_key)}</b><small>до ${date(item.ends_at)}</small></span><strong>АКТИВНО</strong></div>`).join('');
    const expenses=(data.expenses||[]).slice(0,8).map(item=>`<div class="r176-log"><span><b>${esc(item.detail)}</b><small>${date(item.created_at)}</small></span><strong>−${fmt(item.amount)}</strong></div>`).join('');
    holder.innerHTML=`
      <div class="section-head"><div><small>РАСХОДЫ ГОСУДАРСТВЕННЫХ ФОНДОВ</small><h2>Государственные программы</h2></div></div>
      <div class="r176-grid">${cards}</div>
      ${data.can_expanded_report?'<button class="secondary wide r176-report" type="button" data-r176-expanded-report>📊 ОПУБЛИКОВАТЬ РАСШИРЕННЫЙ ОТЧЁТ НАДЗОРА</button>':''}
      <details class="r176-details"><summary>Активные эффекты и история расходов</summary><div class="r176-log-list">${effects||'<div class="empty">Активных эффектов нет.</div>'}${expenses||'<div class="empty">Расходов программ пока нет.</div>'}</div></details>`;
  }

  function renderPropertyQuick(){
    const holder=document.getElementById('r176PropertyQuick');
    const data=state?.reality176?.property;
    if(!holder||!data)return;
    const value=(data.my_items||[]).reduce((sum,item)=>sum+Number(item.purchase_price||0),0);
    const debts=(data.my_items||[]).reduce((sum,item)=>sum+Number(item.debt||0),0);
    const icons=(data.my_items||[]).filter(item=>item.status!=='auction'&&item.status!=='state_owned').slice(0,6).map(item=>item.emoji).join(' ');
    const prestige=prestigeTitle(value,(data.my_items||[]).length);
    holder.innerHTML=`
      <div class="section-head"><div><small>ЛИЧНЫЙ ПРЕСТИЖ И ДЕКЛАРАЦИИ</small><h2>Имущество чиновников</h2></div></div>
      <div class="r176-quick-grid">
        <article class="r176-quick" data-r176-property="store"><span>🏛</span><div><b>Имущество чиновников</b><small>${esc(prestige)}${icons?` · ${esc(icons)}`:''}</small></div><strong>${(data.my_items||[]).length} · ${fmt(value)}</strong></article>
        <article class="r176-quick" data-r176-property="auction"><span>🔨</span><div><b>Государственный аукцион</b><small>Конфискованное имущество и защищённые ставки</small></div><strong>${(data.auctions||[]).length}</strong></article>
        ${data.can_investigate?'<article class="r176-quick" data-r176-property="investigations"><span>🔎</span><div><b>Имущественная проверка</b><small>Декларации, предупреждения, прокурор и предложения конфискации</small></div><strong>'+(data.investigations||[]).filter(x=>x.status==='open'||x.status==='referred').length+'</strong></article>':''}
      </div>
      ${debts?`<div class="r176-alert">🔒 Задолженность по содержанию: <b>${fmt(debts)}</b></div>`:''}`;
  }

  function render(){
    if(!state)return;
    ensureContainers();
    renderPrograms();
    renderPropertyQuick();
    if(document.getElementById('r176Modal')?.classList.contains('open'))renderPropertyModal(activePropertyTab);
  }

  function openModal(title,kicker,content){
    ensureContainers();
    document.getElementById('r176ModalTitle').textContent=title;
    document.getElementById('r176ModalKicker').textContent=kicker||'REALITY 176';
    document.getElementById('r176ModalBody').innerHTML=content;
    const modal=document.getElementById('r176Modal');
    modal.classList.add('open');modal.setAttribute('aria-hidden','false');
    document.body.style.overflow='hidden';
  }

  function closeModal(){
    const modal=document.getElementById('r176Modal');
    modal?.classList.remove('open');modal?.setAttribute('aria-hidden','true');
    document.body.style.overflow='';
  }

  function openProgram(key){
    const program=state?.reality176?.programs?.programs?.find(item=>item.key===key);
    if(!program)return;
    let extra='';
    if(['festival','social_help','oversight_operation','market_intervention','election_campaign'].includes(key)){
      extra+=`<div class="field"><label>СУММА ИЗ ФОНДА</label><input name="amount" type="number" min="${program.min_cost}" max="${Math.min(program.max_cost,program.fund_balance)}" value="${program.calculated_cost}"><small class="hint">Доступно в фонде: ${fmt(program.fund_balance)}</small></div>`;
    }
    if(key==='social_help')extra+=`<div class="field"><label>ПОЛУЧАТЕЛЕЙ</label><select name="recipient_count"><option value="3">3 участника</option><option value="4">4 участника</option><option value="5" selected>5 участников</option></select></div>`;
    if(key==='market_intervention')extra+=`<div class="field"><label>АКЦИЯ</label><select name="symbol"><option value="EGO">👑 EGO</option><option value="HERO">⚡ HERO</option><option value="NPC">🎭 NPC</option><option value="CORV">🐦‍⬛ CORV</option><option value="CENTER">🌌 CENTER</option></select></div>`;
    openModal(program.title,`${program.emoji} ГОСУДАРСТВЕННАЯ ПРОГРАММА`,`
      <article class="r176-modal-card"><p>${esc(program.effect)}</p><div class="r176-meta"><span>Фонд: <b>${esc(program.fund_title)}</b></span><span>Баланс: <b>${fmt(program.fund_balance)}</b></span></div></article>
      <form id="r176ProgramForm" data-program-key="${esc(key)}">${extra}<button class="action wide" type="submit">${program.emoji} ПОДТВЕРДИТЬ ЗАПУСК</button></form>`);
  }

  function propertyTabs(active){
    const data=state?.reality176?.property||{};
    const tabs=[['store','🏛 Магазин'],['mine','💼 Моё'],['declarations','📄 Декларации'],['ranking','🏆 Рейтинг'],['auction','🔨 Аукцион']];
    if(data.can_investigate)tabs.push(['investigations','🔎 Проверки']);
    return `<nav class="r176-tabs">${tabs.map(([key,title])=>`<button type="button" class="${active===key?'active':''}" data-r176-property-tab="${key}">${title}</button>`).join('')}</nav>`;
  }

  function storeContent(data){
    if(!data.is_official)return '<div class="empty">Покупать новое имущество могут только действующие чиновники. Декларации и аукцион доступны для просмотра.</div>';
    return `<div class="r176-shop">${(data.catalog||[]).map(item=>`<article class="r176-item ${item.owned?'owned':''}"><div class="r176-card-title"><span>${esc(item.emoji)}</span><div><b>${esc(item.title)}</b><small>Цена ${fmt(item.price)} + налог ${fmt(item.luxury_tax)}</small></div></div><div class="r176-meta"><span>Всего: <b>${fmt(item.total_cost)}</b></span><span>Содержание: ${(Number(item.maintenance_bp)/100).toLocaleString('ru-RU')}% / 7 дней</span></div><button type="button" class="action wide" data-r176-buy="${esc(item.key)}" ${!item.allowed||item.owned?'disabled':''}>${item.owned?'✓ УЖЕ ЕСТЬ':item.allowed?'КУПИТЬ':'НЕДОСТУПНО ДЛЯ ДОЛЖНОСТИ'}</button></article>`).join('')}</div>`;
  }

  function mineContent(data){
    const items=data.my_items||[];
    return `<div class="r176-toolbar"><button type="button" class="secondary wide" data-r176-declaration-refresh>📄 ОБНОВИТЬ МОЮ ДЕКЛАРАЦИЮ</button></div>${items.length?items.map(item=>`<article class="r176-item"><div class="r176-card-title"><span>${esc(item.emoji)}</span><div><b>${esc(item.title)}</b><small>${esc(statusLabel(item.status))}</small></div></div><div class="r176-meta"><span>Стоимость: <b>${fmt(item.purchase_price)}</b></span><span>Следующее содержание: ${date(item.next_maintenance_at)}</span></div>${item.debt?`<div class="r176-alert">Долг: <b>${fmt(item.debt)}</b></div><button class="positive wide" type="button" data-r176-pay-debt="${esc(item.property_id)}">ПОГАСИТЬ ДОЛГ</button>`:''}</article>`).join(''):'<div class="empty">Имущество пока не приобретено.</div>'}`;
  }

  function declarationsContent(data){
    return (data.declarations||[]).length?`<div class="r176-declarations">${data.declarations.map(person=>`<details class="r176-details"><summary><span><b>${esc(person.name)}</b><small>${esc(prestigeTitle(person.total_value,person.items.length))} · ${person.offices.map(key=>esc(state.office_specs?.[key]?.title||key)).join(' · ')}</small></span><strong>${fmt(person.total_value)}</strong></summary><div class="r176-declaration-grid"><div><small>ЛИЧНЫЙ БАЛАНС</small><b>${fmt(person.balance)}</b></div><div><small>ИМУЩЕСТВО</small><b>${person.items.length}</b></div><div><small>НАЛОГИ</small><b>${fmt(person.luxury_tax_paid)}</b></div><div><small>СОДЕРЖАНИЕ</small><b>${fmt(person.maintenance_paid)}</b></div></div><div class="r176-log-list">${person.items.length?person.items.map(item=>`<div class="r176-log"><span><b>${esc(item.emoji)} ${esc(item.title)}</b><small>${esc(statusLabel(item.status))}${item.debt?` · долг ${fmt(item.debt)}`:''}</small></span><strong>${fmt(item.value)}</strong></div>`).join(''):'<div class="empty">Имущества нет.</div>'}</div></details>`).join('')}</div>`:'<div class="empty">Действующих чиновников для деклараций нет.</div>';
  }

  function rankingContent(data){
    return (data.ranking||[]).length?`<div class="r176-ranking">${data.ranking.map((person,index)=>`<div class="r176-rank"><strong>${index+1}</strong><span><b>${esc(person.name)}</b><small>${esc(prestigeTitle(person.total_value,person.count))} · ${person.count} объектов · самый дорогой ${fmt(person.most_expensive)} · налог ${fmt(person.tax_paid)}</small></span><b>${fmt(person.total_value)}</b></div>`).join('')}</div>`:'<div class="empty">Рейтинг пока пуст.</div>';
  }

  function auctionContent(data){
    return (data.auctions||[]).length?`<div class="r176-auctions">${data.auctions.map(item=>`<article class="r176-item"><div class="r176-card-title"><span>${esc(item.emoji)}</span><div><b>${esc(item.title)}</b><small>Бывший владелец: ${esc(item.former_owner_name)} · до ${date(item.ends_at)}</small></div></div><div class="r176-meta"><span>Текущая ставка: <b>${fmt(item.current_price||item.start_price)}</b></span><span>Минимум: <b>${fmt(item.minimum_bid)}</b></span></div>${item.current_bidder_name?`<p>Лидирует: <b>${esc(item.current_bidder_name)}</b></p>`:''}<form class="r176BidForm" data-auction-id="${esc(item.auction_id)}"><div class="field"><label>ВАША СТАВКА</label><input name="amount" type="number" min="${item.minimum_bid}" value="${item.minimum_bid}"></div><button class="action wide" type="submit" ${item.can_bid?'':'disabled'}>${item.can_bid?'СДЕЛАТЬ СТАВКУ':'СТАВКА НЕДОСТУПНА'}</button></form></article>`).join('')}</div>`:'<div class="empty">Активных государственных аукционов нет.</div>';
  }

  function investigationsContent(data){
    const users=(state.eligible_users||[]).map(user=>`<option value="${user.user_id}">${esc(user.name)} · ${fmt(user.career_points)} карьеры</option>`).join('');
    const properties=(data.declarations||[]).flatMap(person=>person.items.map(item=>`<option value="${esc(item.property_id)}">${esc(person.name)} · ${esc(item.emoji)} ${esc(item.title)}</option>`)).join('');
    const openForm=`<details class="r176-details" open><summary>Открыть имущественную проверку</summary><form id="r176InvestigationForm"><div class="field"><label>ПРОВЕРЯЕМЫЙ</label><select name="target_user_id">${users}</select></div><div class="field"><label>КОНКРЕТНЫЙ ОБЪЕКТ, ЕСЛИ НУЖЕН АРЕСТ</label><select name="property_id"><option value="">Без конкретного объекта</option>${properties}</select></div><div class="field"><label>ОСНОВАНИЕ</label><textarea name="reason" maxlength="800" placeholder="Несоответствие доходов, крупная покупка, долг или жалоба"></textarea></div><button class="action wide" type="submit">🔎 ОТКРЫТЬ ПРОВЕРКУ</button></form></details>`;
    const rows=(data.investigations||[]).map(item=>`<article class="r176-item"><div class="r176-card-title"><span>🔎</span><div><b>${esc(item.target_name)}</b><small>${esc(statusLabel(item.status))} · ${date(item.created_at)}</small></div></div><p>${esc(item.reason)}</p>${item.result?`<div class="r176-alert">${esc(item.result)}</div>`:''}${['open','referred'].includes(item.status)?`<div class="r176-invest-actions"><button type="button" class="secondary" data-r176-invest-action="clear" data-investigation="${esc(item.investigation_id)}">Оправдать</button><button type="button" class="secondary" data-r176-invest-action="warning" data-investigation="${esc(item.investigation_id)}">Предупредить</button><button type="button" class="secondary" data-r176-invest-action="refer" data-investigation="${esc(item.investigation_id)}">Прокурору</button><button type="button" class="danger" data-r176-invest-action="seize" data-investigation="${esc(item.investigation_id)}" ${item.property_id?'':'disabled'}>Арест</button><button type="button" class="danger" data-r176-invest-action="confiscate" data-investigation="${esc(item.investigation_id)}" ${item.property_id?'':'disabled'}>Конфискация</button></div>`:''}</article>`).join('');
    return openForm+(rows||'<div class="empty">Имущественных проверок пока нет.</div>');
  }

  function renderPropertyModal(tab){
    const data=state?.reality176?.property;
    const body=document.getElementById('r176ModalBody');
    if(!data||!body)return;
    activePropertyTab=tab;
    let content='';
    if(tab==='store')content=storeContent(data);
    else if(tab==='mine')content=mineContent(data);
    else if(tab==='declarations')content=declarationsContent(data);
    else if(tab==='ranking')content=rankingContent(data);
    else if(tab==='auction')content=auctionContent(data);
    else if(tab==='investigations')content=investigationsContent(data);
    body.innerHTML=propertyTabs(tab)+`<div class="r176-tab-content">${content}</div>`;
  }

  function openProperty(tab='store'){
    openModal('Имущество чиновников','🏛 REALITY 176','');
    renderPropertyModal(tab);
  }

  function openInvestigationDecision(id,decision){
    const titles={clear:'Оправдать проверяемого',warning:'Выдать предупреждение',refer:'Передать прокурору',seize:'Предложить временный арест',confiscate:'Предложить конфискацию'};
    openModal(titles[decision]||'Решение по проверке','🔎 ИМУЩЕСТВЕННАЯ ПРОВЕРКА',`<form id="r176InvestigationActionForm" data-investigation="${esc(id)}" data-decision="${esc(decision)}"><div class="field"><label>ЗАКЛЮЧЕНИЕ И ОБОСНОВАНИЕ</label><textarea name="note" maxlength="800" placeholder="Опишите доказательства и основание решения"></textarea></div><button class="${decision==='seize'||decision==='confiscate'?'danger':'action'} wide" type="submit">ПОДТВЕРДИТЬ РЕШЕНИЕ</button></form>`);
  }

  document.addEventListener('click',event=>{
    if(event.target.closest?.('[data-r176-close]')||event.target===document.getElementById('r176Modal')){closeModal();return}
    const program=event.target.closest?.('[data-r176-program]');if(program){openProgram(program.dataset.r176Program);return}
    if(event.target.closest?.('[data-r176-expanded-report]')){action({action:'oversight_expanded_report'},'Опубликовать расширенный отчёт Надзора?');return}
    const property=event.target.closest?.('[data-r176-property]');if(property){openProperty(property.dataset.r176Property||'store');return}
    const tab=event.target.closest?.('[data-r176-property-tab]');if(tab){renderPropertyModal(tab.dataset.r176PropertyTab);return}
    const buy=event.target.closest?.('[data-r176-buy]');if(buy){action({action:'property_buy',item_key:buy.dataset.r176Buy},'Купить имущество с личного баланса вместе с налогом на роскошь?');return}
    const debt=event.target.closest?.('[data-r176-pay-debt]');if(debt){action({action:'property_debt_pay',property_id:debt.dataset.r176PayDebt},'Погасить долг и перечислить деньги в казну?');return}
    if(event.target.closest?.('[data-r176-declaration-refresh]')){action({action:'declaration_refresh'});return}
    const invest=event.target.closest?.('[data-r176-invest-action]');if(invest){openInvestigationDecision(invest.dataset.investigation,invest.dataset.r176InvestAction);return}
    if(event.target.closest?.('#refreshButton'))setTimeout(load,240);
    if(event.target.closest?.('[data-tab="treasury"],[data-tab="powers"],[data-tab="home"]')){setTimeout(render,120);setTimeout(load,420)}
  },true);

  document.addEventListener('submit',event=>{
    const form=event.target;
    if(form.id==='r176ProgramForm'){
      event.preventDefault();const values=Object.fromEntries(new FormData(form).entries());
      action({action:'program_start',program_key:form.dataset.programKey,...values},'Запустить программу и списать средства именно из указанного государственного фонда?');return;
    }
    if(form.classList?.contains('r176BidForm')){
      event.preventDefault();const values=Object.fromEntries(new FormData(form).entries());
      action({action:'property_auction_bid',auction_id:form.dataset.auctionId,amount:Number(values.amount)},'Сумма ставки будет временно заблокирована. Подтвердить?');return;
    }
    if(form.id==='r176InvestigationForm'){
      event.preventDefault();const values=Object.fromEntries(new FormData(form).entries());
      action({action:'property_investigation_open',...values},'Открыть официальную имущественную проверку?');return;
    }
    if(form.id==='r176InvestigationActionForm'){
      event.preventDefault();const values=Object.fromEntries(new FormData(form).entries());
      action({action:'property_investigation_action',investigation_id:form.dataset.investigation,decision:form.dataset.decision,note:values.note},'Подтвердить официальное решение Надзора?');return;
    }
  },true);

  window.addEventListener('pageshow',()=>setTimeout(load,100));
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(load,120)});
  ensureContainers();
  load();
})();
