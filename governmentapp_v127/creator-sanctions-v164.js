(()=>{
  'use strict';
  if(window.__governmentCreatorSanctionsV164)return;
  window.__governmentCreatorSanctionsV164=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice('government_'.length):0));
  const currentUserId=Number(tg?.initDataUnsafe?.user?.id||0);
  const headers={
    'Content-Type':'application/json',
    'X-Telegram-Init-Data':tg?.initData||''
  };

  let governmentState=null;
  let selectedUserId=0;
  let activeSanctions=[];
  let loading=false;
  let frame=0;

  const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,char=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[char]));

  function ownerMode(){
    const user=governmentState?.user||{};
    const access=governmentState?.role_access||{};
    return Boolean(user.owner_admin||access.owner_admin||governmentState?.creator_control_v151?.active);
  }

  function toast(message,error=false){
    const existing=document.getElementById('creatorSanctionsToastV164');
    const node=existing||document.createElement('div');
    node.id='creatorSanctionsToastV164';
    node.className=`creator-sanctions-toast-v164${error?' error':''}`;
    node.textContent=String(message||'');
    if(!existing)document.body.appendChild(node);
    requestAnimationFrame(()=>node.classList.add('show'));
    clearTimeout(node.__hideTimer);
    node.__hideTimer=setTimeout(()=>node.classList.remove('show'),3200);
  }

  async function requestJson(url,options={}){
    const response=await fetch(url,{cache:'no-store',headers,...options});
    const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул повреждённый ответ.'}));
    if(!response.ok||!data.ok)throw new Error(data.reason||`Ошибка ${response.status}`);
    return data;
  }

  async function loadGovernmentState(){
    if(!chatId)return null;
    governmentState=await requestJson(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}`);
    return governmentState;
  }

  async function loadSanctions(userId){
    selectedUserId=Number(userId||0);
    if(!selectedUserId){
      activeSanctions=[];
      renderPanel();
      return;
    }
    loading=true;
    renderPanel();
    try{
      const data=await requestJson(
        `/sanctions-v126/api/state?chat_id=${encodeURIComponent(chatId)}&user_id=${encodeURIComponent(selectedUserId)}`
      );
      activeSanctions=Array.isArray(data.active)?data.active:[];
    }catch(error){
      activeSanctions=[];
      toast(error.message||'Не удалось загрузить санкции.',true);
    }finally{
      loading=false;
      renderPanel();
    }
  }

  function userOptions(){
    const users=Array.isArray(governmentState?.eligible_users)?[...governmentState.eligible_users]:[];
    users.sort((a,b)=>{
      if(Number(a.user_id)===currentUserId)return -1;
      if(Number(b.user_id)===currentUserId)return 1;
      return String(a.name||'').localeCompare(String(b.name||''),'ru');
    });
    return users.map(user=>{
      const id=Number(user.user_id||0);
      const own=id===currentUserId?' · ВЫ':'';
      return `<option value="${id}"${id===selectedUserId?' selected':''}>${escapeHtml(user.name||`ID ${id}`)}${own}</option>`;
    }).join('');
  }

  function sanctionsMarkup(){
    if(loading)return '<div class="creator-sanctions-empty-v164">Проверяем ограничения…</div>';
    if(!selectedUserId)return '<div class="creator-sanctions-empty-v164">Выбери участника.</div>';
    if(!activeSanctions.length)return '<div class="creator-sanctions-clear-v164">✅ Активных санкций у участника нет.</div>';
    return `<div class="creator-sanctions-list-v164">${activeSanctions.map(item=>`
      <article class="creator-sanction-item-v164">
        <span>${escapeHtml(item.emoji||'🚫')}</span>
        <div><b>${escapeHtml(item.title||item.type||'Ограничение')}</b><small>${escapeHtml(item.remaining||'действует')} · ${escapeHtml(item.reason||'Решение администрации')}</small></div>
      </article>`).join('')}</div>`;
  }

  function ensurePanel(){
    if(!ownerMode())return null;
    const oversight=document.querySelector('[data-screen="oversight"]');
    const composer=document.getElementById('sanctionComposer');
    if(!oversight||!composer)return null;
    let panel=document.getElementById('creatorSanctionsPanelV164');
    if(panel)return panel;
    panel=document.createElement('article');
    panel.id='creatorSanctionsPanelV164';
    panel.className='creator-sanctions-panel-v164';
    composer.insertAdjacentElement('beforebegin',panel);
    return panel;
  }

  function renderPanel(){
    const panel=ensurePanel();
    if(!panel)return;
    const users=Array.isArray(governmentState?.eligible_users)?governmentState.eligible_users:[];
    if(!selectedUserId&&users.length){
      const own=users.find(user=>Number(user.user_id)===currentUserId);
      selectedUserId=Number((own||users[0]).user_id||0);
    }
    panel.innerHTML=`
      <div class="creator-sanctions-head-v164">
        <div><small>АДМИН-ПАНЕЛЬ СОЗДАТЕЛЯ</small><h3>Полное снятие санкций</h3></div>
        <span>🛡️</span>
      </div>
      <p class="creator-sanctions-copy-v164">Выбери любого участника, включая себя. Кнопка снимает сразу все его активные ограничения в этой беседе.</p>
      <label class="creator-sanctions-field-v164"><span>УЧАСТНИК</span><select id="creatorSanctionsUserV164">${userOptions()}</select></label>
      <div id="creatorSanctionsStateV164">${sanctionsMarkup()}</div>
      <button id="creatorSanctionsClearV164" class="creator-sanctions-clear-button-v164" type="button" ${loading||!selectedUserId||!activeSanctions.length?'disabled':''}>
        ✅ СНЯТЬ ВСЕ САНКЦИИ С ЧЕЛОВЕКА
      </button>`;

    panel.querySelector('#creatorSanctionsUserV164')?.addEventListener('change',event=>{
      loadSanctions(Number(event.target.value||0));
    });
    panel.querySelector('#creatorSanctionsClearV164')?.addEventListener('click',clearAllSanctions);
  }

  async function confirmAction(text){
    if(tg?.showConfirm){
      return await new Promise(resolve=>tg.showConfirm(text,resolve));
    }
    return window.confirm(text);
  }

  async function clearAllSanctions(){
    if(loading||!selectedUserId||!activeSanctions.length)return;
    const user=(governmentState?.eligible_users||[]).find(item=>Number(item.user_id)===selectedUserId);
    const name=user?.name||`ID ${selectedUserId}`;
    const confirmed=await confirmAction(`Снять все активные санкции с участника «${name}»?`);
    if(!confirmed)return;

    loading=true;
    renderPanel();
    try{
      const data=await requestJson('/sanctions-v126/api/action',{
        method:'POST',
        body:JSON.stringify({
          action:'revoke',
          chat_id:chatId,
          user_id:selectedUserId
        })
      });
      activeSanctions=[];
      tg?.HapticFeedback?.notificationOccurred?.('success');
      toast(data.message||'Все санкции сняты.');
      await loadGovernmentState();
    }catch(error){
      tg?.HapticFeedback?.notificationOccurred?.('error');
      toast(error.message||'Не удалось снять санкции.',true);
    }finally{
      loading=false;
      renderPanel();
    }
  }

  async function boot(){
    if(!chatId)return;
    try{
      await loadGovernmentState();
      if(!ownerMode())return;
      renderPanel();
      if(selectedUserId)await loadSanctions(selectedUserId);
    }catch(error){
      console.warn('Creator sanctions v164:',error);
    }
  }

  function schedule(){
    cancelAnimationFrame(frame);
    frame=requestAnimationFrame(()=>{
      if(governmentState&&ownerMode())renderPanel();
    });
  }

  document.addEventListener('click',event=>{
    if(event.target.closest('[data-tab="oversight"]'))setTimeout(schedule,0);
    if(event.target.closest('#refreshButton'))setTimeout(async()=>{
      try{
        await loadGovernmentState();
        renderPanel();
        if(selectedUserId)await loadSanctions(selectedUserId);
      }catch(_error){}
    },350);
  },true);
  window.addEventListener('focus',schedule);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)schedule();});
  boot();
})();
