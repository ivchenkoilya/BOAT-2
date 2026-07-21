(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const previousFetch=window.fetch.bind(window);
  const runtime={chatId:0,userId:0,state:null,busy:false,timer:null,types:new Set(['gambling'])};
  window.SanctionsAdminV126=runtime;
  const $=id=>document.getElementById(id);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);

  function sourceUrl(input){
    if(typeof input==='string'||input instanceof URL)return String(input);
    if(input instanceof Request)return input.url;
    return '';
  }

  function toast(text,type='success'){
    const node=$('toast');if(!node)return;
    node.textContent=text;node.className=`toast show ${type}`;
    clearTimeout(node.__san126Timer);node.__san126Timer=setTimeout(()=>node.className='toast',3600);
  }

  async function request(url,options={}){
    const response=await previousFetch(url,{cache:'no-store',...options,headers:{'X-Telegram-Init-Data':tg?.initData||'',...(options.headers||{})}});
    const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
    if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
    return data;
  }

  window.fetch=async(input,init={})=>{
    const response=await previousFetch(input,init);
    if(sourceUrl(input).includes('/admin-v76/api/state')){
      response.clone().json().then(data=>{
        if(!data?.ok)return;
        runtime.chatId=Number(data.selected_chat?.chat_id||0);
        runtime.userId=Number(data.target?.user_id||0);
        if(runtime.chatId&&runtime.userId)load(true);else{runtime.state=null;render()}
      }).catch(()=>{});
    }
    return response;
  };

  function installStyles(){
    if($('san126Styles'))return;
    const style=document.createElement('style');style.id='san126Styles';style.textContent=`
      .san126-hero{position:relative;overflow:hidden;padding:17px;border:1px solid #823f56;border-radius:22px;background:radial-gradient(circle at 100% 0,#ff5e8833,transparent 43%),linear-gradient(150deg,#32131e,#0e090d);box-shadow:0 18px 45px #0008;margin-bottom:12px}.san126-hero:before{content:"";position:absolute;width:170px;height:170px;right:-80px;top:-90px;border-radius:50%;background:#ff587c22;filter:blur(14px)}
      .san126-head{position:relative;display:flex;align-items:center;gap:12px}.san126-icon{width:56px;height:56px;display:grid;place-items:center;border:1px solid #a14e68;border-radius:18px;background:#491827;font-size:28px}.san126-head small,.san126-head b{display:block}.san126-head small{font-size:9px;color:#ff98ae;font-weight:900;letter-spacing:.15em}.san126-head b{font-size:19px;margin-top:4px}.san126-count{margin-left:auto;padding:7px 10px;border:1px solid #8d465c;border-radius:999px;background:#32101b;color:#ffc1cf;font-size:9px;font-weight:900}
      .san126-types{display:grid;grid-template-columns:1fr 1fr;gap:8px}.san126-type{display:flex;align-items:center;gap:9px;min-height:64px;padding:10px;border:1px solid #49303a;border-radius:15px;background:#100a0d;color:#f6edf0;text-align:left}.san126-type.selected{border-color:#e06182;background:linear-gradient(145deg,#542031,#281018);box-shadow:0 0 22px #d34e7530}.san126-type>span{font-size:23px}.san126-type b,.san126-type small{display:block}.san126-type b{font-size:10px}.san126-type small{font-size:8px;color:#aa929a;margin-top:3px;line-height:1.35}
      .san126-field{display:grid;gap:6px;margin-top:11px}.san126-field label{font-size:9px;color:#a9959d;font-weight:800}.san126-field select,.san126-field textarea{width:100%;border:1px solid #583642;border-radius:14px;background:#0c080a;color:#f7edf0;padding:11px;outline:none}.san126-field select{min-height:49px}.san126-field textarea{min-height:83px;resize:vertical;font-family:inherit;line-height:1.45}
      .san126-presets{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}.san126-button{min-height:47px;border:1px solid #663747;border-radius:13px;background:linear-gradient(180deg,#3b1723,#1d0c12);color:#ffd9e2;font-weight:900;font-size:9px}.san126-button.primary{width:100%;min-height:55px;margin-top:10px;border-color:#e06a89;background:linear-gradient(135deg,#dd4e75,#8b2744);color:white;box-shadow:0 12px 28px #b832593d}.san126-button.good{border-color:#34715a;background:linear-gradient(180deg,#164332,#0b231b);color:#baffdc}
      .san126-list{display:grid;gap:8px}.san126-item{padding:12px;border:1px solid #4b3039;border-radius:15px;background:#0e090c}.san126-item.active{border-color:#7f4054;background:linear-gradient(145deg,#251017,#10090c)}.san126-item header{display:flex;gap:9px;align-items:center}.san126-item header>span{font-size:22px}.san126-item header div{flex:1}.san126-item b,.san126-item small{display:block}.san126-item b{font-size:11px}.san126-item small{font-size:8px;color:#a28e95;margin-top:3px}.san126-item p{margin:9px 0;color:#c0aeb4;font-size:9px;line-height:1.45}.san126-item footer{display:flex;justify-content:space-between;align-items:center;gap:8px}.san126-status{font-size:8px;font-weight:900;color:#ff9db2}.san126-revoke{min-height:35px;border:1px solid #34715a;border-radius:10px;background:#102b21;color:#aaffd5;padding:6px 10px;font-size:8px;font-weight:900}.san126-empty{padding:20px;text-align:center;border:1px dashed #49313a;border-radius:16px;color:#9d8991;background:#0d090b;font-size:9px}.san126-note{padding:11px;border:1px solid #684a23;border-radius:13px;background:#2b1e0b;color:#ffe3a5;font-size:9px;line-height:1.5;margin-top:10px}
      @media(max-width:380px){.san126-types{grid-template-columns:1fr}.san126-presets{grid-template-columns:1fr}}
    `;document.head.appendChild(style);
  }

  function installScreen(){
    installStyles();
    if(document.querySelector('[data-screen="sanctions126"]'))return;
    const history=document.querySelector('[data-screen="history"]');if(!history)return;
    const screen=document.createElement('section');screen.className='screen';screen.dataset.screen='sanctions126';screen.innerHTML=`
      <div class="section-head"><div><small>НАДЗОР</small><h2>Санкции участника</h2></div><button class="mini-button" id="san126Refresh">Обновить</button></div>
      <div id="san126Hero"></div>
      <article class="panel requires-user">
        <div class="panel-title"><span>🚫</span><div><b>Ввести ограничения</b><small>Выбери один или несколько видов санкций</small></div></div>
        <div class="san126-types" id="san126Types"></div>
        <div class="san126-field"><label>Срок постановления</label><select id="san126Duration"></select></div>
        <div class="san126-field"><label>Причина</label><textarea id="san126Reason" placeholder="Например: злоупотребление ставками или использование бага"></textarea></div>
        <div class="san126-presets"><button class="san126-button" data-san126-preset="gambling">🎲 Ставки на сутки</button><button class="san126-button" data-san126-preset="finance">💸 Финансы на 3 дня</button><button class="san126-button" data-san126-preset="full">🔒 Полный бан на сутки</button><button class="san126-button good" id="san126Clear">✅ Снять все санкции</button></div>
        <button class="san126-button primary" id="san126Issue">🚨 ОПУБЛИКОВАТЬ ПОСТАНОВЛЕНИЕ</button>
        <div class="san126-note">После подтверждения бот сразу опубликует официальное сообщение в группе от имени <b>Надзора за гандонами</b>.</div>
      </article>
      <article class="panel"><div class="panel-title"><span>⛔</span><div><b>Активные санкции</b><small>Срок, причина и досрочное снятие</small></div></div><div class="san126-list" id="san126Active"></div></article>
      <article class="panel"><div class="panel-title"><span>📜</span><div><b>История постановлений</b><small>Выданные, истёкшие и отменённые ограничения</small></div></div><div class="san126-list" id="san126History"></div></article>`;
    history.parentNode.insertBefore(screen,history);
    const nav=document.querySelector('.bottom-nav');const historyButton=nav?.querySelector('[data-tab="history"]');
    if(nav&&!nav.querySelector('[data-tab="sanctions126"]')){const button=document.createElement('button');button.dataset.tab='sanctions126';button.innerHTML='<span>🚫</span><small>Санкции</small>';nav.insertBefore(button,historyButton||null)}
  }

  async function load(silent=false){
    installScreen();
    if(!runtime.chatId||!runtime.userId){runtime.state=null;render();return}
    try{runtime.state=await request(`/sanctions-v126/api/state?chat_id=${runtime.chatId}&user_id=${runtime.userId}`);render()}
    catch(error){if(!silent)toast(error.message||'Не удалось загрузить санкции.','error')}
  }

  function renderTypes(){
    const root=$('san126Types');if(!root)return;
    const types=runtime.state?.types||{};
    root.innerHTML=Object.entries(types).map(([key,item])=>`<button class="san126-type ${runtime.types.has(key)?'selected':''}" data-san126-type="${key}"><span>${item.emoji}</span><span><b>${esc(item.title)}</b><small>${esc(item.short)}</small></span></button>`).join('');
    const duration=$('san126Duration');if(duration&&runtime.state?.durations){const current=duration.value||'86400';duration.innerHTML=runtime.state.durations.map(item=>`<option value="${item.seconds}">${esc(item.title)}</option>`).join('');duration.value=[...duration.options].some(x=>x.value===current)?current:'86400'}
  }

  function activeMarkup(items){
    return items.length?items.map(item=>`<div class="san126-item active"><header><span>${item.emoji}</span><div><b>${esc(item.title)}</b><small>${item.remaining} · до ${item.expires_at?new Date(item.expires_at*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'отдельного решения'}</small></div></header><p>${esc(item.reason)}</p><footer><span class="san126-status">ДЕЙСТВУЕТ</span><button class="san126-revoke" data-san126-revoke="${item.id}">Снять досрочно</button></footer></div>`).join(''):'<div class="san126-empty">У выбранного участника нет активных санкций.</div>';
  }

  function historyMarkup(items){
    return items.length?items.slice(0,30).map(item=>{const active=Boolean(item.active)&&(Number(item.expires_at)===0||Number(item.expires_at)>Date.now()/1000);const status=active?'ДЕЙСТВУЕТ':item.revoke_reason||'ЗАВЕРШЕНО';return `<div class="san126-item ${active?'active':''}"><header><span>${item.emoji}</span><div><b>${esc(item.title)}</b><small>${new Date(item.issued_at*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}</small></div></header><p>${esc(item.reason)}</p><footer><span class="san126-status">${esc(status)}</span><small>#${item.id}</small></footer></div>`}).join(''):'<div class="san126-empty">История санкций пока пуста.</div>';
  }

  function render(){
    installScreen();const state=runtime.state,active=state?.active||[];
    const hero=$('san126Hero');if(hero)hero.innerHTML=runtime.userId?`<article class="san126-hero"><div class="san126-head"><div class="san126-icon">⚖️</div><div><small>НАДЗОР ЗА ГАНДОНАМИ</small><b>${active.length?'Ограничения действуют':'Нарушений не зафиксировано'}</b></div><span class="san126-count">${fmt(active.length)} АКТИВНЫХ</span></div></article>`:'<div class="san126-empty">Сначала выбери участника.</div>';
    renderTypes();if($('san126Active'))$('san126Active').innerHTML=activeMarkup(active);if($('san126History'))$('san126History').innerHTML=historyMarkup(state?.history||[]);
    document.querySelectorAll('[data-screen="sanctions126"] .requires-user').forEach(node=>node.classList.toggle('disabled',!runtime.userId));
  }

  async function action(payload){
    if(runtime.busy)return;if(!runtime.chatId||!runtime.userId){toast('Сначала выбери участника.','error');return}
    runtime.busy=true;
    try{const data=await request('/sanctions-v126/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({chat_id:runtime.chatId,user_id:runtime.userId,...payload})});toast(data.message||'Готово.');tg?.HapticFeedback?.notificationOccurred?.('success');await load(true)}
    catch(error){toast(error.message||'Действие не выполнено.','error');tg?.HapticFeedback?.notificationOccurred?.('error')}
    finally{runtime.busy=false}
  }

  function preset(name){
    runtime.types.clear();
    if(name==='gambling'){runtime.types.add('gambling');$('san126Duration').value='86400';$('san126Reason').value='Злоупотребление ставками'}
    if(name==='finance'){runtime.types.add('finance');$('san126Duration').value='259200';$('san126Reason').value='Нарушение правил финансовой системы'}
    if(name==='full'){runtime.types.add('full_game');$('san126Duration').value='86400';$('san126Reason').value='Систематическое нарушение правил реальности'}
    renderTypes();
  }

  document.addEventListener('click',event=>{
    const type=event.target.closest('[data-san126-type]');if(type){event.preventDefault();const key=type.dataset.san126Type;if(key==='full_game'){runtime.types.clear();runtime.types.add(key)}else{runtime.types.delete('full_game');runtime.types.has(key)?runtime.types.delete(key):runtime.types.add(key)}renderTypes();return}
    const quick=event.target.closest('[data-san126-preset]');if(quick){preset(quick.dataset.san126Preset);return}
    const revoke=event.target.closest('[data-san126-revoke]');if(revoke){if(confirm('Досрочно снять эту санкцию и опубликовать сообщение в группе?'))action({action:'revoke',sanction_id:Number(revoke.dataset.san126Revoke)});return}
    if(event.target.closest('#san126Issue')){const reason=$('san126Reason').value.trim();if(!runtime.types.size){toast('Выбери вид санкций.','error');return}if(reason.length<3){toast('Укажи причину санкций.','error');return}const duration=Number($('san126Duration').value||0);if(confirm(`Ввести санкции на срок «${$('san126Duration').selectedOptions[0]?.textContent}» и опубликовать постановление?`))action({action:'issue',types:[...runtime.types],duration,reason});return}
    if(event.target.closest('#san126Clear')){if(confirm('Снять все активные санкции и сообщить об этом в группе?'))action({action:'revoke'});return}
    if(event.target.closest('#san126Refresh')){load();return}
  },true);

  document.addEventListener('DOMContentLoaded',()=>{installScreen();clearInterval(runtime.timer);runtime.timer=setInterval(()=>{if(document.querySelector('[data-screen="sanctions126"].active'))load(true)},30000)});
  installScreen();
})();
