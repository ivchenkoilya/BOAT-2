(()=>{
  'use strict';
  const tg=window.Telegram?.WebApp;
  const originalFetch=window.fetch.bind(window);
  const runtime={chatId:0,state:null,busy:false};
  window.FinanceAdminV112=runtime;
  const fmt=v=>new Intl.NumberFormat('ru-RU').format(Number(v)||0);
  const esc=v=>String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const remain=ts=>{
    const sec=Math.max(0,Number(ts||0)-Math.floor(Date.now()/1000));
    const d=Math.floor(sec/86400),h=Math.floor(sec%86400/3600);
    return d?`${d} д ${h} ч`:`${h} ч`;
  };
  function sourceUrl(input){
    if(typeof input==='string'||input instanceof URL)return String(input);
    if(input instanceof Request)return input.url;
    return '';
  }
  window.fetch=async(input,init={})=>{
    const response=await originalFetch(input,init);
    if(sourceUrl(input).includes('/admin-v76/api/state')){
      response.clone().json().then(data=>{
        const chatId=Number(data?.selected_chat?.chat_id||0);
        if(chatId){runtime.chatId=chatId;load(chatId,true)}
      }).catch(()=>{});
    }
    return response;
  };
  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=text;node.className=`toast show ${type}`;
    clearTimeout(node.__finTimer);node.__finTimer=setTimeout(()=>node.className='toast',3600);
  }
  function installStyles(){
    if(document.getElementById('fin112Styles'))return;
    const style=document.createElement('style');style.id='fin112Styles';style.textContent=`
      .fin112-hero{position:relative;overflow:hidden;border:1px solid #79612e;border-radius:22px;padding:16px;background:radial-gradient(circle at 100% 0,#f8ca4d33,transparent 42%),linear-gradient(150deg,#2b2110,#0d0a08);margin-bottom:12px;box-shadow:0 18px 44px #0008}
      .fin112-head{display:flex;gap:12px;align-items:center}.fin112-icon{width:54px;height:54px;display:grid;place-items:center;border:1px solid #ae8737;border-radius:17px;background:#3b2b10;font-size:28px}.fin112-head small,.fin112-head b{display:block}.fin112-head small{font-size:9px;letter-spacing:.15em;color:#d8b95f;font-weight:900}.fin112-head b{font-size:19px;margin-top:4px}.fin112-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:13px}.fin112-metric{padding:11px;border:1px solid #594522;border-radius:13px;background:#100d09}.fin112-metric small,.fin112-metric b{display:block}.fin112-metric small{font-size:8px;color:#9c8a68}.fin112-metric b{font-size:18px;color:#f2d27c;margin-top:3px}
      .fin112-list{display:grid;gap:8px}.fin112-item{padding:12px;border:1px solid #3c3045;border-radius:14px;background:#0d0912}.fin112-item.overdue{border-color:#7c344c;background:#1d0e14}.fin112-item header{display:flex;justify-content:space-between;gap:8px}.fin112-item b{font-size:11px}.fin112-item strong{font-size:11px;color:#f2d27c}.fin112-item p{font-size:9px;color:#9d90a5;line-height:1.45;margin:6px 0}.fin112-item footer{display:flex;justify-content:space-between;align-items:center;gap:8px}.fin112-item footer small{font-size:8px;color:#85798d}.fin112-forgive{border:1px solid #7b4255;border-radius:9px;background:#351620;color:#ffc1d3;padding:7px 9px;font-size:8px;font-weight:900}.fin112-empty{padding:18px;text-align:center;border:1px dashed #44364d;border-radius:15px;color:#918397}.fin112-warning{padding:11px;border:1px solid #7c6330;border-radius:13px;background:#2b210f;color:#ffe2a0;font-size:9px;line-height:1.45;margin-bottom:10px}
    `;document.head.appendChild(style);
  }
  function installScreen(){
    if(document.querySelector('[data-screen="finance"]'))return;
    const history=document.querySelector('[data-screen="history"]');if(!history)return;
    const screen=document.createElement('section');screen.className='screen';screen.dataset.screen='finance';screen.innerHTML=`
      <div class="section-head"><div><small>ЭКОНОМИКА</small><h2>Переводы и займы</h2></div><button class="mini-button" id="fin112Refresh">Обновить</button></div>
      <div id="fin112Summary"></div>
      <div id="fin112Warnings"></div>
      <article class="panel"><div class="panel-title"><span>🤝</span><div><b>Активные договоры</b><small>Займы, остатки и просрочки</small></div></div><div class="fin112-list" id="fin112Loans"></div></article>
      <article class="panel"><div class="panel-title"><span>💸</span><div><b>Последние переводы</b><small>Операции выбранной беседы</small></div></div><div class="fin112-list" id="fin112Transfers"></div></article>`;
    history.parentNode.insertBefore(screen,history);
    const nav=document.querySelector('.bottom-nav');const historyButton=nav?.querySelector('[data-tab="history"]');
    if(nav&&!nav.querySelector('[data-tab="finance"]')){const b=document.createElement('button');b.dataset.tab='finance';b.innerHTML='<span>💸</span><small>Финансы</small>';nav.insertBefore(b,historyButton||null)}
  }
  async function load(chatId=runtime.chatId,silent=false){
    if(!chatId)return;
    try{
      const r=await originalFetch(`/finance-v112/api/state?chat_id=${chatId}`,{cache:'no-store',headers:{'X-Telegram-Init-Data':tg?.initData||''}});
      const data=await r.json().catch(()=>({ok:false,reason:'Некорректный ответ сервера.'}));
      if(!r.ok||!data.ok)throw new Error(data.reason||'Не удалось загрузить финансы.');
      runtime.chatId=chatId;runtime.state=data;render();
    }catch(e){if(!silent)toast(e.message||'Не удалось загрузить финансы.','error')}
  }
  function cycleWarning(transfers){
    const recent=(transfers||[]).filter(x=>Number(x.completed_at||0)>Date.now()/1000-86400);
    for(const a of recent){for(const b of recent){if(a.sender_id===b.recipient_id&&a.recipient_id===b.sender_id&&a.transfer_id!==b.transfer_id)return '⚠️ Обнаружены встречные переводы между одними участниками за последние сутки. Проверь возможную прокрутку влияния.'}}
    return '';
  }
  function render(){
    installStyles();installScreen();const s=runtime.state?.summary||{};
    const summary=document.getElementById('fin112Summary');if(summary)summary.innerHTML=`<div class="fin112-hero"><div class="fin112-head"><div class="fin112-icon">🏦</div><div><small>ФИНАНСОВЫЙ ЦЕНТР</small><b>Экономика беседы</b></div></div><div class="fin112-grid"><div class="fin112-metric"><small>АКТИВНЫЕ ЗАЙМЫ</small><b>${fmt(s.active)}</b></div><div class="fin112-metric"><small>ПРОСРОЧЕННЫЕ</small><b>${fmt(s.overdue)}</b></div><div class="fin112-metric"><small>ОСТАТОК ДОЛГОВ</small><b>${fmt(s.debt_total)}</b></div><div class="fin112-metric"><small>ПЕРЕВОДЫ СЕГОДНЯ</small><b>${fmt(s.transfers_today)}</b></div></div></div>`;
    const warning=cycleWarning(runtime.state?.transfers);const warnings=document.getElementById('fin112Warnings');if(warnings)warnings.innerHTML=warning?`<div class="fin112-warning">${esc(warning)}</div>`:'';
    const loans=document.getElementById('fin112Loans');if(loans){const rows=runtime.state?.loans||[];loans.innerHTML=rows.length?rows.map(x=>`<div class="fin112-item ${x.status==='overdue'?'overdue':''}"><header><b>#${esc(x.token)} · ${esc(x.lender_name)} → ${esc(x.borrower_name)}</b><strong>${fmt(x.remaining)}</strong></header><p>Выдано ${fmt(x.principal)} под ${fmt(x.interest_percent)}%. Вернуть всего ${fmt(x.total_due)}.</p><footer><small>${x.status==='overdue'?'🔴 ПРОСРОЧЕН':`🟢 осталось ${remain(x.due_at)}`}</small><button class="fin112-forgive" data-fin112-forgive="${esc(x.loan_id)}">Простить долг</button></footer></div>`).join(''):'<div class="fin112-empty">Активных договоров нет.</div>'}
    const transfers=document.getElementById('fin112Transfers');if(transfers){const rows=runtime.state?.transfers||[];transfers.innerHTML=rows.length?rows.map(x=>`<div class="fin112-item"><header><b>${esc(x.sender_name)} → ${esc(x.recipient_name)}</b><strong>${fmt(x.amount)}</strong></header><p>Обычный перевод влияния. Не учитывается в карьерном прогрессе и Древе.</p></div>`).join(''):'<div class="fin112-empty">Переводов пока нет.</div>'}
  }
  async function forgive(loanId){
    if(runtime.busy||!runtime.chatId)return;if(!confirm('Простить весь оставшийся долг?'))return;runtime.busy=true;
    try{const r=await originalFetch('/finance-v112/api/action',{method:'POST',headers:{'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''},body:JSON.stringify({action:'forgive',chat_id:runtime.chatId,loan_id:loanId})});const d=await r.json().catch(()=>({ok:false,reason:'Ошибка ответа.'}));if(!r.ok||!d.ok)throw new Error(d.reason||'Не удалось выполнить действие.');toast(d.message||'Готово.');await load(runtime.chatId,true)}catch(e){toast(e.message||'Ошибка.','error')}finally{runtime.busy=false}
  }
  document.addEventListener('click',e=>{if(e.target.closest('#fin112Refresh'))load(runtime.chatId);const b=e.target.closest('[data-fin112-forgive]');if(b)forgive(b.dataset.fin112Forgive)});
  document.addEventListener('DOMContentLoaded',()=>{installStyles();installScreen();setTimeout(()=>installScreen(),500)});
})();
