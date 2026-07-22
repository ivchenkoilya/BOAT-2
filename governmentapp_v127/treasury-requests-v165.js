(()=>{
  'use strict';
  if(window.__governmentTreasuryRequestsV165)return;
  window.__governmentTreasuryRequestsV165=true;
  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
  let state=null,loading=false,draft=null,brandObserver=null;

  function markVersion(){
    const brand=document.querySelector('.brand small');
    if(!brand)return;
    if(brand.textContent!=='REALITY 165')brand.textContent='REALITY 165';
    if(!brandObserver){
      brandObserver=new MutationObserver(()=>{if(brand.textContent!=='REALITY 165')brand.textContent='REALITY 165'});
      brandObserver.observe(brand,{childList:true,subtree:true,characterData:true});
    }
  }
  function toast(text,type='success'){
    const node=document.getElementById('toast');if(!node)return;
    node.textContent=String(text||'Готово.');node.className=`toast show ${type}`;
    clearTimeout(node.__tr165Timer);node.__tr165Timer=setTimeout(()=>node.className='toast',3800);
  }
  async function api(path,options={}){
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
    try{
      const response=await fetch(path,{cache:'no-store',...options,signal:controller.signal,headers:{...headers,...(options.headers||{})}});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      return data;
    }catch(error){if(error.name==='AbortError')throw new Error('Сервер долго не отвечает.');throw error}
    finally{clearTimeout(timeout)}
  }
  function ensureMount(){
    let node=document.getElementById('treasuryRequestsV165');if(node)return node;
    const management=document.getElementById('treasuryManagementV164');
    const hero=document.getElementById('treasuryHero');
    if(!management&&!hero)return null;
    node=document.createElement('div');node.id='treasuryRequestsV165';node.className='treasury-requests-v165';
    (management||hero).insertAdjacentElement('afterend',node);return node;
  }
  function captureDraft(){
    const form=document.getElementById('treasuryRequestFormV165');
    if(form)draft=Object.fromEntries(new FormData(form).entries());
  }
  function restoreDraft(){
    if(!draft)return;
    const form=document.getElementById('treasuryRequestFormV165');if(!form)return;
    for(const [key,value] of Object.entries(draft)){
      const field=form.elements.namedItem(key);if(field)field.value=String(value??'');
    }
  }
  function statusTitle(item){
    if(item.status==='pending')return 'ОЖИДАЕТ ПРЕЗИДЕНТА';
    if(item.status==='processing')return 'РАССМАТРИВАЕТСЯ';
    if(item.status==='approved')return 'ВЫПЛАЧЕНО';
    if(item.status==='sent_to_duma')return `ПЕРЕДАНО В ГОСДУМУ${item.bill_number?` · №${item.bill_number}`:''}`;
    if(item.status==='rejected')return 'ОТКЛОНЕНО';
    if(item.status==='withdrawn')return 'ОТОЗВАНО';
    return String(item.status||'');
  }
  function statusClass(status){
    if(status==='approved')return 'green';
    if(status==='rejected'||status==='withdrawn')return 'red';
    return 'gold';
  }
  function requestCard(item,canReview,selfId){
    const pending=item.status==='pending',mine=Number(item.requester_id)===Number(selfId);
    const actions=pending?`<div class="treasury-request-actions-v165">
      ${canReview?`<button class="positive" data-request-approve="${esc(item.request_id)}">✅ ОДОБРИТЬ</button><button class="danger" data-request-reject="${esc(item.request_id)}">❌ ОТКЛОНИТЬ</button>`:''}
      ${mine?`<button class="secondary" data-request-withdraw="${esc(item.request_id)}">↩ ОТОЗВАТЬ</button>`:''}
    </div>`:'';
    const review=item.review_reason?`<div class="treasury-request-review-v165"><b>Решение:</b> ${esc(item.review_reason)}</div>`:'';
    const bill=item.bill_id?`<small>Госдума: ${item.bill_number?`законопроект №${item.bill_number}`:'бюджетный проект'}${item.bill_status?` · ${esc(item.bill_status)}`:''}</small>`:'';
    return `<article class="treasury-request-card-v165 ${item.priority==='urgent'?'urgent':''}">
      <div class="card-head">
        <div><b>${item.structure_emoji} ${esc(item.structure_title)}</b><small>${item.office_emoji} ${esc(item.requester_name)} · ${esc(item.office_title)} · ${date(item.created_at)}</small>${bill}</div>
        <span class="badge ${statusClass(item.status)}">${esc(statusTitle(item))}</span>
      </div>
      <div class="treasury-request-amount-v165">${fmt(item.amount)} влияния</div>
      <p>${esc(item.reason)}</p>
      <div class="treasury-request-meta-v165"><span>${item.priority==='urgent'?'🔥 СРОЧНЫЙ':'📌 ОБЫЧНЫЙ'} ЗАПРОС</span>${item.reviewer_name?`<span>Решение: ${esc(item.reviewer_name)}</span>`:''}</div>
      ${review}${actions}
    </article>`;
  }
  function render(){
    const mount=ensureMount();if(!mount||!state)return;
    captureDraft();
    const tr=state.treasury_requests_v165||{};
    const requestable=Array.isArray(tr.requestable_structures)?tr.requestable_structures:[];
    const pending=Array.isArray(tr.pending)?tr.pending:[];
    const recent=Array.isArray(tr.recent)?tr.recent:[];
    const selfId=Number(state.user?.user_id)||0;
    const canRequest=Boolean(tr.can_request),canReview=Boolean(tr.can_review);
    const requestForm=canRequest?`
      <article class="panel treasury-request-form-panel-v165">
        <div class="panel-title"><span>🏛</span><div><b>Запросить деньги из казны</b><small>Запрос поступит президенту; крупная сумма после одобрения уйдёт в Госдуму</small></div></div>
        <form id="treasuryRequestFormV165">
          <div class="field"><label>СТРУКТУРА</label><select name="structure_key">${requestable.map(item=>`<option value="${esc(item.key)}">${item.emoji} ${esc(item.title)} · баланс ${fmt(item.balance)}</option>`).join('')}</select></div>
          <div class="inline-fields">
            <div class="field"><label>СУММА</label><input name="amount" type="number" min="1" max="1000000" value="${esc(draft?.amount||100)}"></div>
            <div class="field"><label>ПРИОРИТЕТ</label><select name="priority"><option value="normal">📌 Обычный</option><option value="urgent">🔥 Срочный</option></select></div>
          </div>
          <div class="field"><label>ОБОСНОВАНИЕ</label><textarea name="reason" minlength="10" maxlength="500" placeholder="Для какой государственной задачи нужны деньги">${esc(draft?.reason||'')}</textarea></div>
          <button class="action wide" type="submit">📨 ОТПРАВИТЬ ЗАПРОС ПРЕЗИДЕНТУ</button>
        </form>
      </article>`:requestable.length?`<div class="treasury-request-warning-v165">🚫 Активные санкции временно запрещают вашей структуре подавать бюджетные запросы.</div>`:'';
    const reviewPanel=canReview?`
      <article class="panel treasury-review-panel-v165">
        <div class="panel-title"><span>🦅</span><div><b>Запросы на решение президента</b><small>Одобрение исполняется сразу в пределах лимита или автоматически передаётся в Госдуму</small></div></div>
        <div class="treasury-request-list-v165">${pending.length?pending.map(item=>requestCard(item,true,selfId)).join(''):'<div class="empty">Новых запросов от государственных структур нет.</div>'}</div>
      </article>`:'';
    mount.innerHTML=`${requestForm}${reviewPanel}
      <article class="panel">
        <div class="panel-title"><span>📚</span><div><b>Реестр запросов госструктур</b><small>Запросы, решения президента и передача бюджетов в Госдуму</small></div></div>
        <div class="treasury-request-list-v165">${recent.length?recent.map(item=>requestCard(item,false,selfId)).join(''):'<div class="empty">Государственные структуры ещё не запрашивали финансирование.</div>'}</div>
      </article>`;
    restoreDraft();markVersion();
  }
  async function load(){
    if(!chatId||loading)return;loading=true;
    try{
      state=await api(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_tr165=${Date.now()}`);
      render();
    }catch(error){toast(error.message||'Не удалось загрузить запросы казны.','error')}
    finally{loading=false;markVersion()}
  }
  async function post(payload,successText){
    try{
      const result=await api('/government-v165/api/action',{
        method:'POST',body:JSON.stringify({chat_id:chatId,...payload})
      });
      toast(result.message||successText||'Готово.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      document.getElementById('refreshButton')?.click();setTimeout(load,180);
    }catch(error){
      toast(error.message||'Действие не выполнено.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }
  }
  document.addEventListener('submit',event=>{
    if(event.target.id!=='treasuryRequestFormV165')return;
    event.preventDefault();captureDraft();
    const data=Object.fromEntries(new FormData(event.target).entries());
    post({
      action:'treasury_request_create',
      structure_key:String(data.structure_key||''),
      amount:Number(data.amount)||0,
      priority:String(data.priority||'normal'),
      reason:String(data.reason||'')
    },'Запрос отправлен.');
    draft=null;
  });
  document.addEventListener('click',event=>{
    if(event.target.closest?.('[data-tab="treasury"]'))setTimeout(load,100);
    if(event.target.closest?.('#refreshButton'))setTimeout(load,190);
    const approve=event.target.closest?.('[data-request-approve]');
    if(approve){
      if(confirm('Одобрить запрос? В пределах лимита деньги будут перечислены сразу, иначе решение уйдёт в Госдуму.')){
        post({action:'treasury_request_review',request_id:approve.dataset.requestApprove,decision:'approve'},'Запрос одобрен.');
      }
      return;
    }
    const reject=event.target.closest?.('[data-request-reject]');
    if(reject){
      const reason=prompt('Укажи причину отказа (минимум 5 символов):','Недостаточно обоснований');
      if(reason!==null)post({action:'treasury_request_review',request_id:reject.dataset.requestReject,decision:'reject',review_reason:reason},'Запрос отклонён.');
      return;
    }
    const withdraw=event.target.closest?.('[data-request-withdraw]');
    if(withdraw&&confirm('Отозвать этот запрос?')){
      post({action:'treasury_request_withdraw',request_id:withdraw.dataset.requestWithdraw},'Запрос отозван.');
    }
  },true);
  document.addEventListener('input',event=>{if(event.target.closest?.('#treasuryRequestFormV165'))captureDraft()});
  document.addEventListener('change',event=>{if(event.target.closest?.('#treasuryRequestFormV165'))captureDraft()});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)load()});
  window.addEventListener('focus',load);
  const mountObserver=new MutationObserver(()=>{if(!document.getElementById('treasuryRequestsV165'))ensureMount()});
  mountObserver.observe(document.documentElement,{childList:true,subtree:true});
  ensureMount();markVersion();load();setInterval(markVersion,500);
})();