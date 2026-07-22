(()=>{
  'use strict';
  if(window.__governmentTreasuryManagementV164)return;
  window.__governmentTreasuryManagementV164=true;

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
  let formDraft=null;

  function treasuryActive(){
    return Boolean(document.querySelector('.screen[data-screen="treasury"]')?.classList.contains('active'));
  }

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=String(text||'Готово.');
    node.className=`toast show ${type}`;
    clearTimeout(node.__tm164Timer);
    node.__tm164Timer=setTimeout(()=>node.className='toast',3600);
  }

  function ensureMount(){
    let node=document.getElementById('treasuryManagementV164');
    if(node)return node;
    const hero=document.getElementById('treasuryHero');
    if(!hero)return null;
    node=document.createElement('div');
    node.id='treasuryManagementV164';
    node.className='treasury-management-v164';
    hero.insertAdjacentElement('afterend',node);
    return node;
  }

  function captureDraft(){
    const form=document.getElementById('treasuryManagementFormV164');
    if(form)formDraft=Object.fromEntries(new FormData(form).entries());
  }

  function restoreDraft(){
    if(!formDraft)return;
    const form=document.getElementById('treasuryManagementFormV164');
    if(!form)return;
    for(const [key,value] of Object.entries(formDraft)){
      const field=form.elements.namedItem(key);
      if(field)field.value=String(value??'');
    }
    syncTargetFields();
    syncMode();
  }

  async function api(path,options={}){
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),15000);
    try{
      const response=await fetch(path,{cache:'no-store',...options,signal:controller.signal,headers:{...headers,...(options.headers||{})}});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      return data;
    }catch(error){
      if(error.name==='AbortError')throw new Error('Сервер долго не отвечает.');
      throw error;
    }finally{clearTimeout(timeout)}
  }

  async function sharedState(force=false){
    const now=Date.now();
    if(!force&&window.__governmentTreasuryState&&now-Number(window.__governmentTreasuryStateAt||0)<3000){
      return window.__governmentTreasuryState;
    }
    if(window.__governmentTreasuryStatePromise)return window.__governmentTreasuryStatePromise;
    const promise=api(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_treasury=${now}`)
      .then(data=>{
        window.__governmentTreasuryState=data;
        window.__governmentTreasuryStateAt=Date.now();
        return data;
      })
      .finally(()=>{
        if(window.__governmentTreasuryStatePromise===promise)window.__governmentTreasuryStatePromise=null;
      });
    window.__governmentTreasuryStatePromise=promise;
    return promise;
  }

  function userOptions(){
    const selected=Number(formDraft?.target_user_id||0);
    return (state?.eligible_users||[]).map(user=>
      `<option value="${Number(user.user_id)}" ${selected===Number(user.user_id)?'selected':''}>${esc(user.name)} · 💰 ${fmt(user.points)} · ⭐ ${fmt(user.career_points)}</option>`
    ).join('');
  }

  function structureOptions(structures){
    const selected=String(formDraft?.structure_key||'');
    return structures.map(item=>
      `<option value="${esc(item.key)}" ${selected===String(item.key)?'selected':''}>${item.emoji} ${esc(item.title)} · ${fmt(item.balance)}</option>`
    ).join('');
  }

  function operationLabel(item){
    const mode=item.mode==='direct'?'прямое решение президента':'бюджетный закон';
    return `${mode} · ${date(item.created_at)}`;
  }

  function render(){
    const mount=ensureMount();
    if(!mount||!state)return;
    captureDraft();
    const tm=state.treasury_management_v164||{};
    const treasury=state.treasury||{};
    const structures=Array.isArray(tm.structures)?tm.structures:[];
    const recent=Array.isArray(tm.recent)?tm.recent:[];
    const sanctioned=Boolean(tm.sanctioned);
    const canPropose=Boolean(tm.can_propose);
    const warning=sanctioned&&canPropose
      ?'<div class="treasury-warning-v164"><b>🚫 На президенте есть санкции</b><span>Прямые расходы заблокированы, но бюджетные проекты можно передавать в Госдуму.</span></div>'
      :'';
    const form=canPropose?`
      <article class="panel treasury-control-v164">
        <div class="panel-title"><span>💸</span><div><b>Выдать деньги из казны</b><small>Мелкие расходы исполняются сразу, крупные автоматически уходят в Госдуму</small></div></div>
        ${warning}
        <form id="treasuryManagementFormV164">
          <div class="field"><label>ТИП ПОЛУЧАТЕЛЯ</label><select name="target_type" id="treasuryTargetTypeV164"><option value="user">👤 Участник беседы</option><option value="structure">🏛 Государственная структура</option></select></div>
          <div class="field" id="treasuryUserFieldV164"><label>ПОЛУЧАТЕЛЬ</label><select name="target_user_id">${userOptions()}</select></div>
          <div class="field" id="treasuryStructureFieldV164" hidden><label>ГОСУДАРСТВЕННАЯ СТРУКТУРА</label><select name="structure_key">${structureOptions(structures)}</select></div>
          <div class="field"><label>СУММА</label><input name="amount" id="treasuryAmountV164" type="number" min="1" max="1000000" value="${esc(formDraft?.amount||Math.max(1,Math.min(100,Number(tm.direct_limit)||100)))}"></div>
          <div class="field"><label>ОСНОВАНИЕ</label><textarea name="reason" minlength="10" maxlength="500" placeholder="На что и почему выделяются деньги">${esc(formDraft?.reason||'')}</textarea></div>
          <div class="treasury-mode-v164" id="treasuryModeV164"></div>
          <button class="positive wide" id="treasurySubmitV164" type="submit">💸 ВЫПЛАТИТЬ ИЗ КАЗНЫ</button>
        </form>
      </article>`:`<div class="empty treasury-readonly-v164">Управление расходами доступно действующему Президенту реальности. Балансы государственных структур открыты для всех.</div>`;
    mount.innerHTML=`
      <article class="panel treasury-president-v164">
        <div class="panel-title"><span>🏛</span><div><b>Президентское управление казной</b><small>Отдельные фонды, лимиты и публичная история решений</small></div></div>
        <div class="metric-grid treasury-metrics-v164">
          <div class="metric"><small>СВОБОДНАЯ КАЗНА</small><b>${fmt(treasury.balance)}</b></div>
          <div class="metric"><small>ЛИМИТ ОДНОЙ ВЫПЛАТЫ</small><b>${fmt(tm.direct_limit)}</b></div>
          <div class="metric"><small>ОСТАТОК НА СЕГОДНЯ</small><b>${fmt(tm.daily_remaining)}</b></div>
          <div class="metric"><small>В ФОНДАХ СТРУКТУР</small><b>${fmt(tm.structure_total)}</b></div>
        </div>
        <p class="hint">Самостоятельный расход ограничен системой. Выплата самому себе, превышение лимита или санкции автоматически переводят решение на голосование Госдумы.</p>
      </article>
      ${form}
      <article class="panel">
        <div class="panel-title"><span>🏦</span><div><b>Балансы государственных структур</b><small>Средства отделены от личных балансов чиновников</small></div></div>
        <div class="treasury-structure-grid-v164">${structures.map(item=>`<div class="treasury-structure-v164"><span>${item.emoji}</span><div><b>${esc(item.title)}</b><small>${item.updated_at?`обновлено ${date(item.updated_at)}`:'финансирование ещё не выделялось'}</small></div><strong>${fmt(item.balance)}</strong></div>`).join('')}</div>
      </article>
      <article class="panel">
        <div class="panel-title"><span>📋</span><div><b>Президентские решения</b><small>Последние прямые выплаты и финансирование структур</small></div></div>
        <div class="log-list">${recent.length?recent.map(item=>`<div class="log-item"><span><b>${item.target_type==='structure'?'🏛':'👤'} ${esc(item.target_title)}</b><small>${esc(item.reason)} · ${operationLabel(item)}</small></span><strong class="minus">−${fmt(item.amount)}</strong></div>`).join(''):'<div class="empty">Президентских расходов пока нет.</div>'}</div>
      </article>`;
    restoreDraft();
  }

  function syncTargetFields(){
    const form=document.getElementById('treasuryManagementFormV164');
    if(!form)return;
    const type=String(form.elements.target_type?.value||'user');
    const user=document.getElementById('treasuryUserFieldV164');
    const structure=document.getElementById('treasuryStructureFieldV164');
    if(user)user.hidden=type!=='user';
    if(structure)structure.hidden=type!=='structure';
  }

  function syncMode(){
    const form=document.getElementById('treasuryManagementFormV164');
    const tm=state?.treasury_management_v164||{};
    if(!form)return;
    const amount=Math.max(0,Number(form.elements.amount?.value)||0);
    const type=String(form.elements.target_type?.value||'user');
    const targetId=Number(form.elements.target_user_id?.value)||0;
    const selfId=Number(state?.user?.user_id)||0;
    const direct=Boolean(tm.can_direct)&&amount>0&&amount<=Number(tm.direct_limit||0)&&amount<=Number(tm.daily_remaining||0)&&!(type==='user'&&targetId===selfId);
    const mode=document.getElementById('treasuryModeV164');
    const button=document.getElementById('treasurySubmitV164');
    if(mode)mode.innerHTML=direct
      ?`<b>⚡ Будет исполнено сразу</b><span>После операции останется дневного лимита: ${fmt(Math.max(0,Number(tm.daily_remaining||0)-amount))}</span>`
      :'<b>🏛 Будет внесено в Госдуму</b><span>Депутаты проголосуют, затем президент подпишет бюджетный закон.</span>';
    if(button){
      button.className=`${direct?'positive':'action'} wide`;
      button.textContent=direct?'💸 ВЫПЛАТИТЬ ИЗ КАЗНЫ':'🏛 ВНЕСТИ В ГОСДУМУ';
    }
  }

  async function load(force=false){
    if(!chatId||loading||!treasuryActive())return;
    loading=true;
    try{
      state=await sharedState(force);
      render();
    }catch(error){toast(error.message||'Не удалось загрузить управление казной.','error')}
    finally{loading=false}
  }

  async function submit(form){
    const data=Object.fromEntries(new FormData(form).entries());
    const button=document.getElementById('treasurySubmitV164');
    if(button)button.disabled=true;
    try{
      const result=await api('/government-v164/api/action',{method:'POST',body:JSON.stringify({
        action:'treasury_disburse',chat_id:chatId,target_type:String(data.target_type||'user'),
        target_user_id:Number(data.target_user_id)||0,structure_key:String(data.structure_key||''),
        amount:Number(data.amount)||0,reason:String(data.reason||'')
      })});
      formDraft=null;
      window.__governmentTreasuryState=null;
      window.__governmentTreasuryStateAt=0;
      toast(result.message||'Решение казны исполнено.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      document.getElementById('refreshButton')?.click();
      setTimeout(()=>load(true),240);
    }catch(error){
      toast(error.message||'Решение казны не выполнено.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }finally{if(button)button.disabled=false}
  }

  document.addEventListener('click',event=>{
    if(event.target.closest?.('[data-tab="treasury"]'))setTimeout(()=>load(false),120);
    if(event.target.closest?.('#refreshButton')&&treasuryActive())setTimeout(()=>load(true),220);
  },true);
  document.addEventListener('input',event=>{
    if(event.target.closest?.('#treasuryManagementFormV164')){captureDraft();syncMode()}
  });
  document.addEventListener('change',event=>{
    if(event.target.closest?.('#treasuryManagementFormV164')){captureDraft();syncTargetFields();syncMode()}
  });
  document.addEventListener('submit',event=>{
    if(event.target.id!=='treasuryManagementFormV164')return;
    event.preventDefault();captureDraft();submit(event.target);
  });
  document.addEventListener('visibilitychange',()=>{if(!document.hidden&&treasuryActive())load(false)});
  window.addEventListener('focus',()=>{if(treasuryActive())load(false)});
})();