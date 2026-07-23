(()=>{
  'use strict';
  if(window.__governmentRealityV179)return;
  window.__governmentRealityV179=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
  const duration=value=>{let sec=Math.max(0,Number(value)||0);const d=Math.floor(sec/86400);sec%=86400;const h=Math.floor(sec/3600);const m=Math.floor(sec%3600/60);return d?`${d} д. ${h} ч.`:h?`${h} ч. ${m} мин.`:`${Math.max(1,m)} мин.`};
  const requestId=()=>crypto?.randomUUID?.()||`r179-${Date.now()}-${Math.random().toString(36).slice(2)}`;

  let state=null;
  let loading=false;
  let busy=false;
  let view='projects';
  let timers=[];

  function toast(text,type='success'){
    const node=document.getElementById('toast');if(!node)return;
    node.textContent=String(text||'Готово');node.className=`toast show ${type}`;
    clearTimeout(node.__r179);node.__r179=setTimeout(()=>node.className='toast',4200);
  }

  function ensureLayout(){
    const stack=document.querySelector('.screen-stack');
    const nav=document.getElementById('bottomNav');
    if(stack&&!document.querySelector('.screen[data-screen="construction179"]')){
      stack.insertAdjacentHTML('beforeend',`<section class="screen r179-screen" data-screen="construction179"><div class="section-head"><div><small>REALITY 179 · ИНФРАСТРУКТУРА</small><h2>Государственное строительство</h2></div></div><div id="r179Construction"></div></section>`);
    }
    if(nav&&!nav.querySelector('[data-tab="construction179"]')){
      const treasury=nav.querySelector('[data-tab="treasury"]');
      const button=document.createElement('button');button.type='button';button.dataset.tab='construction179';button.innerHTML='<span>🏗</span><small>Строительство</small>';
      nav.insertBefore(button,treasury||null);
    }
    const ratingButton=nav?.querySelector('[data-tab="ratings177"] small');if(ratingButton)ratingButton.textContent='Доверие';
    const ratingHeading=document.querySelector('.screen[data-screen="ratings177"] h2');if(ratingHeading)ratingHeading.textContent='Рейтинг доверия власти';
  }

  function openModal(title,kicker,content){
    const titleNode=document.getElementById('r177ModalTitle'),kickerNode=document.getElementById('r177ModalKicker'),body=document.getElementById('r177ModalBody'),modal=document.getElementById('r177Modal');
    if(!modal||!body)return;
    titleNode.textContent=title;kickerNode.textContent=kicker;body.innerHTML=content;
    modal.classList.add('open');modal.setAttribute('aria-hidden','false');document.body.classList.add('r177-modal-open');
  }
  function closeModal(){const modal=document.getElementById('r177Modal');modal?.classList.remove('open');modal?.setAttribute('aria-hidden','true');document.body.classList.remove('r177-modal-open')}

  async function api(payload,button=null){
    if(busy)return null;busy=true;const old=button?.textContent||'';
    if(button){button.disabled=true;button.textContent='⌛ ВЫПОЛНЯЕМ…'}
    try{
      const response=await fetch('/government-v179/api/action',{method:'POST',cache:'no-store',headers,body:JSON.stringify({chat_id:chatId,...payload})});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Операция не выполнена.');
      toast(data.message||'Готово');tg?.HapticFeedback?.notificationOccurred?.('success');closeModal();await load(true);return data;
    }catch(error){toast(error.message||'Операция не выполнена.','error');tg?.HapticFeedback?.notificationOccurred?.('error');return null}
    finally{busy=false;if(button&&button.isConnected){button.disabled=false;button.textContent=old}}
  }

  async function load(force=false){
    if(!chatId||loading)return;loading=true;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_r179=${Date.now()}`,{cache:'no-store',headers:{'X-Telegram-Init-Data':tg?.initData||''}});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось загрузить Reality 179.');
      state=data;scheduleRender();
    }catch(error){toast(error.message||'Не удалось загрузить Reality 179.','error')}
    finally{loading=false}
  }

  function scheduleRender(){timers.forEach(clearTimeout);timers=[];[0,140,420].forEach(delay=>timers.push(setTimeout(render,delay)))}
  function statusText(status){return ({awaiting_vote:'Ожидает голосования',awaiting_funding:'Ожидает финансирования',building:'Строится',completed:'Завершён',frozen:'Заморожен',cancelled:'Отменён',active:'Работает',underfunded:'Недостаточное финансирование'})[status]||String(status||'—')}
  function sourceOptions(sources,selected=''){return (sources||[]).map(source=>`<option value="${esc(source.key)}" ${source.key===selected?'selected':''}>${esc(source.title)} · ${fmt(source.balance)}</option>`).join('')}

  function tabs(){return `<nav class="r179-tabs">${[['projects','🏗 Проекты'],['buildings','🏙 Объекты'],['effects','⚙️ Эффекты'],['ranking','🏆 Рейтинг'],['history','📋 История']].map(([key,title])=>`<button type="button" data-r179-view="${key}" class="${view===key?'active':''}">${title}</button>`).join('')}</nav>`}

  function catalog(data){
    if(!data.can_propose)return '<div class="r179-note">Предлагать государственные стройки могут Президент, министр финансов, депутаты и руководители профильных структур. Остальные участники могут вкладываться в уже утверждённые проекты.</div>';
    return `<div class="r179-catalog">${(data.catalog||[]).map(item=>`<article class="r179-card"><div class="r179-title"><span>${esc(item.emoji)}</span><div><b>${esc(item.title)}</b><small>${duration(item.duration)} · построено/заявлено ${item.count}/3</small></div><strong>${fmt(item.cost)}</strong></div><p>${esc(item.effect)}</p><div class="r179-meta"><span>Содержание <b>${(Number(item.maintenance_bp)/100).toLocaleString('ru-RU')}%</b> / 7 дней</span><span>Доверие инициатора <b>+${item.trust}</b></span></div><button type="button" class="action wide" data-r179-propose="${esc(item.key)}" ${item.available?'':'disabled'}>${item.available?'ПРЕДЛОЖИТЬ СТРОИТЕЛЬСТВО':'ЛИМИТ 3 ОБЪЕКТА'}</button></article>`).join('')}</div>`;
  }

  function projectCard(project,data){
    const progress=Math.min(100,Math.round(Number(project.funded_amount)*100/Math.max(1,Number(project.total_cost))));
    const spec=project.spec||{};const canFund=data.can_propose&&project.status==='awaiting_funding';
    return `<article class="r179-card project ${esc(project.status)}"><div class="r179-title"><span>${esc(spec.emoji||'🏗')}</span><div><b>${esc(spec.title||project.building_key)}</b><small>${esc(statusText(project.status))} · инициатор ${esc(project.initiator_name)}</small></div><strong>${fmt(project.total_cost)}</strong></div><div class="r179-progress"><i style="width:${progress}%"></i></div><div class="r179-meta"><span>Собрано <b>${fmt(project.funded_amount)}</b></span><span>Осталось <b>${fmt(project.remaining)}</b></span>${project.completes_at?`<span>Готово <b>${date(project.completes_at)}</b></span>`:''}</div>${project.cancelled_reason?`<div class="r179-warning">${esc(project.cancelled_reason)}</div>`:''}${project.status==='awaiting_funding'?`<div class="r179-actions"><button type="button" class="positive" data-r179-contribute="${esc(project.project_id)}" data-remaining="${Number(project.remaining)}">🤝 ВЛОЖИТЬСЯ В СТРОИТЕЛЬСТВО</button>${canFund?`<button type="button" class="secondary" data-r179-fund="${esc(project.project_id)}" data-building="${esc(project.building_key)}" data-remaining="${Number(project.remaining)}">🏛 НАПРАВИТЬ ГОССРЕДСТВА</button>`:''}</div>`:''}</article>`;
  }

  function projectsContent(data){
    const active=(data.projects||[]).filter(item=>item.status!=='completed'&&item.status!=='cancelled');
    const completed=(data.projects||[]).filter(item=>item.status==='completed'||item.status==='cancelled').slice(0,12);
    return `<div class="section-head r179-subhead"><div><small>НОВЫЕ ОБЪЕКТЫ</small><h2>Доступные проекты</h2></div></div>${catalog(data)}<div class="section-head r179-subhead"><div><small>ФИНАНСИРОВАНИЕ И РАБОТЫ</small><h2>Текущие проекты</h2></div></div>${active.map(item=>projectCard(item,data)).join('')||'<div class="empty">Активных проектов нет.</div>'}<details class="r177-details"><summary>Завершённые и отменённые проекты</summary><div>${completed.map(item=>projectCard(item,data)).join('')||'<div class="empty">История проектов пуста.</div>'}</div></details>`;
  }

  function buildingsContent(data){return (data.buildings||[]).map(item=>`<article class="r179-card building ${esc(item.status)}"><div class="r179-title"><span>${esc(item.spec?.emoji||'🏛')}</span><div><b>${esc(item.spec?.title||item.building_key)} · объект ${item.level_no}/3</b><small>${esc(statusText(item.status))} · инициатор ${esc(item.initiator_name)}</small></div></div><p>${esc(item.spec?.effect||'')}</p><div class="r179-meta"><span>Содержание <b>${fmt(item.spec?.maintenance)}</b></span><span>Следующее <b>${date(item.next_maintenance_at)}</b></span>${item.next_income_at?`<span>Доход <b>${date(item.next_income_at)}</b></span>`:''}</div>${Number(item.maintenance_debt)>0?`<div class="r179-warning">Долг по содержанию: ${fmt(item.maintenance_debt)}</div><button type="button" class="positive wide" data-r179-debt="${esc(item.building_id)}" data-building="${esc(item.building_key)}">🧾 ПОГАСИТЬ ДОЛГ</button>`:''}</article>`).join('')||'<div class="empty">Построенных объектов пока нет.</div>'}

  function effectsContent(data){const effects=data.effects||{},counts=effects.counts||{};const cards=[['🏫','Гранты',effects.education_bonus_percent],['🏥','Социальная помощь',effects.social_bonus_percent],['🎭','Фестивали',effects.festival_bonus_percent],['🔬','Научные проекты',effects.science_bonus_percent],['🏘','Скидка на имущество',effects.property_maintenance_discount_percent],['🏦','Снижение комиссий',effects.bank_fee_discount_percent],['🚓','Защита казны',effects.treasury_loss_reduction_percent],['⚡','Доход заводов',effects.factory_income_bonus_percent]];return `<div class="r179-effect-grid">${cards.map(([emoji,title,value])=>`<article><span>${emoji}</span><small>${esc(title)}</small><b>+${fmt(value)}%</b></article>`).join('')}</div><div class="r179-counts">${Object.entries(counts).map(([key,value])=>`<span>${esc(key)}: <b>${fmt(value)}</b></span>`).join('')}</div>`}
  function rankingContent(data){return (data.ranking||[]).map((item,index)=>`<div class="r177-rank"><strong>${index+1}</strong><span><b>${esc(item.name)}</b><small>${esc(item.title)} · внесено ${fmt(item.amount)}</small></span><b>${fmt(item.score)}</b></div>`).join('')||'<div class="empty">Строительных вкладов пока нет.</div>'}
  function historyContent(data){return `<div class="r177-log-list">${(data.history||[]).map(item=>`<div class="r177-log"><span><b>${esc(item.detail)}</b><small>${date(item.created_at)} · ${esc(item.operation_type)}</small></span><strong>${Number(item.amount)?fmt(item.amount):'—'}</strong></div>`).join('')||'<div class="empty">История строительства пуста.</div>'}</div>`}

  function renderConstruction(){const mount=document.getElementById('r179Construction'),data=state?.reality179?.construction;if(!mount||!data)return;let content=projectsContent(data);if(view==='buildings')content=buildingsContent(data);if(view==='effects')content=effectsContent(data);if(view==='ranking')content=rankingContent(data);if(view==='history')content=historyContent(data);mount.innerHTML=tabs()+content}

  function renderTrust(){
    const mount=document.getElementById('r177Ratings'),trust=state?.reality179?.trust;if(!mount||!trust)return;
    let card=document.getElementById('r179OverallTrust');
    if(!card){card=document.createElement('article');card.id='r179OverallTrust';card.className='r179-trust-card';mount.prepend(card)}
    card.innerHTML=`<div><small>🏛 ОБЩЕЕ ДОВЕРИЕ К ВЛАСТИ</small><b>${fmt(trust.overall)} / 100</b><em>${esc(trust.label)}</em></div><div class="r177-rating-bar"><i style="width:${Math.max(0,Math.min(100,Number(trust.overall)||0))}%"></i></div><div class="r179-trust-sources">${(trust.sources_7d||[]).slice(0,5).map(item=>`<span>${esc(item.source)} <b>${Number(item.delta)>0?'+':''}${fmt(item.delta)}</b></span>`).join('')||'<span>Значимых изменений за 7 дней нет</span>'}</div>`;
  }

  function render(){ensureLayout();renderConstruction();renderTrust()}

  document.addEventListener('click',event=>{
    const viewButton=event.target.closest('[data-r179-view]');if(viewButton){view=viewButton.dataset.r179View;renderConstruction();return}
    const nav=event.target.closest('[data-tab="construction179"],[data-tab="ratings177"]');if(nav){setTimeout(()=>{render();load(true)},80);return}
    const propose=event.target.closest('[data-r179-propose]');if(propose){const data=state?.reality179?.construction;const item=(data?.catalog||[]).find(row=>row.key===propose.dataset.r179Propose);if(!item)return;openModal(item.title,`${item.emoji} НОВЫЙ ГОСУДАРСТВЕННЫЙ ОБЪЕКТ`,`<article class="r177-info"><p>${esc(item.effect)}</p><div><span>Стоимость: <b>${fmt(item.cost)}</b></span><span>Срок: <b>${duration(item.duration)}</b></span><span>Лимит: <b>${item.count}/3</b></span></div></article><form id="r179ProposeForm" data-key="${esc(item.key)}"><div class="field"><label>ИСТОЧНИК ФИНАНСИРОВАНИЯ</label><select name="source_key">${sourceOptions(item.sources)}</select></div><button class="action wide" type="submit">🏗 СОЗДАТЬ ПРОЕКТ</button></form>`);return}
    const contribute=event.target.closest('[data-r179-contribute]');if(contribute){openModal('Вложиться в строительство','🤝 ДОБРОВОЛЬНЫЙ СТРОИТЕЛЬНЫЙ ВКЛАД',`<form id="r179ContributionForm" data-project="${esc(contribute.dataset.r179Contribute)}"><div class="field"><label>СУММА ВКЛАДА</label><input name="amount" type="number" min="100" max="${Number(contribute.dataset.remaining)}" value="${Math.min(10000,Number(contribute.dataset.remaining))}"><small class="hint">Фиксированного максимума нет. Излишек сверх остатка проекта не спишется.</small></div><button class="positive wide" type="submit">🤝 ВЛОЖИТЬСЯ В СТРОИТЕЛЬСТВО</button></form>`);return}
    const fund=event.target.closest('[data-r179-fund]');if(fund){const item=(state?.reality179?.construction?.catalog||[]).find(row=>row.key===fund.dataset.building);if(!item)return;openModal('Государственное финансирование','🏛 КАЗНА И ПРОФИЛЬНЫЕ ФОНДЫ',`<form id="r179FundForm" data-project="${esc(fund.dataset.r179Fund)}"><div class="field"><label>ИСТОЧНИК</label><select name="source_key">${sourceOptions(item.sources)}</select></div><div class="field"><label>СУММА</label><input name="amount" type="number" min="1" max="${Number(fund.dataset.remaining)}" value="${Number(fund.dataset.remaining)}"></div><button class="action wide" type="submit">🏛 НАПРАВИТЬ СРЕДСТВА</button></form>`);return}
    const debt=event.target.closest('[data-r179-debt]');if(debt){const item=(state?.reality179?.construction?.catalog||[]).find(row=>row.key===debt.dataset.building);if(!item)return;openModal('Погасить долг объекта','🧾 ВОССТАНОВЛЕНИЕ ФИНАНСИРОВАНИЯ',`<form id="r179DebtForm" data-building-id="${esc(debt.dataset.r179Debt)}"><div class="field"><label>ИСТОЧНИК</label><select name="source_key">${sourceOptions(item.sources)}</select></div><button class="positive wide" type="submit">🧾 ПОГАСИТЬ ДОЛГ</button></form>`);return}
  });

  document.addEventListener('submit',event=>{
    const form=event.target;
    if(form.id==='r179ProposeForm'){event.preventDefault();const values=Object.fromEntries(new FormData(form).entries());api({action:'construction_propose',building_key:form.dataset.key,source_key:values.source_key,request_id:requestId()},form.querySelector('button'));return}
    if(form.id==='r179ContributionForm'){event.preventDefault();const values=Object.fromEntries(new FormData(form).entries());api({action:'construction_contribute',project_id:form.dataset.project,amount:Number(values.amount),request_id:requestId()},form.querySelector('button'));return}
    if(form.id==='r179FundForm'){event.preventDefault();const values=Object.fromEntries(new FormData(form).entries());api({action:'construction_fund',project_id:form.dataset.project,source_key:values.source_key,amount:Number(values.amount),request_id:requestId()},form.querySelector('button'));return}
    if(form.id==='r179DebtForm'){event.preventDefault();const values=Object.fromEntries(new FormData(form).entries());api({action:'construction_debt_pay',building_id:form.dataset.buildingId,source_key:values.source_key,request_id:requestId()},form.querySelector('button'));return}
  });

  window.addEventListener('pageshow',()=>load(true));
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)load(true)});
  ensureLayout();load();
})();
