(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const previousFetch=window.fetch.bind(window);
  const runtime={chatId:0,state:null,busy:false,timer:null};
  window.RealityEventsV96=runtime;

  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({
    '&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'
  }[char]));
  const remain=seconds=>{
    const value=Math.max(0,Number(seconds)||0);
    const h=Math.floor(value/3600),m=Math.floor(value%3600/60);
    return h?`${h} ч ${m} мин`:`${m} мин`;
  };

  function sourceUrl(input){
    if(typeof input==='string'||input instanceof URL)return String(input);
    if(input instanceof Request)return input.url;
    return '';
  }

  window.fetch=async(input,init={})=>{
    const response=await previousFetch(input,init);
    const url=sourceUrl(input);
    if(url.includes('/admin-v76/api/state')){
      response.clone().json().then(data=>{
        const chatId=Number(data?.selected_chat?.chat_id||0);
        if(chatId){runtime.chatId=chatId;loadState(chatId,true)}
      }).catch(()=>{});
    }
    return response;
  };

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=text;
    node.className=`toast show ${type}`;
    clearTimeout(node.__v96Timer);
    node.__v96Timer=setTimeout(()=>node.className='toast',3600);
  }

  function installStyles(){
    if(document.getElementById('v96EventStyles'))return;
    const style=document.createElement('style');
    style.id='v96EventStyles';
    style.textContent=`
      .bottom-nav{overflow-x:auto;justify-content:flex-start;scrollbar-width:none}.bottom-nav::-webkit-scrollbar{display:none}.bottom-nav>button{min-width:59px;flex:1 0 59px}
      .v96-event-hero{position:relative;overflow:hidden;border:1px solid #654889;border-radius:21px;padding:17px;background:radial-gradient(circle at 100% 0,#8e52cd44,transparent 42%),linear-gradient(150deg,#261838,#0e0a16);box-shadow:0 18px 46px #0008;margin-bottom:12px}
      .v96-event-hero:before{content:"";position:absolute;width:160px;height:160px;right:-75px;top:-78px;border-radius:50%;background:#bd75ff24;filter:blur(13px)}
      .v96-event-head{position:relative;display:flex;gap:12px;align-items:center}.v96-event-icon{width:54px;height:54px;display:grid;place-items:center;border:1px solid #8962aa;border-radius:17px;background:#321c48;font-size:27px;box-shadow:0 0 24px #9c55d344}
      .v96-event-head small,.v96-event-head b{display:block}.v96-event-head small{color:#d3a7ff;font-size:9px;font-weight:900;letter-spacing:.14em}.v96-event-head b{font-size:18px;margin-top:4px}.v96-event-status{margin-left:auto;padding:6px 9px;border:1px solid #6f5190;border-radius:999px;color:#d9bcf7;background:#241533;font-size:8px;font-weight:900}
      .v96-description{position:relative;margin:14px 0 10px;color:#b9adc3;font-size:11px;line-height:1.55}.v96-progress-row{display:flex;justify-content:space-between;align-items:end;position:relative}.v96-progress-row small,.v96-progress-row b{display:block}.v96-progress-row small{color:#8e8099;font-size:8px;letter-spacing:.1em}.v96-progress-row b{font-size:24px;color:#f2d894}.v96-progress-row strong{font-size:11px;color:#cbbdd3}.v96-progress{height:9px;margin-top:8px;border:1px solid #473356;border-radius:999px;background:#08060c;overflow:hidden}.v96-progress i{display:block;height:100%;width:0;background:linear-gradient(90deg,#7a3fc0,#d18cff);transition:width .35s ease}
      .v96-empty{padding:22px 14px;text-align:center;border:1px dashed #44334e;border-radius:18px;color:#897c93;background:#0d0912}.v96-empty b{display:block;color:#d8cce0;font-size:15px;margin-bottom:6px}
      .v96-control-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.v96-control-grid .full{grid-column:1/-1}.v96-event-select{width:100%;min-height:50px;border:1px solid #4d3860;border-radius:14px;background:#0b0811;color:#f1e8f7;padding:0 12px;font-weight:800;margin-bottom:9px}
      .v96-action{min-height:47px;border:1px solid #523a67;border-radius:13px;background:linear-gradient(180deg,#241631,#130d1c);color:#ddd0e5;font-weight:900;font-size:10px}.v96-action.primary{background:linear-gradient(135deg,#b66eff,#7131ba);border-color:#c996f1;color:white;box-shadow:0 9px 24px #7131ba38}.v96-action.good{border-color:#39735e;background:linear-gradient(180deg,#174132,#0b231b);color:#b7ffda}.v96-action.warn{border-color:#80642e;background:linear-gradient(180deg,#4c3918,#291e0d);color:#ffe3a1}.v96-action.danger{border-color:#754052;background:linear-gradient(180deg,#3d1d29,#211018);color:#ffc4d5}
      .v96-setting-row{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px;border:1px solid #3d2c48;border-radius:14px;background:#0d0913;margin-top:9px}.v96-setting-row b,.v96-setting-row small{display:block}.v96-setting-row b{font-size:12px}.v96-setting-row small{font-size:9px;color:#8d8194;margin-top:3px}.v96-switch{width:51px;height:29px;border:1px solid #523d60;border-radius:999px;background:#17101e;padding:3px}.v96-switch i{display:block;width:21px;height:21px;border-radius:50%;background:#766881;transition:.2s}.v96-switch.on{border-color:#3c8b6a;background:#153a2c}.v96-switch.on i{transform:translateX(20px);background:#76efb4}
      .v96-tax-table{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:10px}.v96-tax-item{padding:9px;border:1px solid #513645;border-radius:11px;background:#160c12}.v96-tax-item small,.v96-tax-item b{display:block}.v96-tax-item small{font-size:8px;color:#b695a2}.v96-tax-item b{font-size:13px;color:#ffacc4;margin-top:2px}
      .v96-participants{display:grid;gap:7px}.v96-person{display:grid;grid-template-columns:1fr auto;gap:9px;align-items:center;padding:10px 11px;border:1px solid #372a40;border-radius:13px;background:#0d0912}.v96-person b,.v96-person small{display:block}.v96-person b{font-size:11px}.v96-person small{font-size:8px;color:#8d8194;margin-top:3px}.v96-person strong{color:#ebd395;font-size:12px}.v96-person em{display:block;color:#7fe5bd;font-size:8px;font-style:normal;text-align:right;margin-top:2px}
      .v96-history{display:grid;gap:7px}.v96-history-item{padding:11px;border:1px solid #372a40;border-radius:13px;background:#0d0912}.v96-history-item header{display:flex;justify-content:space-between;gap:10px}.v96-history-item b{font-size:11px}.v96-history-item time{font-size:8px;color:#817588}.v96-history-item p{font-size:9px;color:#9c8fa5;line-height:1.45;margin:6px 0 0}.v96-history-item.completed{border-color:#315f4e}.v96-history-item.failed,.v96-history-item.cancelled{border-color:#603746}
      @media(max-width:380px){.v96-control-grid{grid-template-columns:1fr}.v96-control-grid .full{grid-column:auto}.v96-tax-table{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);
  }

  function installScreen(){
    if(document.querySelector('[data-screen="events"]'))return;
    const history=document.querySelector('[data-screen="history"]');
    if(!history)return;
    const screen=document.createElement('section');
    screen.className='screen';
    screen.dataset.screen='events';
    screen.innerHTML=`
      <div class="section-head"><div><small>СОБЫТИЕ ДНЯ</small><h2>Событие реальности</h2></div><button class="mini-button" id="v96Refresh">Обновить</button></div>
      <div id="v96Current"></div>
      <article class="panel">
        <div class="panel-title"><span>🎛</span><div><b>Управление событием</b><small>Запуск, досрочное завершение и ручная награда</small></div></div>
        <select class="v96-event-select" id="v96EventSelect"></select>
        <div class="v96-control-grid">
          <button class="v96-action primary" data-v96-action="event_start">▶ ЗАПУСТИТЬ ВЫБРАННОЕ</button>
          <button class="v96-action" data-v96-action="event_start_random">🎲 СЛУЧАЙНОЕ</button>
          <button class="v96-action warn" data-v96-action="event_reroll">🔄 ПЕРЕВЫБРАТЬ</button>
          <button class="v96-action good" data-v96-action="event_finish">🏁 ЗАВЕРШИТЬ ПО УСЛОВИЯМ</button>
          <button class="v96-action good" data-v96-action="event_reward">🎁 НАЧИСЛИТЬ НАГРАДЫ</button>
          <button class="v96-action danger" data-v96-action="event_cancel">🛑 ОТМЕНИТЬ БЕЗ НАГРАД</button>
          <button class="v96-action full" data-v96-action="event_pin">📌 ЗАКРЕПИТЬ НА ЗАВТРА</button>
        </div>
        <div class="v96-setting-row"><div><b>Автоматический запуск</b><small>Каждый день примерно в 10:00 UTC</small></div><button class="v96-switch" id="v96AutoToggle" type="button"><i></i></button></div>
      </article>
      <article class="panel"><div class="panel-title"><span>👥</span><div><b>Участники события</b><small>Вклад, выполнение условий и полученные награды</small></div></div><div class="v96-participants" id="v96Participants"></div></article>
      <article class="panel"><div class="panel-title"><span>📜</span><div><b>История событий</b><small>Последние двадцать запусков выбранной беседы</small></div></div><div class="v96-history" id="v96History"></div></article>`;
    history.parentNode.insertBefore(screen,history);

    const nav=document.querySelector('.bottom-nav');
    const historyButton=nav?.querySelector('[data-tab="history"]');
    if(nav&&!nav.querySelector('[data-tab="events"]')){
      const button=document.createElement('button');
      button.dataset.tab='events';
      button.innerHTML='<span>🌠</span><small>Событие</small>';
      nav.insertBefore(button,historyButton||null);
    }
  }

  function selectedChat(){
    return Number(runtime.chatId||localStorage.getItem('admin76Chat')||0);
  }

  async function loadState(chatId=selectedChat(),silent=false){
    if(!chatId)return;
    try{
      const response=await previousFetch(`/events-v96/api/state?chat_id=${chatId}`,{
        cache:'no-store',headers:{'X-Telegram-Init-Data':tg?.initData||''}
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Некорректный ответ сервера.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось загрузить события.');
      runtime.chatId=chatId;runtime.state=data;render();
    }catch(error){if(!silent)toast(error.message||'Не удалось загрузить события.','error')}
  }

  async function action(name){
    const chatId=selectedChat();
    if(!chatId){toast('Сначала выбери беседу.','error');return}
    if(runtime.busy)return;
    runtime.busy=true;
    document.querySelectorAll('[data-v96-action]').forEach(button=>button.disabled=true);
    try{
      const select=document.getElementById('v96EventSelect');
      const body={action:name,chat_id:chatId,event_key:select?.value||''};
      if(name==='event_toggle')body.enabled=!Boolean(runtime.state?.settings?.enabled);
      const response=await previousFetch('/events-v96/api/action',{
        method:'POST',headers:{'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''},body:JSON.stringify(body)
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Некорректный ответ сервера.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      toast(data.message||'Готово.','success');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      await loadState(chatId,true);
    }catch(error){
      toast(error.message||'Действие не выполнено.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }finally{
      runtime.busy=false;
      document.querySelectorAll('[data-v96-action]').forEach(button=>button.disabled=false);
    }
  }

  function progressNote(event){
    const key=event?.event_key;
    if(key==='collective')return 'карьерного влияния собрано';
    if(key==='game_night')return 'забегов засчитано';
    if(key==='boss_fall')return 'боссов побеждено';
    if(key==='tree_awakening')return 'игроков завершили испытание';
    return 'прогресс события';
  }

  function renderCurrent(){
    const root=document.getElementById('v96Current');
    if(!root)return;
    const event=runtime.state?.event;
    if(!event){
      root.innerHTML='<div class="v96-empty"><b>Событие сейчас не идёт</b>Запусти выбранное событие вручную или дождись ежедневного автоматического выбора.</div>';
      return;
    }
    const info=event.info||{};
    const target=Math.max(0,Number(event.target)||0),progress=Math.max(0,Number(event.progress)||0);
    const percent=target?Math.max(0,Math.min(100,progress/target*100)):100;
    const tax=event.event_key==='ego_tax'?`<div class="v96-tax-table"><div class="v96-tax-item"><small>ДЕКОРАЦИЯ И ПЫЛЬ</small><b>−50</b></div><div class="v96-tax-item"><small>МАССОВКА</small><b>−100</b></div><div class="v96-tax-item"><small>ВТОРОСТЕПЕННАЯ</small><b>−150</b></div><div class="v96-tax-item"><small>ГЛАВНЫЙ ГЕРОЙ</small><b>−200</b></div></div>`:'';
    root.innerHTML=`<article class="v96-event-hero"><div class="v96-event-head"><div class="v96-event-icon">${esc(info.emoji||'🌠')}</div><div><small>ТЕКУЩЕЕ СОБЫТИЕ</small><b>${esc(info.title||event.event_key)}</b></div><span class="v96-event-status">${event.forced?'РУЧНОЙ ЗАПУСК':'АВТОМАТИЧЕСКОЕ'}</span></div><p class="v96-description">${esc(info.description||'')}</p>${target?`<div class="v96-progress-row"><div><small>${esc(progressNote(event).toUpperCase())}</small><b>${fmt(progress)} / ${fmt(target)}</b></div><strong>${remain(Number(event.ends_at)-Date.now()/1000)}</strong></div><div class="v96-progress"><i style="width:${percent}%"></i></div>`:`<div class="v96-progress-row"><div><small>ДЕЙСТВУЕТ ЕЩЁ</small><b>${remain(Number(event.ends_at)-Date.now()/1000)}</b></div><strong>24 часа</strong></div>`}${tax}</article>`;
  }

  function participantStats(person,eventKey){
    if(eventKey==='collective')return `Вклад: ${fmt(person.contribution)}`;
    if(eventKey==='game_night')return `Забеги: ${fmt(person.game_runs)}/5`;
    if(eventKey==='ego_tax')return `Налог: ${fmt(person.tax_amount)} · ${person.tax_refunded?'возвращён':'не возвращён'}`;
    if(eventKey==='influence_day')return `Бонус дня: +${fmt(person.event_bonus)}/500`;
    if(eventKey==='tree_awakening')return `${person.influence_done?'✅':'⬜'} влияние · ${person.task_done?'✅':'⬜'} задание · ${(person.game_runs>0||person.boss_attacks>=5)?'✅':'⬜'} игра/босс`;
    if(eventKey==='boss_fall')return `Удары: ${fmt(person.boss_attacks)} · урон: ${fmt(person.boss_damage)}`;
    return 'Участник события';
  }

  function renderParticipants(){
    const root=document.getElementById('v96Participants');
    if(!root)return;
    const eventKey=runtime.state?.event?.event_key||'';
    const people=runtime.state?.participants||[];
    root.innerHTML=people.length?people.map(person=>`<div class="v96-person"><div><b>${esc(person.full_name||`ID ${person.user_id}`)}</b><small>${esc(participantStats(person,eventKey))}</small></div><div><strong>+${fmt(person.reward_influence||0)}</strong><em>${person.reward_tree?`+${fmt(person.reward_tree)} Древо`:person.completed?'выполнено':''}</em></div></div>`).join(''):'<div class="empty">Участников пока нет.</div>';
  }

  function renderHistory(){
    const root=document.getElementById('v96History');
    if(!root)return;
    const items=runtime.state?.history||[];
    root.innerHTML=items.length?items.map(item=>`<article class="v96-history-item ${esc(item.status)}"><header><b>${esc(item.info?.emoji||'🌠')} ${esc(item.info?.title||item.event_key)}</b><time>${new Date(Number(item.starts_at)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}</time></header><p>${esc(item.result_text||`${fmt(item.progress)}/${fmt(item.target)} · ${item.status}`)}</p></article>`).join(''):'<div class="empty">История пока пуста.</div>';
  }

  function renderControls(){
    const definitions=runtime.state?.definitions||{};
    const select=document.getElementById('v96EventSelect');
    if(select){
      const current=select.value;
      select.innerHTML=Object.values(definitions).map(item=>`<option value="${esc(item.key)}">${esc(item.emoji)} ${esc(item.title)}</option>`).join('');
      if(definitions[current])select.value=current;
      else if(runtime.state?.settings?.pinned_event&&definitions[runtime.state.settings.pinned_event])select.value=runtime.state.settings.pinned_event;
    }
    const toggle=document.getElementById('v96AutoToggle');
    toggle?.classList.toggle('on',Boolean(runtime.state?.settings?.enabled));
    const pin=document.querySelector('[data-v96-action="event_pin"]');
    if(pin){
      const pinned=runtime.state?.settings?.pinned_event;
      pin.textContent=pinned?`📌 ЗАВТРА: ${definitions[pinned]?.title||pinned}`:'📌 ЗАКРЕПИТЬ НА ЗАВТРА';
    }
  }

  function render(){
    installStyles();installScreen();renderCurrent();renderControls();renderParticipants();renderHistory();
    const version=document.getElementById('versionText');
    if(version)version.textContent='Reality 96 · События';
  }

  document.addEventListener('click',event=>{
    const button=event.target.closest('[data-v96-action]');
    if(button){action(button.dataset.v96Action);return}
    if(event.target.closest('#v96AutoToggle')){action('event_toggle');return}
    if(event.target.closest('#v96Refresh')){loadState(selectedChat());return}
  },true);

  document.addEventListener('DOMContentLoaded',()=>{
    installStyles();installScreen();
    const chatId=selectedChat();if(chatId)loadState(chatId,true);
    clearInterval(runtime.timer);runtime.timer=setInterval(()=>{if(document.querySelector('[data-screen="events"].active'))loadState(selectedChat(),true)},30000);
  });
})();
