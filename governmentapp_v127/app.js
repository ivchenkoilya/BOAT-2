(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  tg?.ready();tg?.expand();tg?.setHeaderColor?.('#08070c');tg?.setBackgroundColor?.('#08070c');
  const $=id=>document.getElementById(id);
  const params=new URLSearchParams(location.search);
  const startParam=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||'');
  const chatId=Number(params.get('chat_id')||(startParam.startsWith('government_')?startParam.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
  const draftStorageKey=`government-drafts-v130:${chatId}`;
  let state=null,busy=false,toastTimer=null,refreshTimer=null,drafts={};

  try{drafts=JSON.parse(sessionStorage.getItem(draftStorageKey)||'{}')||{}}catch(_error){drafts={}}

  function toast(text,type='success'){
    const node=$('toast');node.textContent=text;node.className=`toast show ${type}`;
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>node.className='toast',3400);
  }

  function formKey(form){
    if(form.matches('.nominate-form'))return `nominate:${form.dataset.election||''}`;
    return form.id||'';
  }

  function captureDrafts(){
    document.querySelectorAll('form').forEach(form=>{
      const key=formKey(form);if(!key)return;
      const values={};
      form.querySelectorAll('input[name],textarea[name],select[name]').forEach(field=>{
        if(field.type==='checkbox'){
          if(!Array.isArray(values[field.name]))values[field.name]=[];
          if(field.checked)values[field.name].push(field.value);
        }else values[field.name]=field.value;
      });
      drafts[key]=values;
    });
    try{sessionStorage.setItem(draftStorageKey,JSON.stringify(drafts))}catch(_error){}
  }

  function restoreDrafts(){
    document.querySelectorAll('form').forEach(form=>{
      const values=drafts[formKey(form)];if(!values)return;
      form.querySelectorAll('input[name],textarea[name],select[name]').forEach(field=>{
        if(!(field.name in values))return;
        if(field.type==='checkbox')field.checked=Array.isArray(values[field.name])&&values[field.name].includes(field.value);
        else field.value=String(values[field.name]??'');
      });
      if(form.id==='billForm'&&$('billType')&&$('billExtra')){
        const type=$('billType').value;
        $('billExtra').innerHTML=billExtra(type);
        const refreshed=drafts[formKey(form)]||{};
        $('billExtra').querySelectorAll('input[name],textarea[name],select[name]').forEach(field=>{
          if(field.name in refreshed)field.value=String(refreshed[field.name]??'');
        });
      }
    });
  }

  function isEditing(){
    const active=document.activeElement;
    return Boolean(active&&active.matches('input,textarea,select')&&active.closest('form'));
  }

  async function api(path,options={}){
    const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),15000);
    try{
      const response=await fetch(`/government-v127/api/${path}`,{cache:'no-store',...options,signal:controller.signal,headers:{...headers,...(options.headers||{})}});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      return data;
    }catch(error){if(error.name==='AbortError')throw new Error('Сервер долго не отвечает.');throw error}
    finally{clearTimeout(timeout)}
  }

  async function load(silent=false){
    if(busy&&!silent)return;
    captureDrafts();
    try{
      state=await api(`state?chat_id=${encodeURIComponent(chatId)}`);
      render();restoreDrafts();$('loading').classList.add('hidden');
    }catch(error){$('loading').classList.add('hidden');toast(error.message||'Не удалось загрузить государство.','error')}
  }

  async function action(name,payload={},confirmText=''){
    if(busy)return false;
    if(confirmText&&!confirm(confirmText))return false;
    captureDrafts();busy=true;
    try{
      const data=await api('action',{method:'POST',body:JSON.stringify({action:name,chat_id:chatId,...payload})});
      toast(data.message||'Готово.');tg?.HapticFeedback?.notificationOccurred?.('success');await load(true);return true;
    }catch(error){toast(error.message||'Действие не выполнено.','error');tg?.HapticFeedback?.notificationOccurred?.('error');return false}
    finally{busy=false}
  }

  function officeLabel(keys){
    if(!keys?.length)return 'Государственной должности нет';
    return keys.map(key=>state.office_specs?.[key]?.emoji+' '+state.office_specs?.[key]?.title).join(' · ');
  }

  function renderIdentity(){
    const user=state.user||{};
    $('chatTitle').textContent=state.chat?.title||String(state.chat?.chat_id||'');
    $('identity').innerHTML=`<div><b>${esc(user.name||'Участник')}</b><small>${esc(officeLabel(user.offices))}${user.sanctioned?' · 🚫 есть санкции':''}</small></div><strong>⭐ ${fmt(user.career_points)}<br>💰 ${fmt(user.points)}</strong>`;
  }

  function officeCard(spec,key,seat=1){
    const office=(state.offices||[]).find(x=>x.office_key===key&&Number(x.seat_no)===Number(seat));
    if(!office)return `<article class="office-card vacant"><div class="office-title"><span>${spec.emoji}</span><div><b>${esc(spec.title)}${spec.seats>1?` · место ${seat}`:''}</b><small>Порог: ${fmt(spec.threshold)} карьеры</small></div></div><div class="office-person">Должность свободна</div><div class="office-meta">Можно провести выборы или назначение согласно государственным правилам.</div></article>`;
    return `<article class="office-card"><div class="office-title"><span>${office.emoji}</span><div><b>${esc(office.title)}${spec.seats>1?` · место ${office.seat_no}`:''}</b><small>Полномочия: ещё ${esc(office.remaining)}</small></div></div><div class="office-person">${esc(office.name)}</div><div class="office-meta">⭐ ${fmt(office.career_points)} · доверие ${fmt(office.trust)}%</div><div class="trust"><i style="width:${Math.max(0,Math.min(100,office.trust))}%"></i></div></article>`;
  }

  function renderHome(){
    const president=(state.offices||[]).find(x=>x.office_key==='president');
    const deputySeats=Number(state.office_specs?.deputy?.seats)||5;
    $('homeHero').innerHTML=`<article class="hero"><div class="hero-head"><div class="hero-icon">${president?'🦅':'🏛'}</div><div><small>${president?'ПРЕЗИДЕНТ РЕАЛЬНОСТИ':'ГОСУДАРСТВО ФОРМИРУЕТСЯ'}</small><b>${esc(president?.name||'Президент ещё не избран')}</b></div></div><div class="metric-grid"><div class="metric"><small>КАЗНА</small><b>${fmt(state.treasury?.balance)} 💰</b></div><div class="metric"><small>ДЕЙСТВУЮЩИЕ ЗАКОНЫ</small><b>${(state.laws||[]).filter(x=>x.active).length}</b></div><div class="metric"><small>ДЕПУТАТЫ</small><b>${(state.offices||[]).filter(x=>x.office_key==='deputy').length}/${deputySeats}</b></div><div class="metric"><small>НАЛОГОВЫЙ ЦИКЛ</small><b>${state.tax?.enabled?'ВКЛЮЧЁН':'ВЫКЛЮЧЕН'}</b></div></div></article>`;
    const order=['president','chair','deputy','finance','oversight'];
    $('officeGrid').innerHTML=order.map(key=>{const spec=state.office_specs[key];return Array.from({length:Number(spec.seats)||1},(_,i)=>officeCard(spec,key,i+1)).join('')}).join('');
    const activeE=(state.elections||[]).filter(x=>['nomination','voting'].includes(x.phase));
    const activeB=(state.bills||[]).filter(x=>['voting','president_review','vetoed'].includes(x.status));
    const items=[...activeE.map(x=>`<div class="log-item"><span><b>${x.emoji} Выборы: ${esc(x.office_title)}</b><small>${x.phase==='nomination'?'Выдвижение':'Голосование'} · ${esc(x.remaining)}</small></span><strong>${x.candidates.length}</strong></div>`),...activeB.map(x=>`<div class="log-item"><span><b>${x.emoji} Законопроект №${x.number}</b><small>${esc(x.title)} · ${statusTitle(x.status)}</small></span><strong>${x.votes.yes}/${x.votes.no}</strong></div>`)];
    $('activeProcesses').innerHTML=items.length?`<div class="log-list">${items.join('')}</div>`:'<div class="empty">Активных выборов и законопроектов сейчас нет.</div>';
  }

  function renderElectionControls(){
    const p=state.permissions||{};const active=(state.elections||[]).filter(x=>['nomination','voting'].includes(x.phase));
    const has=key=>active.some(x=>x.office_key===key);const buttons=[];
    if(p.can_start_president&&!has('president'))buttons.push('<button class="action" data-start-election="president">🦅 Выборы президента</button>');
    if(p.can_start_deputy&&!has('deputy'))buttons.push('<button class="action" data-start-election="deputy">🗳 Выборы депутатов</button>');
    if(p.can_start_chair&&!has('chair'))buttons.push('<button class="secondary" data-start-election="chair">🏛 Выборы председателя</button>');
    const scale=state.government_scale||{};
    const note=scale.active_users?`<p class="hint">Активных за ${fmt(scale.activity_window_days||14)} дней: ${fmt(scale.active_users)}. Депутатских мест: ${fmt(scale.deputy_seats)}. Кворум: ${fmt(scale.quorum)}.</p>`:'';
    $('electionControls').innerHTML=buttons.length?`<article class="panel"><div class="panel-title"><span>🗳</span><div><b>Открыть избирательную кампанию</b><small>Выдвижение 24 часа, затем голосование 24 часа</small></div></div>${note}<div class="button-grid">${buttons.join('')}</div></article>`:'';
  }

  function electionCard(election){
    const phase=election.phase==='nomination'?'ВЫДВИЖЕНИЕ':election.phase==='voting'?'ГОЛОСОВАНИЕ':election.phase==='resolved'?'ЗАВЕРШЕНО':'ОТМЕНЕНО';
    const canNominate=election.phase==='nomination';
    const candidates=election.candidates?.length?`<div class="candidate-list">${election.candidates.map(c=>`<div class="candidate"><span><b>${esc(c.name)}</b><small>⭐ ${fmt(c.career_points)} · ${esc(c.program)}</small></span>${election.phase==='voting'?`<button class="${Number(election.my_vote)===Number(c.user_id)?'selected':''}" data-vote-election="${esc(election.election_id)}" data-candidate="${c.user_id}">${Number(election.my_vote)===Number(c.user_id)?'✓ ВЫБРАН':'ГОЛОСОВАТЬ'}${state.user?.is_admin?` · ${c.votes}`:''}</button>`:`<strong>${state.user?.is_admin?c.votes:''}</strong>`}</div>`).join('')}</div>`:'<div class="empty">Кандидатов пока нет.</div>';
    const nominate=canNominate?`<form class="nominate-form" data-election="${esc(election.election_id)}"><div class="field"><label>ПРОГРАММА КАНДИДАТА</label><textarea name="program" maxlength="600" placeholder="Что ты изменишь за семь дней?"></textarea><small class="hint">Черновик сохраняется автоматически и не исчезнет при обновлении.</small></div><button class="action wide" type="submit">📣 ВЫДВИНУТЬ СВОЮ КАНДИДАТУРУ</button></form>`:'';
    return `<article class="election-card"><div class="card-head"><div><b>${election.emoji} ${esc(election.office_title)}</b><small>${election.seats} мест · осталось ${esc(election.remaining)}</small></div><span class="badge gold">${phase}</span></div>${candidates}${nominate}</article>`;
  }

  function renderElections(){
    renderElectionControls();const rows=state.elections||[];const seats=Number(state.office_specs?.deputy?.seats)||3;
    $('electionList').innerHTML=rows.length?rows.map(electionCard).join(''):`<div class="empty">Выборов ещё не проводилось. Начни с президента и ${seats} депутатов.</div>`;
  }

  function userOptions(selected=0){return (state.eligible_users||[]).map(u=>`<option value="${u.user_id}" ${Number(selected)===Number(u.user_id)?'selected':''}>${esc(u.name)} · ⭐ ${fmt(u.career_points)}</option>`).join('')}

  function billExtra(type){
    if(type==='tax_policy')return `<div class="inline-fields"><div class="field"><label>0–10 000, %</label><input name="rate_1" type="number" min="0" max="30" value="${state.tax.rate_1}"></div><div class="field"><label>10–50 тыс., %</label><input name="rate_2" type="number" min="0" max="30" value="${state.tax.rate_2}"></div><div class="field"><label>50–200 тыс., %</label><input name="rate_3" type="number" min="0" max="30" value="${state.tax.rate_3}"></div><div class="field"><label>Свыше 200 тыс., %</label><input name="rate_4" type="number" min="0" max="30" value="${state.tax.rate_4}"></div></div><div class="field"><label>МАКСИМАЛЬНЫЙ НАЛОГ</label><input name="max_tax" type="number" min="0" value="${state.tax.max_tax}"></div>`;
    if(type==='budget')return `<div class="field"><label>ПОЛУЧАТЕЛЬ</label><select name="target_user_id">${userOptions()}</select></div><div class="field"><label>СУММА ИЗ КАЗНЫ</label><input name="amount" type="number" min="1" max="1000000" value="1000"></div>`;
    if(type==='appointment')return `<div class="field"><label>ДОЛЖНОСТЬ</label><select name="office_key"><option value="finance">💰 Министр финансов</option><option value="oversight">🚨 Глава Надзора</option></select></div><div class="field"><label>КАНДИДАТ</label><select name="target_user_id">${userOptions()}</select></div>`;
    return '';
  }

  function renderBillComposer(){
    if(!state.permissions?.can_create_bill){$('billComposer').innerHTML='<div class="empty">Вносить законопроекты могут президент, председатель, депутаты, министр финансов и глава Надзора.</div>';return}
    $('billComposer').innerHTML=`<article class="panel"><div class="panel-title"><span>📜</span><div><b>Новый законопроект</b><small>После публикации депутаты голосуют 12 часов</small></div></div><form id="billForm"><div class="field"><label>ТИП ДОКУМЕНТА</label><select name="bill_type" id="billType"><option value="general">📜 Обычный закон</option><option value="tax_policy">🏦 Налоговая политика</option><option value="budget">💸 Бюджетная выплата</option><option value="appointment">🎖 Назначение чиновника</option></select></div><div class="field"><label>НАЗВАНИЕ</label><input name="title" maxlength="120" placeholder="О чём закон"></div><div class="field"><label>ОПИСАНИЕ</label><textarea name="description" maxlength="1200" placeholder="Что изменится и зачем"></textarea></div><div id="billExtra"></div><button class="action wide" type="submit">🏛 ВНЕСТИ В ГОСДУМУ</button></form></article>`;
    $('billExtra').innerHTML=billExtra('general');
  }

  function statusTitle(status){return ({voting:'голосование',president_review:'у президента',vetoed:'вето',enacted:'принят',rejected:'отклонён',expired:'срок истёк'})[status]||status}
  function statusBadge(status){const cls=status==='enacted'?'green':status==='rejected'||status==='vetoed'?'red':'gold';return `<span class="badge ${cls}">${esc(statusTitle(status).toUpperCase())}</span>`}

  function billCard(bill){
    const voteButtons=bill.status==='voting'&&state.permissions?.can_vote_bill?`<div class="vote-row"><button class="yes ${bill.my_vote==='yes'?'active':''}" data-vote-bill="${esc(bill.bill_id)}" data-vote="yes">✅ ЗА</button><button class="no ${bill.my_vote==='no'?'active':''}" data-vote-bill="${esc(bill.bill_id)}" data-vote="no">❌ ПРОТИВ</button><button class="${bill.my_vote==='abstain'?'active':''}" data-vote-bill="${esc(bill.bill_id)}" data-vote="abstain">⚪ ВОЗДЕРЖАТЬСЯ</button></div>`:'';
    const president=bill.status==='president_review'&&state.permissions?.can_president?`<div class="button-grid"><button class="positive" data-president="sign" data-bill="${esc(bill.bill_id)}">✍️ ПОДПИСАТЬ</button><button class="danger" data-president="veto" data-bill="${esc(bill.bill_id)}">🛑 НАЛОЖИТЬ ВЕТО</button></div>`:'';
    const override=bill.status==='vetoed'&&state.permissions?.can_chair?`<button class="action wide" data-override="${esc(bill.bill_id)}">🏛 ПРЕОДОЛЕТЬ ВЕТО</button>`:'';
    return `<article class="bill-card"><div class="card-head"><div><b>${bill.emoji} Законопроект №${bill.number}</b><small>${esc(bill.type_title)} · автор ${esc(bill.author_name)}${bill.remaining?` · ${esc(bill.remaining)}`:''}</small></div>${statusBadge(bill.status)}</div><h3>${esc(bill.title)}</h3><p class="bill-text">${esc(bill.description)}</p><div class="vote-stats"><span>✅ За: <b>${bill.votes.yes}</b></span><span>❌ Против: <b>${bill.votes.no}</b></span><span>⚪ ${bill.votes.abstain}</span></div>${voteButtons}${president}${override}</article>`;
  }

  function renderDuma(){renderBillComposer();const bills=(state.bills||[]).filter(x=>x.bill_type!=='sanction');$('billList').innerHTML=bills.length?bills.map(billCard).join(''):'<div class="empty">Законопроектов пока нет.</div>'}
  function renderLaws(){const laws=state.laws||[];$('lawList').innerHTML=laws.length?laws.map(law=>`<article class="law-card"><div class="card-head"><div><b>${law.emoji} Закон №${law.number}</b><small>${esc(law.type_title)} · ${date(law.enacted_at)}</small></div><span class="badge green">ДЕЙСТВУЕТ</span></div><h3>${esc(law.title)}</h3><p class="law-text">${esc(law.text)}</p></article>`).join(''):'<div class="empty">Кодекс пока пуст. Первый закон появится после голосования Госдумы и подписи президента.</div>'}

  function renderTreasury(){
    const tax=state.tax||{},treasury=state.treasury||{};
    $('treasuryHero').innerHTML=`<article class="hero"><div class="hero-head"><div class="hero-icon">💰</div><div><small>КАЗНА БЕСЕДЫ</small><b>${fmt(treasury.balance)} влияния</b></div></div><div class="metric-grid"><div class="metric"><small>НАЛОГОВЫЙ ДОЛГ</small><b>${fmt(tax.total_debt)}</b></div><div class="metric"><small>ДОЛЖНИКОВ</small><b>${fmt(tax.debtors)}</b></div><div class="metric"><small>МОЙ ДОЛГ</small><b>${fmt(tax.my_debt)}</b></div><div class="metric"><small>СЛЕДУЮЩИЙ СБОР</small><b>${tax.enabled?esc(tax.next_tax_text):'ОТКЛЮЧЁН'}</b></div></div></article>`;
    const controls=state.permissions?.can_manage_tax?`<div class="button-grid"><button class="${tax.enabled?'danger':'positive'}" data-tax-toggle="${tax.enabled?'0':'1'}">${tax.enabled?'⏸ ОТКЛЮЧИТЬ АВТОСБОР':'▶ ВКЛЮЧИТЬ АВТОСБОР'}</button><button class="action" data-tax-run>🏦 ПРОВЕСТИ ПЕРИОД</button></div>`:'';
    const debtButton=Number(tax.my_debt)>0?'<button class="positive wide" data-pay-tax>🧾 ПОГАСИТЬ МОЙ НАЛОГОВЫЙ ДОЛГ</button>':'';
    $('taxPolicy').innerHTML=`<article class="panel"><div class="panel-title"><span>🏦</span><div><b>Налог на богатство</b><small>Списывается только обычное влияние</small></div></div><div class="tax-table"><div class="tax-tier"><small>ДО ${fmt(tax.wealth_1)}</small><b>${tax.rate_1}%</b></div><div class="tax-tier"><small>ДО ${fmt(tax.wealth_2)}</small><b>${tax.rate_2}%</b></div><div class="tax-tier"><small>ДО ${fmt(tax.wealth_3)}</small><b>${tax.rate_3}%</b></div><div class="tax-tier"><small>ВЫШЕ ${fmt(tax.wealth_3)}</small><b>${tax.rate_4}%</b></div></div><p class="hint">Максимум за один период: ${fmt(tax.max_tax)}. Ставки меняются только налоговым законом.</p>${controls}${debtButton}</article>`;
    const log=treasury.log||[];
    $('treasuryLog').innerHTML=`<article class="panel"><div class="panel-title"><span>📒</span><div><b>История казны</b><small>Налоги, выплаты и погашения задолженности</small></div></div><div class="log-list">${log.length?log.map(item=>`<div class="log-item"><span><b>${esc(item.reason)}</b><small>${date(item.created_at)} · ${esc(item.source_type)}</small></span><strong class="${item.delta>=0?'plus':'minus'}">${item.delta>0?'+':''}${fmt(item.delta)}</strong></div>`).join(''):'<div class="empty">Операций в казне пока нет.</div>'}</div></article>`;
  }

  function renderSanctionComposer(){
    if(!state.permissions?.can_propose_sanction){$('sanctionComposer').innerHTML='<div class="empty">Санкционное предложение может внести президент, глава Надзора или депутат.</div>';return}
    const types={gambling:'🎲 Азартные игры',miniapp:'🎮 Mini App',finance:'💸 Финансы',raid_event:'🌌 Рейд и события',tasks:'🎯 Задания',career_freeze:'⭐ Заморозка карьеры',full_game:'🔒 Полный игровой бан'};
    $('sanctionComposer').innerHTML=`<article class="panel"><div class="panel-title"><span>🚨</span><div><b>Предложить санкции</b><small>Решение проходит голосование Госдумы и подпись президента</small></div></div><form id="sanctionForm"><div class="field"><label>УЧАСТНИК</label><select name="target_user_id">${userOptions()}</select></div><div class="check-grid">${Object.entries(types).map(([key,title])=>`<label class="check"><input type="checkbox" name="sanction_type" value="${key}"><span>${title}</span></label>`).join('')}</div><div class="field"><label>СРОК</label><select name="duration"><option value="600">10 минут</option><option value="3600">1 час</option><option value="21600">6 часов</option><option value="86400" selected>24 часа</option><option value="259200">3 дня</option><option value="604800">7 дней</option><option value="0">Бессрочно</option></select></div><div class="field"><label>ПРИЧИНА</label><textarea name="reason" maxlength="500" placeholder="В чём установлено нарушение"></textarea></div><button class="danger wide" type="submit">🚨 ВНЕСТИ САНКЦИОННОЕ ПРЕДЛОЖЕНИЕ</button></form></article>`;
  }

  function renderOversight(){renderSanctionComposer();const bills=(state.bills||[]).filter(x=>x.bill_type==='sanction');$('sanctionBills').innerHTML=bills.length?bills.map(billCard).join(''):'<div class="empty">Санкционных предложений пока нет.</div>'}
  function render(){if(!state)return;renderIdentity();renderHome();renderElections();renderDuma();renderLaws();renderTreasury();renderOversight()}
  function formData(form){return Object.fromEntries(new FormData(form).entries())}

  document.addEventListener('click',event=>{
    const tab=event.target.closest('[data-tab]');
    if(tab){captureDrafts();document.querySelectorAll('.bottom-nav button').forEach(x=>x.classList.toggle('active',x===tab));document.querySelectorAll('.screen').forEach(x=>x.classList.toggle('active',x.dataset.screen===tab.dataset.tab));window.scrollTo({top:0,behavior:'smooth'});return}
    if(event.target.closest('#refreshButton')){load();return}
    const start=event.target.closest('[data-start-election]');if(start){action('start_election',{office_key:start.dataset.startElection},'Открыть выборы на эту должность?');return}
    const candidate=event.target.closest('[data-vote-election]');if(candidate){action('vote_election',{election_id:candidate.dataset.voteElection,candidate_id:Number(candidate.dataset.candidate)});return}
    const vote=event.target.closest('[data-vote-bill]');if(vote){action('vote_bill',{bill_id:vote.dataset.voteBill,vote:vote.dataset.vote});return}
    const president=event.target.closest('[data-president]');if(president){action('president_decision',{bill_id:president.dataset.bill,decision:president.dataset.president},president.dataset.president==='sign'?'Подписать закон и немедленно ввести его в силу?':'Наложить президентское вето?');return}
    const override=event.target.closest('[data-override]');if(override){action('override_veto',{bill_id:override.dataset.override},'Попытаться преодолеть президентское вето?');return}
    const toggle=event.target.closest('[data-tax-toggle]');if(toggle){action('tax_toggle',{enabled:toggle.dataset.taxToggle==='1'},'Изменить режим автоматического налогового сбора?');return}
    if(event.target.closest('[data-tax-run]')){action('tax_run',{},'Провести налоговый период сейчас и списать налог со всех участников?');return}
    if(event.target.closest('[data-pay-tax]')){action('pay_tax_debt',{},'Погасить налоговый долг с обычного баланса?');return}
  });

  document.addEventListener('input',event=>{if(event.target.closest('form'))captureDrafts()});
  document.addEventListener('change',event=>{
    if(event.target.id==='billType'&&$('billExtra')){$('billExtra').innerHTML=billExtra(event.target.value);captureDrafts();restoreDrafts();return}
    if(event.target.closest('form'))captureDrafts();
  });

  document.addEventListener('submit',event=>{
    if(event.target.matches('.nominate-form')){event.preventDefault();const data=formData(event.target);action('nominate',{election_id:event.target.dataset.election,program:data.program||''},'Подтвердить выдвижение кандидатуры?');return}
    if(event.target.id==='billForm'){
      event.preventDefault();const data=formData(event.target);const type=data.bill_type;const payload={};
      if(type==='tax_policy')Object.assign(payload,{rate_1:Number(data.rate_1),rate_2:Number(data.rate_2),rate_3:Number(data.rate_3),rate_4:Number(data.rate_4),wealth_1:10000,wealth_2:50000,wealth_3:200000,max_tax:Number(data.max_tax),enabled:true});
      if(type==='budget')Object.assign(payload,{target_user_id:Number(data.target_user_id),amount:Number(data.amount)});
      if(type==='appointment')Object.assign(payload,{target_user_id:Number(data.target_user_id),office_key:data.office_key});
      action('create_bill',{bill_type:type,title:data.title||'',description:data.description||'',payload},'Опубликовать законопроект в группе и открыть голосование?');return
    }
    if(event.target.id==='sanctionForm'){
      event.preventDefault();const data=formData(event.target);const types=[...event.target.querySelectorAll('input[name="sanction_type"]:checked')].map(x=>x.value);
      action('create_bill',{bill_type:'sanction',title:'О введении санкций',description:data.reason||'',payload:{target_user_id:Number(data.target_user_id),types,duration:Number(data.duration),reason:data.reason||''}},'Передать санкционное предложение на голосование Госдумы?');return
    }
  });

  document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!isEditing())load(true)});
  load();clearInterval(refreshTimer);refreshTimer=setInterval(()=>{if(!document.hidden&&!busy&&!isEditing())load(true)},60000);
})();