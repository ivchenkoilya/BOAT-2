(()=>{
  'use strict';
  if(window.__governmentElectionShadowV153)return;
  window.__governmentElectionShadowV153=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
  const organNames={finance:'Минфин',auditor:'Счётная палата',oversight:'Надзор',prosecutor:'Прокуратура',cec:'ЦИК',citizen_report:'Сообщение участника'};
  let state=null,activeElection='',busy=false,frame=0,timer=0,applying=false;

  function toast(text,type='success'){
    const node=document.getElementById('toast');if(!node)return;
    node.textContent=String(text||'Готово.');node.className=`toast show ${type}`;
    clearTimeout(node.__v153Timer);node.__v153Timer=setTimeout(()=>node.className='toast',3900);
  }

  async function api(action,payload={}){
    if(busy)return null;busy=true;
    try{
      const response=await fetch('/government-v153/api/action',{method:'POST',cache:'no-store',headers,body:JSON.stringify({action,chat_id:chatId,...payload})});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      toast(data.message||'Готово.');tg?.HapticFeedback?.notificationOccurred?.('success');await load();return data;
    }catch(error){toast(error?.message||'Действие не выполнено.','error');tg?.HapticFeedback?.notificationOccurred?.('error');return null}
    finally{busy=false}
  }

  function setHtml(node,html){if(node&&node.innerHTML!==html)node.innerHTML=html}

  function ensureUi(){
    const brand=document.querySelector('.brand small');if(brand&&brand.textContent!=='REALITY 153')brand.textContent='REALITY 153';
    const list=document.getElementById('electionList');
    if(list&&!document.getElementById('shadowElectionToolsV153'))list.insertAdjacentHTML('beforebegin','<div id="shadowElectionToolsV153"></div><div id="shadowOffersV153"></div><div id="shadowInvestigationsV153"></div>');
    const controls=document.getElementById('electionControls');
    if(controls&&!document.getElementById('shadowElectionAdminV153'))controls.insertAdjacentHTML('afterend','<div id="shadowElectionAdminV153"></div>');
    const theft=document.getElementById('crisisTheftLog');
    if(theft&&!document.getElementById('theftEvidenceV153'))theft.insertAdjacentHTML('afterend','<div id="theftEvidenceV153"></div>');
    if(!document.getElementById('shadowModalV153'))document.body.insertAdjacentHTML('beforeend','<div class="v153-modal" id="shadowModalV153" hidden><section class="v153-sheet"><button class="v153-close" data-v153-close>×</button><div id="shadowModalContentV153"></div></section></div>');
    document.querySelectorAll('button').forEach(button=>{if(String(button.textContent||'').includes('Предложить назначение'))button.classList.add('v153-obsolete-appointment')});
  }

  const officeOptions=()=> (state?.election_shadow_v153?.office_options||[]).map(item=>`<option value="${esc(item.office_key)}" data-seats="${Number(item.seats)||1}">${esc(item.emoji)} ${esc(item.title)}</option>`).join('');
  const userOptions=()=> (state?.eligible_users||[]).map(item=>`<option value="${Number(item.user_id)}">${esc(item.name)} · 💰 ${fmt(item.points)} · ⭐ ${fmt(item.career_points)}</option>`).join('');

  function updateSeatLimit(){
    const select=document.getElementById('appointmentOfficeV153'),input=document.getElementById('appointmentSeatV153');if(!select||!input)return;
    const seats=Math.max(1,Number(select.selectedOptions?.[0]?.dataset.seats)||1);input.max=String(seats);input.value=String(Math.min(seats,Math.max(1,Number(input.value)||1)));input.disabled=seats===1;
  }

  function renderAdmin(){
    const node=document.getElementById('shadowElectionAdminV153');if(!node||!state)return;
    const shadow=state.election_shadow_v153||{},blocks=[];
    if(shadow.can_presidential_appoint)blocks.push(`<article class="panel v153-admin-card president"><div class="panel-title"><span>🎖</span><div><b>Прямое назначение президента</b><small>Любой участник · любая государственная должность</small></div></div><form id="presidentialAppointmentV153"><div class="field"><label>УЧАСТНИК</label><select name="target_user_id">${userOptions()}</select></div><div class="v153-inline"><div class="field"><label>ДОЛЖНОСТЬ</label><select name="office_key" id="appointmentOfficeV153">${officeOptions()}</select></div><div class="field"><label>МЕСТО</label><input name="seat_no" id="appointmentSeatV153" type="number" min="1" value="1"></div></div><div class="field"><label>ОСНОВАНИЕ</label><textarea name="reason" maxlength="500" placeholder="Кадровое решение Президента реальности"></textarea></div><button class="action wide" type="submit">🎖 НАЗНАЧИТЬ НА ДОЛЖНОСТЬ</button></form></article>`);
    if(shadow.can_start_any_election)blocks.push(`<article class="panel v153-admin-card cec"><div class="panel-title"><span>🗳</span><div><b>Выборы на любую должность</b><small>Полномочие ЦИК и создателя системы</small></div></div><form id="startAnyElectionV153"><div class="field"><label>ДОЛЖНОСТЬ</label><select name="office_key">${officeOptions()}</select></div><button class="secondary wide" type="submit">🗳 ОТКРЫТЬ ВЫДВИЖЕНИЕ</button></form></article>`);
    setHtml(node,blocks.join(''));updateSeatLimit();
  }

  function renderIncoming(){
    const node=document.getElementById('shadowOffersV153');if(!node||!state)return;
    const offers=(state.election_shadow_v153?.incoming_offers||[]).filter(item=>['pending','accepted','reported'].includes(item.status));
    if(!offers.length){setHtml(node,'');return}
    const html=`<div class="section-head v153-section-head"><div><small>ТЕНЕВАЯ КАМПАНИЯ</small><h2>Тайные предложения</h2></div><div class="v153-mask">🕴</div></div><div class="v153-offer-list">${offers.map(item=>{const buttons=item.can_accept?`<div class="v153-offer-actions"><button class="positive" data-bribe-accept="${esc(item.offer_id)}">✅ ПРИНЯТЬ И ОТДАТЬ ГОЛОС</button><button class="secondary" data-bribe-decline="${esc(item.offer_id)}">ОТКЛОНИТЬ</button><button class="danger" data-bribe-report="${esc(item.offer_id)}">🚨 ПЕРЕДАТЬ В ЦИК</button></div>`:'';const reveal=item.buyer_revealed?`<p class="v153-reveal">После завершения раскрыт кандидат: Telegram ID ${Number(item.buyer_revealed)}</p>`:'';return `<article class="panel v153-offer ${esc(item.status)}"><div class="panel-title"><span>💵</span><div><b>Неизвестный кандидат предлагает ${fmt(item.amount)}</b><small>Выборы: ${esc(item.office_title)} · ${esc(item.status_title)}</small></div></div><p>При принятии голос автоматически уйдёт скрытому кандидату и будет заблокирован до конца выборов.</p><div class="v153-offer-meta"><span>Истекает: ${date(item.expires_at)}</span><b>${esc(item.remaining)}</b></div>${buttons}${reveal}</article>`}).join('')}</div>`;
    setHtml(node,html);
  }

  const campaignFor=id=>(state?.election_shadow_v153?.campaigns||[]).find(item=>String(item.election_id)===String(id));
  function decorateCards(){
    const cards=[...document.querySelectorAll('#electionList>.election-card')];
    (state?.elections||[]).forEach((election,index)=>{
      const card=cards[index];if(!card)return;
      card.querySelectorAll('.v153-campaign-box,.v153-secret-lock').forEach(node=>node.remove());
      const mine=(election.candidates||[]).some(candidate=>Number(candidate.user_id)===Number(state.user?.user_id));
      if(election.secret_vote_locked)card.insertAdjacentHTML('beforeend','<div class="v153-secret-lock">🔒 Твой голос передан тайному кандидату. Личность заказчика скрыта до завершения выборов.</div>');
      if(election.phase!=='voting'||!mine)return;
      const campaign=campaignFor(election.election_id);
      card.insertAdjacentHTML('beforeend',`<div class="v153-campaign-box"><div><small>ТЕНЕВАЯ КАМПАНИЯ КАНДИДАТА</small><b>${campaign?`Принято ${fmt(campaign.accepted)} · потрачено ${fmt(campaign.spent)}`:'Предложений пока нет'}</b></div><button class="v153-buy-vote" data-buy-vote="${esc(election.election_id)}">🕴 КУПИТЬ ГОЛОС</button></div>`);
    });
  }

  function evidenceList(items){return items?.length?`<div class="v153-evidence-list">${items.map(item=>`<div><span>${esc(organNames[item.office_key]||item.office_key)}</span><p>${esc(item.clue)}</p><b>+${Number(item.points)}</b></div>`).join('')}</div>`:'<div class="v153-no-evidence">Улик пока нет.</div>'}
  function investigationButtons(item,action,idKey){const offices=item.can_investigate_offices||[];return offices.length?`<div class="v153-investigate-actions">${offices.map(office=>`<button data-v153-investigate="${action}" data-id="${esc(item[idKey])}" data-office="${esc(office)}">🔍 ${esc(organNames[office]||office)}</button>`).join('')}</div>`:''}

  function renderBriberyCases(){
    const node=document.getElementById('shadowInvestigationsV153');if(!node||!state)return;
    const rows=(state.election_shadow_v153?.bribery_investigations||[]).filter(item=>(item.can_investigate_offices||[]).length||state.user?.is_admin);
    if(!rows.length){setHtml(node,'');return}
    setHtml(node,`<div class="section-head v153-section-head"><div><small>ЦИК И СЛЕДСТВИЕ</small><h2>Дела о покупке голосов</h2></div></div><div class="v153-case-list">${rows.map(item=>`<article class="panel v153-case"><div class="panel-title"><span>🚨</span><div><b>Тайное предложение ${fmt(item.amount)}</b><small>Личность заказчика скрыта</small></div></div><div class="v153-progress"><span style="width:${Math.min(100,Number(item.points)/Number(item.required)*100)}%"></span></div><div class="v153-case-metrics"><b>${fmt(item.points)}/${fmt(item.required)} доказательств</b><span>${fmt(item.organs)}/${fmt(item.organs_required)} структур</span></div>${evidenceList(item.evidence)}${investigationButtons(item,'bribe_investigate','offer_id')}</article>`).join('')}</div>`);
  }

  function renderTheftCases(){
    const node=document.getElementById('theftEvidenceV153');if(!node||!state)return;
    document.querySelectorAll('#crisisTheftLog [data-investigate]').forEach(button=>button.classList.add('v153-hidden-old-investigation'));
    const rows=state.election_shadow_v153?.theft_cases||[];
    if(!rows.length){setHtml(node,'');return}
    setHtml(node,`<div class="section-head v153-section-head"><div><small>МНОГОЭТАПНОЕ СЛЕДСТВИЕ</small><h2>Доказательства по казне</h2></div></div><div class="v153-case-list">${rows.map(item=>`<article class="panel v153-case theft"><div class="panel-title"><span>🧾</span><div><b>Дело о хищении ${fmt(item.amount)}</b><small>${fmt(item.percent)}% казны · следы исчезнут через ${esc(item.remaining)}</small></div></div><div class="v153-progress"><span style="width:${Math.min(100,Number(item.points)/Number(item.required)*100)}%"></span></div><div class="v153-case-metrics"><b>${fmt(item.points)}/${fmt(item.required)} доказательств</b><span>${fmt(item.organs)}/${fmt(item.organs_required)} структур</span></div>${evidenceList(item.evidence)}${investigationButtons(item,'theft_investigate_v153','theft_id')}</article>`).join('')}</div>`);
  }

  function openBuyModal(electionId){
    const election=(state?.elections||[]).find(item=>String(item.election_id)===String(electionId));if(!election)return;
    activeElection=String(electionId);const modal=document.getElementById('shadowModalV153'),host=document.getElementById('shadowModalContentV153');if(!modal||!host)return;
    host.innerHTML=`<div class="v153-modal-icon">🕴</div><small>ТЕНЕВАЯ ИЗБИРАТЕЛЬНАЯ КАМПАНИЯ</small><h2>Купить голос</h2><p>Получатель увидит только сумму и название выборов. Имя кандидата останется скрытым.</p><form id="buyVoteFormV153"><div class="field"><label>ПОЛУЧАТЕЛЬ ПРЕДЛОЖЕНИЯ</label><select name="target_user_id">${userOptions()}</select></div><div class="field"><label>СУММА · 1 000–500 000</label><input name="amount" type="number" min="1000" max="500000" step="1000" value="10000"></div><button class="v153-buy-confirm wide" type="submit">💵 ОТПРАВИТЬ ТАЙНОЕ ПРЕДЛОЖЕНИЕ</button></form><div class="v153-warning">Предложение действует один час. При принятии голос будет автоматически отдан тебе и заблокирован.</div>`;
    modal.hidden=false;document.body.classList.add('v153-modal-open');
  }
  function closeModal(){const modal=document.getElementById('shadowModalV153');if(modal)modal.hidden=true;document.body.classList.remove('v153-modal-open');activeElection=''}

  function render(){
    if(applying)return;applying=true;
    try{ensureUi();renderAdmin();renderIncoming();renderBriberyCases();renderTheftCases();decorateCards()}
    finally{setTimeout(()=>{applying=false},0)}
  }
  function schedule(){if(applying)return;cancelAnimationFrame(frame);frame=requestAnimationFrame(render)}
  async function load(){
    if(!chatId)return;
    try{const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}`,{cache:'no-store',headers});const data=await response.json();if(!response.ok||!data?.ok)return;state=data;schedule()}catch(_error){}
  }

  document.addEventListener('click',event=>{
    const buy=event.target.closest?.('[data-buy-vote]');if(buy){openBuyModal(buy.dataset.buyVote);return}
    if(event.target.closest?.('[data-v153-close]')||event.target.id==='shadowModalV153'){closeModal();return}
    const accept=event.target.closest?.('[data-bribe-accept]');if(accept&&confirm('Принять деньги и безвозвратно отдать голос неизвестному кандидату?')){api('bribe_accept',{offer_id:accept.dataset.bribeAccept});return}
    const decline=event.target.closest?.('[data-bribe-decline]');if(decline){api('bribe_decline',{offer_id:decline.dataset.bribeDecline});return}
    const report=event.target.closest?.('[data-bribe-report]');if(report&&confirm('Передать тайное предложение в ЦИК как доказательство?')){api('bribe_report',{offer_id:report.dataset.bribeReport});return}
    const investigate=event.target.closest?.('[data-v153-investigate]');if(investigate){const key=investigate.dataset.v153Investigate==='bribe_investigate'?'offer_id':'theft_id';api(investigate.dataset.v153Investigate,{[key]:investigate.dataset.id,office_key:investigate.dataset.office});return}
    if(event.target.closest?.('#refreshButton,[data-tab="elections"],[data-tab="powers"]'))setTimeout(load,180);
  },true);
  document.addEventListener('change',event=>{if(event.target.id==='appointmentOfficeV153')updateSeatLimit()},true);
  document.addEventListener('submit',event=>{
    if(event.target.id==='buyVoteFormV153'){event.preventDefault();const data=Object.fromEntries(new FormData(event.target).entries());api('bribe_create',{election_id:activeElection,target_user_id:Number(data.target_user_id),amount:Number(data.amount)}).then(result=>{if(result)closeModal()});return}
    if(event.target.id==='presidentialAppointmentV153'){event.preventDefault();const data=Object.fromEntries(new FormData(event.target).entries());if(confirm('Назначить выбранного участника на государственную должность напрямую?'))api('presidential_appoint',{target_user_id:Number(data.target_user_id),office_key:data.office_key,seat_no:Number(data.seat_no)||1,reason:data.reason||''});return}
    if(event.target.id==='startAnyElectionV153'){event.preventDefault();const data=Object.fromEntries(new FormData(event.target).entries());if(confirm('Открыть выборы на выбранную должность?'))api('start_any_election',{office_key:data.office_key})}
  },true);

  const observer=new MutationObserver(()=>{if(!applying)schedule()});observer.observe(document.documentElement,{subtree:true,childList:true});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)load()});window.addEventListener('focus',load);
  ensureUi();load();clearInterval(timer);timer=setInterval(()=>{if(!document.hidden)load()},20000);
})();
