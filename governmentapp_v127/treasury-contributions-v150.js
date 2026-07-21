(()=>{
  'use strict';
  if(window.__governmentTreasuryContributionsV150)return;
  window.__governmentTreasuryContributionsV150=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
  let state=null;
  let busy=false;
  let frame=0;

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=text;
    node.className=`toast show ${type}`;
    clearTimeout(node.__v150Timer);
    node.__v150Timer=setTimeout(()=>node.className='toast',3800);
  }

  function offices(){
    const access=state?.role_access?.offices;
    if(Array.isArray(access))return access;
    return Array.isArray(state?.user?.offices)?state.user.offices:[];
  }

  function canProposeWinTax(){
    return offices().some(role=>['president','finance','deputy'].includes(String(role)));
  }

  function winTaxFields(){
    const rate=Number(state?.tax?.win_rate)||0;
    return `<div class="field win-tax-field-v150"><label>НАЛОГ С ПОЛОЖИТЕЛЬНОГО ИГРОВОГО ВЫИГРЫША, %</label><input name="win_rate" type="number" min="0" max="100" value="${rate}"><p class="hint">От 0% до 100%. Закон вступит в силу после голосования депутатов и подписи президента.</p></div>`;
  }

  function ensureWinTaxOption(){
    const select=document.getElementById('billType');
    if(!select||!canProposeWinTax())return;
    let option=select.querySelector('option[value="win_tax"]');
    if(!option){
      option=document.createElement('option');
      option.value='win_tax';
      option.textContent='🎰 Налог на игровой выигрыш';
      const budget=select.querySelector('option[value="budget"]');
      select.insertBefore(option,budget||null);
    }
    option.hidden=false;
    option.disabled=false;
    if(select.value==='win_tax'){
      const extra=document.getElementById('billExtra');
      if(extra&&!extra.querySelector('[name="win_rate"]'))extra.innerHTML=winTaxFields();
    }
  }

  function contributionState(){
    return state?.treasury_contributions_v150||{};
  }

  function fundCards(data){
    const funds=Array.isArray(data.funds)?data.funds:[];
    return funds.map(fund=>`<article class="fund-card-v150"><span>${esc(fund.emoji)}</span><div><b>${esc(fund.title)}</b><small>${esc(fund.hint)}</small></div><strong>${fmt(fund.amount)}</strong></article>`).join('');
  }

  function topCards(data){
    const top=Array.isArray(data.top)?data.top:[];
    if(!top.length)return '<div class="empty">Первых меценатов пока нет.</div>';
    return `<div class="patron-list-v150">${top.map((item,index)=>`<div><span>${index===0?'🥇':index===1?'🥈':index===2?'🥉':`${index+1}.`}</span><b>${esc(item.name)}</b><strong>${fmt(item.amount)}</strong></div>`).join('')}</div>`;
  }

  function recentCards(data){
    const rows=Array.isArray(data.recent)?data.recent:[];
    if(!rows.length)return '<div class="empty">Добровольных вкладов пока не было.</div>';
    return `<div class="contribution-recent-v150">${rows.map(item=>`<div><span>${esc(item.fund_emoji)}</span><div><b>${esc(item.name)} · ${fmt(item.amount)}</b><small>${esc(item.fund_title)} · ${date(item.created_at)}${item.note?` · ${esc(item.note)}`:''}</small></div></div>`).join('')}</div>`;
  }

  function renderContributions(){
    const taxPolicy=document.getElementById('taxPolicy');
    if(!taxPolicy||!state)return;
    let host=document.getElementById('treasuryContributionV150');
    if(!host){
      host=document.createElement('section');
      host.id='treasuryContributionV150';
      taxPolicy.insertAdjacentElement('afterend',host);
    }
    const data=contributionState();
    const funds=Array.isArray(data.funds)?data.funds:[];
    const options=funds.map(fund=>`<option value="${esc(fund.key)}">${esc(fund.emoji)} ${esc(fund.title)}</option>`).join('');
    const disabled=data.can_contribute?'':'disabled';
    const reason=data.can_contribute?'Вклад сразу попадёт в казну и публичный журнал.':'Для вклада нужно минимум 100 обычного влияния.';
    host.innerHTML=`
      <article class="panel contribution-panel-v150">
        <div class="panel-title"><span>🤝</span><div><b>Внести вклад в государство</b><small>Добровольное пополнение казны без передачи денег лично чиновникам</small></div></div>
        <div class="contribution-summary-v150">
          <div><small>ВСЕГО ВНЕСЕНО</small><b>${fmt(data.total)}</b></div>
          <div><small>МОЙ ВКЛАД</small><b>${fmt(data.my_total)}</b></div>
          <div><small>МОЙ БАЛАНС</small><b>${fmt(data.available_balance)}</b></div>
        </div>
        <form id="treasuryContributionFormV150">
          <div class="field"><label>ГОСУДАРСТВЕННЫЙ ФОНД</label><select name="fund_key" ${disabled}>${options}</select></div>
          <div class="field"><label>СУММА ВКЛАДА</label><input name="amount" type="number" min="${Number(data.min_amount)||100}" max="${Number(data.max_amount)||1000000}" value="1000" ${disabled}></div>
          <div class="quick-contribution-v150"><button type="button" data-contribution-amount="1000">1 000</button><button type="button" data-contribution-amount="10000">10 000</button><button type="button" data-contribution-amount="50000">50 000</button></div>
          <div class="field"><label>КОММЕНТАРИЙ — НЕОБЯЗАТЕЛЬНО</label><input name="note" maxlength="200" placeholder="Например: на развитие государства" ${disabled}></div>
          <p class="hint">${esc(reason)} Деньги расходуются только через государственные механизмы и бюджетные решения.</p>
          <button class="positive wide" type="submit" ${disabled}>🤝 ВНЕСТИ ВКЛАД В КАЗНУ</button>
        </form>
      </article>
      <div class="section-head contribution-head-v150"><div><small>ЦЕЛЕВЫЕ НАКОПЛЕНИЯ</small><h2>Государственные фонды</h2></div></div>
      <div class="fund-grid-v150">${fundCards(data)}</div>
      <div class="contribution-columns-v150">
        <article class="panel"><div class="panel-title"><span>🏆</span><div><b>Меценаты государства</b><small>Топ участников по добровольным вкладам</small></div></div>${topCards(data)}</article>
        <article class="panel"><div class="panel-title"><span>📒</span><div><b>Последние вклады</b><small>Публичный реестр пополнений казны</small></div></div>${recentCards(data)}</article>
      </div>`;
  }

  async function loadState(){
    if(!chatId)return;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}`,{cache:'no-store',headers:{'X-Telegram-Init-Data':tg?.initData||''}});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось загрузить государственные фонды.');
      state=data;
      ensureWinTaxOption();
      renderContributions();
    }catch(error){
      toast(error.message||'Не удалось загрузить государственные фонды.','error');
    }
  }

  async function submitContribution(form){
    if(busy)return;
    const values=Object.fromEntries(new FormData(form).entries());
    const amount=Number(values.amount);
    if(!Number.isFinite(amount)||amount<100||amount>1000000){
      toast('Размер вклада должен быть от 100 до 1 000 000 влияния.','error');
      return;
    }
    const selected=form.querySelector('select[name="fund_key"] option:checked');
    const fundTitle=selected?.textContent||'государственный фонд';
    if(!confirm(`Внести ${fmt(amount)} влияния в ${fundTitle}?`))return;
    busy=true;
    try{
      const response=await fetch('/government-v150/api/contribute',{
        method:'POST',cache:'no-store',headers,
        body:JSON.stringify({chat_id:chatId,amount,fund_key:values.fund_key||'general',note:values.note||''})
      });
      const result=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!result.ok)throw new Error(result.reason||'Вклад не выполнен.');
      toast(result.message||'Вклад поступил в казну.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      await loadState();
      setTimeout(()=>document.getElementById('refreshButton')?.click(),150);
    }catch(error){
      toast(error.message||'Вклад не выполнен.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }finally{busy=false}
  }

  async function submitWinTax(form,event){
    const values=Object.fromEntries(new FormData(form).entries());
    if(values.bill_type!=='win_tax')return false;
    event.preventDefault();
    event.stopImmediatePropagation();
    if(busy)return true;
    const rate=Number(values.win_rate);
    if(!Number.isFinite(rate)||rate<0||rate>100){
      toast('Ставка налога на игровой выигрыш должна быть от 0% до 100%.','error');
      return true;
    }
    if(!confirm(`Передать депутатам закон о налоге ${rate}% с игрового выигрыша?`))return true;
    busy=true;
    try{
      const response=await fetch('/government-v127/api/action',{
        method:'POST',cache:'no-store',headers,
        body:JSON.stringify({
          action:'create_bill',chat_id:chatId,bill_type:'win_tax',
          title:values.title||'О налоге на игровой выигрыш',
          description:values.description||`Установить налог на положительный игровой выигрыш в размере ${rate}%.`,
          payload:{rate}
        })
      });
      const result=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!result.ok)throw new Error(result.reason||'Законопроект не создан.');
      toast('Закон о налоге на выигрыш передан депутатам.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      setTimeout(()=>document.getElementById('refreshButton')?.click(),200);
    }catch(error){
      toast(error.message||'Законопроект не создан.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }finally{busy=false}
    return true;
  }

  document.addEventListener('change',event=>{
    if(event.target.id==='billType'){
      setTimeout(()=>{
        ensureWinTaxOption();
        if(event.target.value==='win_tax'){
          const extra=document.getElementById('billExtra');
          if(extra)extra.innerHTML=winTaxFields();
        }
      },0);
    }
  });

  document.addEventListener('click',event=>{
    const quick=event.target.closest?.('[data-contribution-amount]');
    if(quick){
      const input=document.querySelector('#treasuryContributionFormV150 input[name="amount"]');
      if(input)input.value=String(quick.dataset.contributionAmount||1000);
      return;
    }
    if(event.target.closest?.('#refreshButton'))setTimeout(loadState,250);
  });

  document.addEventListener('submit',async event=>{
    if(event.target.id==='treasuryContributionFormV150'){
      event.preventDefault();
      await submitContribution(event.target);
      return;
    }
    if(event.target.id==='billForm')await submitWinTax(event.target,event);
  },true);

  function scheduleEnsure(){
    cancelAnimationFrame(frame);
    frame=requestAnimationFrame(ensureWinTaxOption);
  }

  const observer=new MutationObserver(scheduleEnsure);
  observer.observe(document.documentElement,{subtree:true,childList:true});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)loadState();});
  window.addEventListener('focus',loadState);
  loadState();
  scheduleEnsure();
})();
