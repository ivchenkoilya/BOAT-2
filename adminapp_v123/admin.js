(()=>{
  'use strict';
  const tg=window.Telegram?.WebApp;
  tg?.ready();tg?.expand();tg?.setHeaderColor?.('#08060f');tg?.setBackgroundColor?.('#08060f');
  const initData=tg?.initData||'';
  const params=new URLSearchParams(location.search);
  let selectedChat=Number(params.get('chat_id')||localStorage.getItem('admin123Chat')||0);
  let selectedUser=Number(params.get('user_id')||localStorage.getItem('admin123User')||0);
  let state=null,toastTimer=null,pendingConfirm=null,searchTimer=null;
  const $=id=>document.getElementById(id);
  const fmt=v=>new Intl.NumberFormat('ru-RU').format(Number(v)||0);
  const esc=v=>String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const headers={'X-Telegram-Init-Data':initData,'Content-Type':'application/json'};

  function toast(text,type=''){
    const node=$('toast');node.textContent=text;node.className=`toast show ${type}`;
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>node.className='toast',3200);
  }
  function loading(show){$('loading').classList.toggle('hidden',!show)}
  async function request(url,options={}){
    const response=await fetch(url,{cache:'no-store',...options,headers:{...headers,...(options.headers||{})}});
    const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
    if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
    return data;
  }
  async function loadState(silent=false){
    if(!silent)loading(true);
    $('connection').textContent='● Обновление…';
    try{
      state=await request(`/admin-v123/api/state?chat_id=${selectedChat||0}&user_id=${selectedUser||0}`);
      selectedChat=Number(state.selected_chat?.chat_id)||0;
      if(state.target){selectedUser=Number(state.target.user_id)||0;localStorage.setItem('admin123User',String(selectedUser))}
      localStorage.setItem('admin123Chat',String(selectedChat));
      render();$('connection').textContent='● Подключено';$('connection').style.color='#66e3aa';
    }catch(e){$('connection').textContent='● Ошибка';$('connection').style.color='#ff7187';toast(e.message,'error')}
    finally{loading(false)}
  }
  async function act(action,extra={}){
    if(!selectedUser&&action!=='chat_cooldowns_reset'){toast('Сначала выбери участника.','error');switchTab('participant');return}
    try{
      tg?.HapticFeedback?.impactOccurred?.('light');
      const result=await request('/admin-v123/api/action',{method:'POST',body:JSON.stringify({action,chat_id:selectedChat,user_id:selectedUser,...extra})});
      toast(result.message||'Готово','success');tg?.HapticFeedback?.notificationOccurred?.('success');await loadState(true);
    }catch(e){toast(e.message,'error');tg?.HapticFeedback?.notificationOccurred?.('error')}
  }
  function metric(icon,label,value,note='',cls=''){
    return `<article class="metric ${cls}"><span>${icon}</span><small>${esc(label)}</small><b>${esc(value)}</b>${note?`<em>${esc(note)}</em>`:''}</article>`;
  }
  function render(){
    $('version').textContent=state.version||'Reality 123';
    $('chatSelect').innerHTML=(state.chats||[]).map(c=>`<option value="${c.chat_id}" ${Number(c.chat_id)===selectedChat?'selected':''}>${esc(c.title)} · ${c.users}</option>`).join('')||'<option value="0">Нет бесед</option>';
    const t=state.target;
    $('targetEmoji').textContent=t?.role?.emoji||'?';$('targetName').textContent=t?.full_name||'Не выбран';
    $('targetMeta').textContent=t?`${t.role.emoji} ${t.role.title} · ⭐ ${fmt(t.career_points)} · 💰 ${fmt(t.points)}`:'Нажми для выбора';
    document.querySelectorAll('.requires-user').forEach(node=>node.classList.toggle('disabled',!t));
    renderOverview();renderUsers(state.quick_users||[],'quickUsers');
    if(!$('searchInput').value.trim())renderUsers(state.quick_users||[],'searchResults');
    renderParticipant();renderCareer();renderSystem();
  }
  function renderOverview(){
    const c=state.selected_chat||{},today=state.today||{};
    $('overviewMetrics').innerHTML=[
      metric('👥','Участников',fmt(c.users||0),'в выбранной беседе'),
      metric('💰','Обычное влияние',fmt(c.wallet_total||0),'суммарный баланс'),
      metric('⭐','Карьерное влияние',fmt(c.career_total||0),'суммарный прогресс'),
      metric('📈','Начислено сегодня',`⭐ ${fmt(today.career||0)}`,`💰 ${fmt(today.wallet||0)} обычного`,'good')
    ].join('');
  }
  function userMarkup(u){
    const active=Number(u.user_id)===selectedUser;
    return `<button class="user ${active?'active':''}" data-user="${u.user_id}"><span>${u.role?.emoji||'👤'}</span><span><b>${esc(u.full_name)}</b><small>${u.username?'@'+esc(u.username):'ID '+u.user_id} · ${esc(u.role?.title||'')}</small></span><strong>⭐ ${fmt(u.career_points)}<br>💰 ${fmt(u.points)}</strong></button>`;
  }
  function renderUsers(users,id){$(id).innerHTML=users.length?users.map(userMarkup).join(''):'<div class="empty">Участники не найдены.</div>'}
  async function selectUser(id){selectedUser=Number(id)||0;localStorage.setItem('admin123User',String(selectedUser));await loadState(true);switchTab('participant');toast(`Выбран: ${state.target?.full_name||id}`,'success')}
  async function searchUsers(){
    const q=$('searchInput').value.trim();
    try{const data=await request(`/admin-v123/api/users?chat_id=${selectedChat}&q=${encodeURIComponent(q)}`);renderUsers(data.users||[],'searchResults')}
    catch(e){toast(e.message,'error')}
  }
  function renderParticipant(){
    const t=state.target,finance=state.finance||{},talents=state.talents||{};
    $('participantMetrics').innerHTML=t?[
      metric(t.role.emoji,'Постоянная роль',t.role.title,t.role.next_title?`до ${t.role.next_title}: ${fmt(t.role.remaining)}`:'высшая роль'),
      metric('⭐','Карьерное влияние',fmt(t.career_points),'не тратится'),
      metric('💰','Обычное влияние',fmt(t.points),'ставки и финансы'),
      metric('🌳','Очки древа',`${fmt(talents.available||0)} свободно`,`${fmt(talents.spent||0)} потрачено`),
      metric('📉','Активные долги',fmt(finance.borrowed||0),`${fmt(finance.active_loans||0)} договоров`,Number(finance.overdue||0)>0?'warn':''),
      metric('📤','Выдано в долг',fmt(finance.lent||0),finance.overdue?`просрочено ${fmt(finance.overdue)}`:'без просрочки')
    ].join(''):'<div class="empty" style="grid-column:1/-1">Выбери участника.</div>';
    $('walletSubtitle').textContent=`Текущий баланс: ${fmt(t?.points||0)}`;
    $('careerSubtitle').textContent=`Текущий прогресс: ${fmt(t?.career_points||0)}`;
    const progress=Math.round(Number(t?.role?.progress||0)*100);$('careerBar').style.width=`${progress}%`;
    $('careerProgressText').textContent=t?(t.role.next_title?`${progress}% роли · до «${t.role.next_title}» осталось ${fmt(t.role.remaining)}`:'Достигнута высшая роль'):'—';
    const presets=state.role_presets||{};
    $('roleGrid').innerHTML=Object.entries(presets).map(([key,r])=>`<button class="${t?.role?.key===key?'active':''}" data-role="${key}"><span>${r.emoji}</span><span><b>${esc(r.title)}</b><small>от ${fmt(r.points)}</small></span></button>`).join('');
  }
  function historyMarkup(items){
    return items.length?items.map(item=>{const delta=Number(item.delta||0);const sign=delta>0?'+':'';const cls=delta>0?'plus':delta<0?'minus':'';const when=item.created_at?new Date(Number(item.created_at)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';return `<div class="history-item"><span><b>${esc(item.reason||item.action||'Операция')}</b><small>${esc(item.source_type||'')} ${when}</small></span><strong class="${cls}">${sign}${fmt(delta)}</strong></div>`}).join(''):'<div class="empty">История пока пуста.</div>';
  }
  function renderCareer(){
    const t=state.target;
    $('careerMetrics').innerHTML=t?[
      metric(t.role.emoji,'Текущая роль',t.role.title,`порог ${fmt(t.role.floor)}`),
      metric('⭐','Карьерное влияние',fmt(t.career_points),t.role.next_title?`ещё ${fmt(t.role.remaining)}`:'максимальная роль'),
      metric('💰','Обычный баланс',fmt(t.points),'на роль не влияет'),
      metric('💬','Сообщений',fmt(t.message_count),'активность участника')
    ].join(''):'<div class="empty" style="grid-column:1/-1">Выбери участника.</div>';
    $('careerHistory').innerHTML=historyMarkup(state.career_history||[]);
    $('walletHistory').innerHTML=historyMarkup(state.wallet_history||[]);
  }
  function renderSystem(){
    const items=state.admin_history||[];
    $('adminHistory').innerHTML=items.length?items.map(item=>{const when=new Date(Number(item.created_at)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});return `<div class="history-item"><span><b>${esc(item.detail||item.action)}</b><small>${esc(item.action)} · ${when}</small></span><strong>#${item.id}</strong></div>`}).join(''):'<div class="empty">Журнал пуст.</div>';
  }
  function switchTab(name){
    document.querySelectorAll('.screen').forEach(s=>s.classList.toggle('active',s.dataset.screen===name));
    document.querySelectorAll('.nav button').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));
    scrollTo({top:0,behavior:'smooth'});
  }
  function openLegacy(){if(state?.legacy_url)location.href=state.legacy_url;else toast('Ссылка недоступна.','error')}
  function confirmAction(action,text){pendingConfirm={action};$('confirmText').textContent=text;$('confirmModal').classList.remove('hidden')}

  document.addEventListener('click',e=>{
    const user=e.target.closest('[data-user]');if(user){selectUser(user.dataset.user);return}
    const tab=e.target.closest('[data-tab]');if(tab){switchTab(tab.dataset.tab);return}
    const role=e.target.closest('[data-role]');if(role){confirmAction('role_set',`Назначить роль «${state.role_presets?.[role.dataset.role]?.title||role.dataset.role}»?`);pendingConfirm.extra={role:role.dataset.role};return}
    const button=e.target.closest('[data-action]');if(button){act(button.dataset.action,{value:Number(button.dataset.value||0)});return}
    const danger=e.target.closest('[data-confirm]');if(danger){confirmAction(danger.dataset.confirm,'Статистика активности будет обнулена, но оба баланса сохранятся.');return}
    const exact=e.target.closest('[data-exact]');if(exact){const kind=exact.dataset.exact;const input=$(kind==='wallet'?'walletExact':'careerExact');const value=Number(String(input.value).replace(/\s/g,''));if(!Number.isFinite(value)||value<0){toast('Введи корректное неотрицательное число.','error');return}act(kind==='wallet'?'wallet_set':'career_set',{value:Math.trunc(value)});return}
  });
  $('chatSelect').addEventListener('change',async e=>{selectedChat=Number(e.target.value)||0;selectedUser=0;localStorage.setItem('admin123Chat',String(selectedChat));localStorage.removeItem('admin123User');await loadState(true)});
  $('targetButton').onclick=()=>switchTab('participant');$('refresh').onclick=()=>loadState(true);$('searchButton').onclick=searchUsers;
  $('searchInput').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(searchUsers,250)});
  $('openLegacy').onclick=openLegacy;$('openLegacyBottom').onclick=openLegacy;
  $('cancelConfirm').onclick=()=>{$('confirmModal').classList.add('hidden');pendingConfirm=null};
  $('acceptConfirm').onclick=async()=>{const item=pendingConfirm;$('confirmModal').classList.add('hidden');pendingConfirm=null;if(item)await act(item.action,item.extra||{})};
  $('confirmModal').addEventListener('click',e=>{if(e.target===$('confirmModal'))$('cancelConfirm').click()});
  loadState();
})();