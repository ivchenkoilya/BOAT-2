(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const previousFetch=window.fetch.bind(window);
  const runtime={state:null,busy:false,renderTimer:null,searchTimer:null};
  window.AdminFullV124=runtime;

  const $=id=>document.getElementById(id);
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({
    '&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'
  }[char]));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};

  function sourceUrl(input){
    if(typeof input==='string'||input instanceof URL)return String(input);
    if(input instanceof Request)return input.url;
    return '';
  }

  function toast(text,type='success'){
    const node=$('toast');
    if(!node)return;
    node.textContent=text;
    node.className=`toast show ${type}`;
    clearTimeout(node.__v124Timer);
    node.__v124Timer=setTimeout(()=>node.className='toast',3600);
  }

  function selectedIds(fallback={}){
    return {
      chat_id:Number(fallback.selected_chat?.chat_id||runtime.state?.selected_chat?.chat_id||localStorage.getItem('admin76Chat')||0),
      user_id:Number(fallback.target?.user_id||runtime.state?.target?.user_id||localStorage.getItem('admin76User')||0)
    };
  }

  async function request(url,options={}){
    const response=await previousFetch(url,{cache:'no-store',...options,headers:{...headers,...(options.headers||{})}});
    const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
    if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
    return data;
  }

  async function loadCareer(chatId,userId,silent=false){
    if(!chatId)return;
    try{
      const data=await request(`/admin-v123/api/state?chat_id=${chatId}&user_id=${userId||0}`);
      runtime.state=data;
      scheduleRender();
    }catch(error){
      if(!silent)toast(error.message||'Не удалось загрузить карьерные данные.','error');
    }
  }

  async function loadCareerUsers(chatId,query){
    if(!chatId)return;
    try{
      const data=await request(`/admin-v123/api/users?chat_id=${chatId}&q=${encodeURIComponent(query||'')}`);
      setTimeout(()=>renderUsers(data.users||[],'searchResults'),60);
    }catch{}
  }

  window.fetch=async(input,init={})=>{
    const url=sourceUrl(input);
    const response=await previousFetch(input,init);
    if(url.includes('/admin-v76/api/state')){
      response.clone().json().then(data=>{
        if(!data?.ok)return;
        const ids=selectedIds(data);
        if(ids.chat_id)loadCareer(ids.chat_id,ids.user_id,true);
      }).catch(()=>{});
    }else if(url.includes('/admin-v76/api/users')){
      try{
        const parsed=new URL(url,location.origin);
        loadCareerUsers(Number(parsed.searchParams.get('chat_id')||0),parsed.searchParams.get('q')||'');
      }catch{}
    }
    return response;
  };

  function installStyles(){
    if($('v124CareerStyles'))return;
    const style=document.createElement('style');
    style.id='v124CareerStyles';
    style.textContent=`
      .bottom-nav{overflow-x:auto;justify-content:flex-start;scrollbar-width:none}.bottom-nav::-webkit-scrollbar{display:none}.bottom-nav>button{min-width:61px;flex:1 0 61px}
      #v124CareerPanel{position:relative;overflow:hidden;border-color:#9c68ce;background:radial-gradient(circle at 100% 0,#b967ff32,transparent 43%),linear-gradient(150deg,#28163a,#100a18);box-shadow:0 18px 45px #0007,0 0 28px #a859db25}
      #v124CareerPanel:before{content:"";position:absolute;width:160px;height:160px;right:-75px;top:-80px;border-radius:50%;background:#c574ff28;filter:blur(14px)}
      .v124-progress{position:relative;margin:12px 0}.v124-progress>div{height:10px;border:1px solid #5a3c72;border-radius:999px;background:#09060e;overflow:hidden}.v124-progress i{display:block;height:100%;width:0;background:linear-gradient(90deg,#7140c7,#c86cff,#f4d077);box-shadow:0 0 15px #b867ff;transition:width .35s ease}.v124-progress small{display:block;margin-top:6px;color:#a99ab2;font-size:9px;line-height:1.4}
      .v124-exact{display:grid;grid-template-columns:1fr 112px;gap:8px;margin-top:9px;position:relative}.v124-exact input{width:100%;min-height:48px;border:1px solid #59406d;border-radius:13px;background:#0b0811;color:#f5ecfb;padding:0 12px;outline:none;font-size:16px}.v124-exact button,.v124-action{min-height:46px;border:1px solid #6d4790;border-radius:13px;background:linear-gradient(180deg,#4b266f,#28133d);color:#fff;font-weight:900}
      .v124-role-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.v124-role{display:flex;align-items:center;gap:9px;min-height:58px;border:1px solid #49335b;border-radius:14px;background:#100b17;color:#f3eaf7;padding:9px;text-align:left}.v124-role.active{border-color:#d08bff;background:linear-gradient(145deg,#46255f,#251334);box-shadow:0 0 20px #b968ff35}.v124-role>span:first-child{font-size:22px}.v124-role b,.v124-role small{display:block}.v124-role b{font-size:11px}.v124-role small{font-size:8px;color:#a797b1;margin-top:3px}
      .v124-career-hero{padding:16px;border:1px solid #7d55a2;border-radius:21px;background:radial-gradient(circle at 100% 0,#b35fff38,transparent 42%),linear-gradient(150deg,#261735,#0e0915);margin-bottom:12px}.v124-career-head{display:flex;align-items:center;gap:12px}.v124-career-icon{width:54px;height:54px;display:grid;place-items:center;border:1px solid #9b6bc1;border-radius:17px;background:#342047;font-size:27px}.v124-career-head small,.v124-career-head b{display:block}.v124-career-head small{color:#d19dff;font-size:9px;letter-spacing:.14em;font-weight:900}.v124-career-head b{font-size:19px;margin-top:3px}.v124-career-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:13px}.v124-career-stat{padding:11px;border:1px solid #4d385d;border-radius:13px;background:#0c0811}.v124-career-stat small,.v124-career-stat b{display:block}.v124-career-stat small{font-size:8px;color:#9a8aa4}.v124-career-stat b{font-size:17px;margin-top:3px;color:#f3d985}
      .v124-history{display:grid;gap:7px}.v124-history-item{display:grid;grid-template-columns:1fr auto;gap:9px;padding:10px 11px;border:1px solid #382942;border-radius:13px;background:#0d0912}.v124-history-item b,.v124-history-item small{display:block}.v124-history-item b{font-size:10px}.v124-history-item small{font-size:8px;color:#8f8198;margin-top:3px}.v124-history-item strong{font-size:11px}.v124-history-item strong.plus{color:#7de4b8}.v124-history-item strong.minus{color:#ff8297}
      #participantMetrics .v124-career-metric,#homeMetrics .v124-career-metric{border-color:#77509c;background:radial-gradient(circle at 100% 0,#b260ff30,transparent 45%),linear-gradient(145deg,#241532,#0e0915)}
      @media(max-width:380px){.v124-role-grid{grid-template-columns:1fr}.v124-exact{grid-template-columns:1fr}.v124-career-grid{grid-template-columns:1fr 1fr}}
    `;
    document.head.appendChild(style);
  }

  function careerPanelMarkup(){
    return `<article class="panel requires-user" id="v124CareerPanel">
      <div class="panel-title"><span>⭐</span><div><b>Карьерное влияние</b><small>Определяет постоянную роль и не тратится в играх</small></div></div>
      <div class="v124-progress"><div><i id="v124CareerBar"></i></div><small id="v124CareerProgress">Загрузка прогресса…</small></div>
      <div class="step-grid"><button data-v124-delta="-50000">−50 000</button><button data-v124-delta="-5000">−5 000</button><button data-v124-delta="5000">+5 000</button><button data-v124-delta="50000">+50 000</button></div>
      <div class="v124-exact"><input id="v124CareerExact" inputmode="numeric" placeholder="Точное карьерное влияние"><button data-v124-set>Установить</button></div>
    </article>`;
  }

  function careerScreenMarkup(){
    return `<section class="screen" data-screen="career124">
      <div class="section-head"><div><small>КАРЬЕРНАЯ СИСТЕМА</small><h2>Роли и история</h2></div><button class="mini-button" id="v124Refresh">Обновить</button></div>
      <div id="v124CareerHero"></div>
      <article class="panel"><div class="panel-title"><span>🎭</span><div><b>Назначить постоянную роль</b><small>Меняется только карьерное влияние</small></div></div><div class="v124-role-grid" id="v124CareerRoles"></div></article>
      <article class="panel"><div class="panel-title"><span>⭐</span><div><b>История карьерного влияния</b><small>Задания, события, босс и ручные изменения</small></div></div><div class="v124-history" id="v124CareerHistory"></div></article>
      <article class="panel"><div class="panel-title"><span>💰</span><div><b>История обычного влияния</b><small>Ставки, игры, переводы и займы</small></div></div><div class="v124-history" id="v124WalletHistory"></div></article>
    </section>`;
  }

  function installUi(){
    installStyles();
    const participant=document.querySelector('[data-screen="participant"]');
    if(participant&&!$('v124CareerPanel')){
      const panels=[...participant.querySelectorAll('.panel.requires-user')];
      const pointsPanel=panels[0];
      if(pointsPanel)pointsPanel.insertAdjacentHTML('afterend',careerPanelMarkup());
    }

    const history=document.querySelector('[data-screen="history"]');
    if(history&&!document.querySelector('[data-screen="career124"]')){
      history.insertAdjacentHTML('beforebegin',careerScreenMarkup());
    }

    const nav=document.querySelector('.bottom-nav');
    const historyButton=nav?.querySelector('[data-tab="history"]');
    if(nav&&!nav.querySelector('[data-tab="career124"]')){
      const button=document.createElement('button');
      button.dataset.tab='career124';
      button.innerHTML='<span>⭐</span><small>Карьера</small>';
      nav.insertBefore(button,historyButton||null);
    }

    const roleGrid=$('roleGrid');
    const rolePanel=roleGrid?.closest('.panel');
    if(rolePanel){
      const title=rolePanel.querySelector('.panel-title b');
      const note=rolePanel.querySelector('.panel-title small');
      if(title)title.textContent='Постоянная карьерная роль';
      if(note)note.textContent='Назначение роли больше не меняет обычный баланс';
    }

    const pointsPanel=$('pointsSubtitle')?.closest('.panel');
    if(pointsPanel){
      const title=pointsPanel.querySelector('.panel-title b');
      const note=pointsPanel.querySelector('.panel-title small');
      if(title)title.textContent='Обычное влияние';
      if(note)note.textContent='Баланс для ставок, переводов, займов и трат';
    }
  }

  function metricCard(icon,label,value,note,id=''){
    return `<article class="metric v124-career-metric" ${id?`id="${id}"`:''}><span>${icon}</span><small>${esc(label)}</small><b>${esc(value)}</b><em>${esc(note)}</em></article>`;
  }

  function renderUsers(users,id){
    const root=$(id);if(!root)return;
    root.innerHTML=users.length?users.map(user=>`<button class="user-item ${Number(user.user_id)===Number(runtime.state?.target?.user_id)?'selected':''}" data-user-id="${user.user_id}"><span class="user-avatar">${user.role?.emoji||'👤'}</span><span><b>${esc(user.full_name)}</b><small>${user.username?'@'+esc(user.username):'ID '+user.user_id} · ${esc(user.role?.title||'')}</small></span><strong>⭐ ${fmt(user.career_points)}<br>💰 ${fmt(user.points)}</strong></button>`).join(''):'<div class="empty">Участники не найдены.</div>';
  }

  function renderRoleGrid(rootId='roleGrid'){
    const root=$(rootId);if(!root)return;
    const target=runtime.state?.target;
    const presets=runtime.state?.role_presets||{};
    root.classList.add('v124-role-grid');
    root.innerHTML=Object.entries(presets).map(([key,role])=>`<button class="v124-role ${target?.role?.key===key?'active':''}" data-v124-role="${key}"><span>${role.emoji}</span><span><b>${esc(role.title)}</b><small>от ${fmt(role.points)}</small></span></button>`).join('');
  }

  function historyMarkup(items){
    return items.length?items.map(item=>{
      const delta=Number(item.delta||0),sign=delta>0?'+':'',cls=delta>0?'plus':delta<0?'minus':'';
      const when=item.created_at?new Date(Number(item.created_at)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
      return `<div class="v124-history-item"><span><b>${esc(item.reason||'Операция')}</b><small>${esc(item.source_type||'')} ${when}</small></span><strong class="${cls}">${sign}${fmt(delta)}</strong></div>`;
    }).join(''):'<div class="empty">История пока пуста.</div>';
  }

  function renderCareer(){
    installUi();
    const state=runtime.state;if(!state)return;
    const target=state.target,chat=state.selected_chat||{},today=state.today||{};
    const version=$('versionText');if(version)version.textContent='Reality 124 · Полная панель';

    if(target){
      const avatar=$('targetAvatar');if(avatar)avatar.textContent=target.role?.emoji||'👤';
      const name=$('targetName');if(name)name.textContent=target.full_name||'Участник';
      const meta=$('targetMeta');if(meta)meta.textContent=`${target.role?.emoji||''} ${target.role?.title||''} · ⭐ ${fmt(target.career_points)} · 💰 ${fmt(target.points)}`;
      const pointsSubtitle=$('pointsSubtitle');if(pointsSubtitle)pointsSubtitle.textContent=`Обычный баланс: ${fmt(target.points)}`;

      const cards=[...document.querySelectorAll('#participantMetrics .metric')];
      if(cards[0]){
        const icon=cards[0].querySelector('span'),label=cards[0].querySelector('small'),value=cards[0].querySelector('b'),note=cards[0].querySelector('em');
        if(icon)icon.textContent=target.role.emoji;if(label)label.textContent='Постоянная роль';if(value)value.textContent=target.role.title;if(note)note.textContent=`порог от ${fmt(target.role.floor)}`;
      }
      if(cards[1]){
        const label=cards[1].querySelector('small'),value=cards[1].querySelector('b'),note=cards[1].querySelector('em');
        if(label)label.textContent='Обычное влияние';if(value)value.textContent=fmt(target.points);if(note)note.textContent='ставки, переводы и займы';
      }
      let careerMetric=$('v124ParticipantCareer');
      if(!careerMetric&&$('participantMetrics')){
        $('participantMetrics').insertAdjacentHTML('beforeend',metricCard('⭐','Карьерное влияние',fmt(target.career_points),target.role.next_title?`до ${target.role.next_title}: ${fmt(target.role.remaining)}`:'высшая роль','v124ParticipantCareer'));
      }else if(careerMetric){
        careerMetric.querySelector('b').textContent=fmt(target.career_points);
        careerMetric.querySelector('em').textContent=target.role.next_title?`до ${target.role.next_title}: ${fmt(target.role.remaining)}`:'высшая роль';
      }

      const progress=Math.round(Number(target.role?.progress||0)*100);
      if($('v124CareerBar'))$('v124CareerBar').style.width=`${progress}%`;
      if($('v124CareerProgress'))$('v124CareerProgress').textContent=target.role.next_title?`${target.role.emoji} ${target.role.title} · ${progress}% · до «${target.role.next_title}» осталось ${fmt(target.role.remaining)}`:`${target.role.emoji} ${target.role.title} · достигнута высшая роль`;
      if($('v124CareerExact')&&!$('v124CareerExact').matches(':focus'))$('v124CareerExact').value=String(target.career_points);
    }

    let homeCareer=$('v124HomeCareer');
    if(!homeCareer&&$('homeMetrics'))$('homeMetrics').insertAdjacentHTML('beforeend',metricCard('⭐','Карьерное влияние',fmt(chat.career_total||0),`сегодня +${fmt(today.career||0)}`,'v124HomeCareer'));
    else if(homeCareer){homeCareer.querySelector('b').textContent=fmt(chat.career_total||0);homeCareer.querySelector('em').textContent=`сегодня +${fmt(today.career||0)}`}

    renderUsers(state.quick_users||[],'quickUsers');
    renderRoleGrid('roleGrid');renderRoleGrid('v124CareerRoles');

    const hero=$('v124CareerHero');
    if(hero)hero.innerHTML=target?`<article class="v124-career-hero"><div class="v124-career-head"><div class="v124-career-icon">${target.role.emoji}</div><div><small>ПОСТОЯННАЯ РОЛЬ</small><b>${esc(target.role.title)}</b></div></div><div class="v124-career-grid"><div class="v124-career-stat"><small>КАРЬЕРНОЕ ВЛИЯНИЕ</small><b>${fmt(target.career_points)}</b></div><div class="v124-career-stat"><small>ОБЫЧНЫЙ БАЛАНС</small><b>${fmt(target.points)}</b></div><div class="v124-career-stat"><small>ДО СЛЕДУЮЩЕЙ РОЛИ</small><b>${target.role.next_title?fmt(target.role.remaining):'0'}</b></div><div class="v124-career-stat"><small>НАЧИСЛЕНО СЕГОДНЯ</small><b>+${fmt(today.career||0)}</b></div></div></article>`:'<div class="empty">Выбери участника.</div>';
    if($('v124CareerHistory'))$('v124CareerHistory').innerHTML=historyMarkup(state.career_history||[]);
    if($('v124WalletHistory'))$('v124WalletHistory').innerHTML=historyMarkup(state.wallet_history||[]);
  }

  function scheduleRender(){clearTimeout(runtime.renderTimer);runtime.renderTimer=setTimeout(renderCareer,80)}

  async function careerAction(action,extra={}){
    const ids=selectedIds();
    if(!ids.chat_id||!ids.user_id){toast('Сначала выбери беседу и участника.','error');return}
    if(runtime.busy)return;
    runtime.busy=true;
    try{
      const data=await request('/admin-v123/api/action',{method:'POST',body:JSON.stringify({action,...ids,...extra})});
      toast(data.message||'Готово.','success');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      document.getElementById('refreshButton')?.click();
      await loadCareer(ids.chat_id,ids.user_id,true);
    }catch(error){
      toast(error.message||'Действие не выполнено.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }finally{runtime.busy=false}
  }

  document.addEventListener('click',event=>{
    const delta=event.target.closest('[data-v124-delta]');
    if(delta){event.preventDefault();event.stopPropagation();careerAction('career_delta',{value:Number(delta.dataset.v124Delta||0)});return}
    const exact=event.target.closest('[data-v124-set]');
    if(exact){event.preventDefault();event.stopPropagation();const value=Number(String($('v124CareerExact')?.value||'').replace(/\s/g,''));if(!Number.isFinite(value)||value<0){toast('Введи корректное неотрицательное число.','error');return}careerAction('career_set',{value:Math.trunc(value)});return}
    const role=event.target.closest('[data-v124-role]');
    if(role){event.preventDefault();event.stopPropagation();const spec=runtime.state?.role_presets?.[role.dataset.v124Role];if(!spec)return;if(confirm(`Назначить роль «${spec.title}»? Обычный баланс не изменится.`))careerAction('role_set',{role:role.dataset.v124Role});return}
    if(event.target.closest('#v124Refresh')){const ids=selectedIds();loadCareer(ids.chat_id,ids.user_id);return}
  },true);

  document.addEventListener('DOMContentLoaded',()=>{
    installUi();
    const ids=selectedIds();if(ids.chat_id)loadCareer(ids.chat_id,ids.user_id,true);
    clearInterval(runtime.searchTimer);
    runtime.searchTimer=setInterval(()=>{if(document.querySelector('[data-screen="career124"].active')){const current=selectedIds();loadCareer(current.chat_id,current.user_id,true)}},30000);
  });

  installUi();
})();
