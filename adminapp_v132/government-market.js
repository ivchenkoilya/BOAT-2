(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const previousFetch=window.fetch.bind(window);
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const runtime={state:null,busy:false,lastKey:'',timer:null};
  window.AdminReality132=runtime;

  const $=id=>document.getElementById(id);
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const remaining=timestamp=>{
    const seconds=Math.max(0,Number(timestamp||0)-Math.floor(Date.now()/1000));
    if(!seconds)return 'нет';
    const hours=Math.floor(seconds/3600),minutes=Math.floor(seconds%3600/60);
    return hours?`${hours} ч. ${minutes} мин.`:`${Math.max(1,minutes)} мин.`;
  };

  function selectedIds(){
    const state=window.AdminFullV124?.state||{};
    return {
      chat_id:Number(state.selected_chat?.chat_id||localStorage.getItem('admin76Chat')||0),
      user_id:Number(state.target?.user_id||localStorage.getItem('admin76User')||0)
    };
  }

  function toast(text,type='success'){
    const node=$('toast');if(!node)return;
    node.textContent=String(text||'Готово.');node.className=`toast show ${type}`;
    clearTimeout(node.__v132Timer);node.__v132Timer=setTimeout(()=>node.className='toast',3600);
  }

  async function request(url,options={}){
    const response=await previousFetch(url,{cache:'no-store',...options,headers:{...headers,...(options.headers||{})}});
    const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
    if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
    return data;
  }

  function installStyles(){
    if($('adminV132Styles'))return;
    const style=document.createElement('style');style.id='adminV132Styles';style.textContent=`
      .v132-hero{padding:16px;border:1px solid #76539b;border-radius:20px;background:radial-gradient(circle at 100% 0,#b660ff35,transparent 42%),linear-gradient(150deg,#261534,#0d0913);margin-bottom:12px;box-shadow:0 16px 38px #0006}
      .v132-hero small,.v132-hero b,.v132-hero span{display:block}.v132-hero small{font-size:8px;letter-spacing:.14em;color:#c995f5;font-weight:900}.v132-hero b{font-size:20px;margin-top:4px}.v132-hero span{font-size:9px;color:#a899b3;margin-top:5px;line-height:1.5}
      .v132-metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}.v132-metric{padding:11px;border:1px solid #4e385e;border-radius:14px;background:#0d0912}.v132-metric small,.v132-metric b,.v132-metric em{display:block}.v132-metric small{font-size:8px;color:#9b8aa5}.v132-metric b{font-size:17px;color:#efd683;margin-top:4px}.v132-metric em{font-style:normal;font-size:8px;color:#8f8099;margin-top:3px}
      .v132-form-grid{display:grid;grid-template-columns:1fr 92px;gap:8px}.v132-field{display:grid;gap:5px;margin-top:9px}.v132-field label{font-size:8px;color:#a492ad;font-weight:900;letter-spacing:.08em}.v132-field input,.v132-field select{width:100%;min-height:46px;border:1px solid #4c385b;border-radius:13px;background:#0b0810;color:#f5ecf8;padding:0 11px;outline:none;font-size:14px}.v132-field input:focus,.v132-field select:focus{border-color:#b472e4;box-shadow:0 0 0 3px #a45bd526}
      .v132-check{display:flex;align-items:center;gap:8px;margin:10px 0;color:#b9a9c3;font-size:9px}.v132-check input{width:18px;height:18px}
      .v132-button{min-height:44px;border:1px solid #6f4a8d;border-radius:13px;background:linear-gradient(180deg,#4b286b,#28153a);color:#fff;font-weight:900;padding:9px 11px}.v132-button.good{border-color:#397d65;background:linear-gradient(180deg,#245d4c,#15382f)}.v132-button.danger{border-color:#814052;background:linear-gradient(180deg,#632b3b,#351720)}.v132-button.gold{border-color:#806b39;background:linear-gradient(180deg,#5b491f,#302610);color:#f8df8d}.v132-button:disabled{opacity:.45}
      .v132-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:9px}.v132-actions.three{grid-template-columns:repeat(3,1fr)}.v132-actions .full{grid-column:1/-1}
      .v132-office-list,.v132-stock-list{display:grid;gap:9px}.v132-office{padding:12px;border:1px solid #3c2d46;border-radius:15px;background:#0e0a13}.v132-office header{display:flex;align-items:flex-start;gap:9px}.v132-office header>span{font-size:24px}.v132-office header>div{min-width:0;flex:1}.v132-office b,.v132-office small{display:block}.v132-office b{font-size:11px}.v132-office small{font-size:8px;color:#95879f;margin-top:3px;line-height:1.4}.v132-office strong{font-size:9px;color:#e4ca78}
      .v132-empty{padding:15px;border:1px dashed #44344d;border-radius:14px;text-align:center;color:#92849b;font-size:9px}
      .v132-stock{position:relative;overflow:hidden;padding:13px;border:1px solid #40304b;border-radius:17px;background:radial-gradient(circle at 100% 0,#7c4faf22,transparent 42%),#0e0a13}.v132-stock.paused{border-color:#8a4b59;background:radial-gradient(circle at 100% 0,#c14f6730,transparent 42%),#110b10}.v132-stock-head{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center}.v132-stock-icon{width:43px;height:43px;display:grid;place-items:center;border:1px solid #624a72;border-radius:13px;background:#20152a;font-size:23px}.v132-stock-head b,.v132-stock-head small{display:block}.v132-stock-head b{font-size:13px}.v132-stock-head small{font-size:8px;color:#9889a2;margin-top:3px}.v132-price{text-align:right}.v132-price strong,.v132-price small{display:block}.v132-price strong{font-size:18px;color:#f0d47c}.v132-price small{font-size:8px;color:#998aa2;margin-top:2px}
      .v132-stock-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:10px}.v132-stock-stat{padding:8px 6px;border:1px solid #34283d;border-radius:10px;background:#09070d;text-align:center}.v132-stock-stat small,.v132-stock-stat b{display:block}.v132-stock-stat small{font-size:7px;color:#817589}.v132-stock-stat b{font-size:10px;margin-top:3px}
      .v132-event{display:grid;grid-template-columns:1fr 84px;gap:8px;margin-top:9px}.v132-note{margin-top:8px;color:#96889f;font-size:8px;line-height:1.5}.v132-status{display:inline-flex;padding:4px 7px;border-radius:999px;border:1px solid #4f3a5f;background:#1b1026;color:#d5b7ed;font-size:7px;font-weight:900}.v132-status.danger{border-color:#733e4c;background:#2e151d;color:#ffb4c1}
      @media(max-width:380px){.v132-form-grid,.v132-event{grid-template-columns:1fr}.v132-actions.three{grid-template-columns:1fr 1fr}.v132-stock-stats{grid-template-columns:1fr 1fr}}
    `;document.head.appendChild(style);
  }

  function governmentScreen(){
    return `<section class="screen" data-screen="government132">
      <div class="section-head"><div><small>REALITY 132</small><h2>Власть и казна</h2></div><button class="mini-button" data-v132-refresh>Обновить</button></div>
      <div id="v132GovHero"></div><div class="v132-metrics" id="v132GovMetrics"></div>
      <article class="panel requires-user">
        <div class="panel-title"><span>🎖</span><div><b>Выдать государственную должность</b><small>Админ может назначить президента, депутата или любого чиновника напрямую</small></div></div>
        <div class="v132-field"><label>ДОЛЖНОСТЬ</label><select id="v132OfficeSelect"></select></div>
        <div class="v132-form-grid"><div class="v132-field"><label>СРОК В ДНЯХ</label><input id="v132TermDays" type="number" min="1" max="30" value="7"></div><div class="v132-field"><label>МЕСТО</label><input id="v132SeatNo" type="number" min="1" max="7" value="1"></div></div>
        <label class="v132-check"><input id="v132Announce" type="checkbox" checked> Опубликовать назначение в беседе</label>
        <button class="v132-button good" data-v132-action="office_assign">🎖 НАЗНАЧИТЬ</button>
      </article>
      <article class="panel requires-user"><div class="panel-title"><span>🏛</span><div><b>Должности выбранного участника</b><small>Продление и немедленное снятие полномочий</small></div></div><div class="v132-office-list" id="v132TargetOffices"></div><button class="v132-button danger" data-v132-action="office_remove_all">Снять все государственные должности</button></article>
      <article class="panel"><div class="panel-title"><span>👥</span><div><b>Полный состав власти</b><small>Все занятые государственные места беседы</small></div></div><div class="v132-office-list" id="v132AllOffices"></div></article>
      <article class="panel"><div class="panel-title"><span>💰</span><div><b>Государственная казна</b><small>Прямое административное изменение с записью в журнал</small></div></div><div class="v132-actions three"><button class="v132-button" data-v132-treasury-delta="-10000">−10 000</button><button class="v132-button" data-v132-treasury-delta="10000">+10 000</button><button class="v132-button" data-v132-treasury-delta="100000">+100 000</button></div><div class="v132-field"><label>ТОЧНОЕ ЗНАЧЕНИЕ КАЗНЫ</label><input id="v132TreasuryExact" inputmode="numeric" type="number" min="0"></div><button class="v132-button gold" data-v132-action="treasury_set">Установить казну</button></article>
      <article class="panel requires-user"><div class="panel-title"><span>🔓</span><div><b>Политические ограничения</b><small>Запрет на выборы и создание конфликтов после наказаний</small></div></div><div id="v132BanState" class="v132-note"></div><button class="v132-button" data-v132-action="political_bans_clear">Снять политические запреты</button></article>
    </section>`;
  }

  function marketScreen(){
    return `<section class="screen" data-screen="market132">
      <div class="section-head"><div><small>REALITY 132</small><h2>Управление акциями</h2></div><button class="mini-button" data-v132-refresh>Обновить</button></div>
      <div class="v132-hero"><small>АДМИНИСТРАТИВНАЯ БИРЖА</small><b>Ручное управление рынком</b><span>Цена, движение курса, остановка торгов, заморозка курса, новости и сброс к базовой стоимости.</span></div>
      <div class="v132-stock-list" id="v132StockList"></div>
    </section>`;
  }

  function installUi(){
    installStyles();
    const stack=document.querySelector('.screen-stack');
    const history=stack?.querySelector('[data-screen="history"]');
    if(stack&&!document.querySelector('[data-screen="government132"]'))history?.insertAdjacentHTML('beforebegin',governmentScreen()+marketScreen());
    const nav=document.querySelector('.bottom-nav');
    const historyButton=nav?.querySelector('[data-tab="history"]');
    if(nav&&!nav.querySelector('[data-tab="government132"]')){
      const gov=document.createElement('button');gov.dataset.tab='government132';gov.innerHTML='<span>🏛</span><small>Власть</small>';
      const market=document.createElement('button');market.dataset.tab='market132';market.innerHTML='<span>📈</span><small>Акции</small>';
      nav.insertBefore(gov,historyButton||null);nav.insertBefore(market,historyButton||null);
    }
  }

  async function load(silent=true){
    installUi();
    const ids=selectedIds();if(!ids.chat_id)return;
    const key=`${ids.chat_id}:${ids.user_id}`;runtime.lastKey=key;
    try{
      const data=await request(`/admin-v132/api/state?chat_id=${ids.chat_id}&user_id=${ids.user_id||0}`);
      runtime.state=data;render();
      const version=$('versionText');if(version)version.textContent='Reality 132 · Власть и биржа';
    }catch(error){if(!silent)toast(error.message,'error')}
  }

  async function act(action,extra={}){
    if(runtime.busy)return;runtime.busy=true;
    const ids=selectedIds();
    try{
      const result=await request('/admin-v132/api/action',{method:'POST',body:JSON.stringify({action,chat_id:ids.chat_id,user_id:ids.user_id,...extra})});
      toast(result.message||'Готово.');tg?.HapticFeedback?.notificationOccurred?.('success');await load(true);
    }catch(error){toast(error.message||'Действие не выполнено.','error');tg?.HapticFeedback?.notificationOccurred?.('error')}
    finally{runtime.busy=false}
  }

  function render(){
    const state=runtime.state;if(!state)return;
    const gov=state.government||{},target=state.target;
    const targetName=target?.name||'Участник не выбран';
    $('v132GovHero').innerHTML=`<div class="v132-hero"><small>АДМИНИСТРАТИВНОЕ УПРАВЛЕНИЕ</small><b>${esc(targetName)}</b><span>${target?`ID ${target.user_id} · ⭐ ${fmt(target.career_points)} · 💰 ${fmt(target.points)}`:'Выбери участника в разделе «Участник».'}</span></div>`;
    $('v132GovMetrics').innerHTML=[
      ['💰','Казна',fmt(gov.treasury||0),'влияния'],
      ['🏛','Должностей',fmt((gov.offices||[]).length),'занято сейчас'],
      ['🎖','У участника',fmt((gov.target_offices||[]).length),target?'действующих':'не выбран'],
      ['🚫','Запреты',fmt((gov.election_ban_until?1:0)+(gov.conflict_ban_until?1:0)),'политических']
    ].map(x=>`<article class="v132-metric"><small>${x[0]} ${esc(x[1])}</small><b>${esc(x[2])}</b><em>${esc(x[3])}</em></article>`).join('');
    const select=$('v132OfficeSelect');if(select){const current=select.value;select.innerHTML=(gov.specs||[]).map(spec=>`<option value="${esc(spec.key)}">${esc(spec.emoji)} ${esc(spec.title)}</option>`).join('');if([...select.options].some(x=>x.value===current))select.value=current;updateSeatField()}
    const treasury=$('v132TreasuryExact');if(treasury&&!treasury.matches(':focus'))treasury.value=Number(gov.treasury||0);
    $('v132TargetOffices').innerHTML=(gov.target_offices||[]).length?(gov.target_offices||[]).map(officeMarkup).join(''):'<div class="v132-empty">У выбранного участника нет государственной должности.</div>';
    $('v132AllOffices').innerHTML=(gov.offices||[]).length?(gov.offices||[]).map(officeMarkup).join(''):'<div class="v132-empty">Правительство пока не сформировано.</div>';
    $('v132BanState').innerHTML=`Выборы: <b>${gov.election_ban_until?remaining(gov.election_ban_until):'доступны'}</b> · Конфликты: <b>${gov.conflict_ban_until?remaining(gov.conflict_ban_until):'доступны'}</b>`;
    $('v132StockList').innerHTML=(state.stocks||[]).map(stockMarkup).join('')||'<div class="v132-empty">Акции не найдены.</div>';
  }

  function officeMarkup(item){
    return `<article class="v132-office"><header><span>${esc(item.emoji)}</span><div><b>${esc(item.title)}${item.office_key==='deputy'?` · место ${item.seat_no}`:''}</b><small>${esc(item.name)}${item.username?' · @'+esc(item.username):''}<br>Осталось: ${esc(item.remaining)} · доверие ${Number(item.trust||50)}%</small></div><strong>⭐ ${fmt(item.career_points)}</strong></header><div class="v132-actions"><button class="v132-button" data-v132-extend="${esc(item.office_key)}" data-seat="${item.seat_no}">+7 дней</button><button class="v132-button danger" data-v132-remove="${esc(item.office_key)}" data-seat="${item.seat_no}">Снять</button></div></article>`;
  }

  function stockMarkup(stock){
    return `<article class="v132-stock ${stock.trading_paused?'paused':''}" data-symbol="${esc(stock.symbol)}"><div class="v132-stock-head"><div class="v132-stock-icon">${esc(stock.icon)}</div><div><b>${esc(stock.symbol)} · ${esc(stock.name)}</b><small>${esc(stock.risk)} риск ${stock.trading_paused?'· торги остановлены':''} ${stock.price_locked?'· курс заморожен':''}</small></div><div class="v132-price"><strong>${fmt(stock.price)}</strong><small>база ${fmt(stock.base_price)}</small></div></div><div class="v132-stock-stats"><div class="v132-stock-stat"><small>Макс.</small><b>${fmt(stock.high)}</b></div><div class="v132-stock-stat"><small>Мин.</small><b>${fmt(stock.low)}</b></div><div class="v132-stock-stat"><small>Держателей</small><b>${fmt(stock.holders)}</b></div><div class="v132-stock-stat"><small>Акций</small><b>${fmt(stock.quantity)}</b></div></div>${stock.last_event?`<div class="v132-note">Последнее событие: <b>${esc(stock.last_event)}</b></div>`:''}<div class="v132-field"><label>ТОЧНАЯ ЦЕНА</label><input data-v132-price-input="${esc(stock.symbol)}" type="number" min="5" value="${Number(stock.price)}"></div><div class="v132-actions three"><button class="v132-button" data-v132-move="${esc(stock.symbol)}" data-percent="-10">−10%</button><button class="v132-button" data-v132-set-price="${esc(stock.symbol)}">Установить</button><button class="v132-button" data-v132-move="${esc(stock.symbol)}" data-percent="10">+10%</button></div><div class="v132-event"><div class="v132-field"><label>РЫНОЧНОЕ СОБЫТИЕ</label><input data-v132-event-title="${esc(stock.symbol)}" maxlength="120" placeholder="Например: компания выпустила новый продукт"></div><div class="v132-field"><label>ЭФФЕКТ %</label><input data-v132-event-effect="${esc(stock.symbol)}" type="number" min="-50" max="50" value="10"></div></div><div class="v132-actions"><button class="v132-button gold" data-v132-event="${esc(stock.symbol)}">Создать событие</button><button class="v132-button ${stock.trading_paused?'good':'danger'}" data-v132-pause="${esc(stock.symbol)}" data-paused="${stock.trading_paused?'0':'1'}">${stock.trading_paused?'Возобновить торги':'Остановить торги'}</button><button class="v132-button ${stock.price_locked?'good':''}" data-v132-lock="${esc(stock.symbol)}" data-locked="${stock.price_locked?'0':'1'}">${stock.price_locked?'Разморозить курс':'Заморозить курс'}</button><button class="v132-button" data-v132-reset="${esc(stock.symbol)}">Сбросить к базовой цене</button></div></article>`;
  }

  function updateSeatField(){
    const office=$('v132OfficeSelect')?.value,field=$('v132SeatNo');if(!field)return;
    const deputy=office==='deputy';field.disabled=!deputy;if(!deputy)field.value='1';
  }

  document.addEventListener('change',event=>{if(event.target?.id==='v132OfficeSelect')updateSeatField()});
  document.addEventListener('click',event=>{
    const refresh=event.target.closest('[data-v132-refresh]');if(refresh){load(false);return}
    const action=event.target.closest('[data-v132-action]');if(action){
      const key=action.dataset.v132Action;
      if(key==='office_assign')act(key,{office_key:$('v132OfficeSelect')?.value||'',seat_no:Number($('v132SeatNo')?.value||1),term_days:Number($('v132TermDays')?.value||7),announce:Boolean($('v132Announce')?.checked)});
      else if(key==='treasury_set')act(key,{value:Number($('v132TreasuryExact')?.value||0)});
      else act(key);return;
    }
    const treasury=event.target.closest('[data-v132-treasury-delta]');if(treasury){act('treasury_delta',{value:Number(treasury.dataset.v132TreasuryDelta||0)});return}
    const extend=event.target.closest('[data-v132-extend]');if(extend){act('office_extend',{office_key:extend.dataset.v132Extend,seat_no:Number(extend.dataset.seat||1),days:7});return}
    const remove=event.target.closest('[data-v132-remove]');if(remove){act('office_remove',{office_key:remove.dataset.v132Remove,seat_no:Number(remove.dataset.seat||1)});return}
    const setPrice=event.target.closest('[data-v132-set-price]');if(setPrice){const symbol=setPrice.dataset.v132SetPrice;const input=document.querySelector(`[data-v132-price-input="${CSS.escape(symbol)}"]`);act('stock_set_price',{symbol,value:Number(input?.value||0)});return}
    const move=event.target.closest('[data-v132-move]');if(move){act('stock_move',{symbol:move.dataset.v132Move,percent:Number(move.dataset.percent||0)});return}
    const pause=event.target.closest('[data-v132-pause]');if(pause){act('stock_pause',{symbol:pause.dataset.v132Pause,paused:pause.dataset.paused==='1'});return}
    const lock=event.target.closest('[data-v132-lock]');if(lock){act('stock_lock',{symbol:lock.dataset.v132Lock,locked:lock.dataset.locked==='1'});return}
    const reset=event.target.closest('[data-v132-reset]');if(reset){act('stock_reset',{symbol:reset.dataset.v132Reset});return}
    const marketEvent=event.target.closest('[data-v132-event]');if(marketEvent){const symbol=marketEvent.dataset.v132Event;const title=document.querySelector(`[data-v132-event-title="${CSS.escape(symbol)}"]`)?.value||'';const effect=document.querySelector(`[data-v132-event-effect="${CSS.escape(symbol)}"]`)?.value||0;act('stock_event',{symbol,title,effect_percent:Number(effect)});return}
  });

  window.fetch=async(input,init={})=>{
    const response=await previousFetch(input,init);
    const url=typeof input==='string'?input:(input instanceof Request?input.url:String(input||''));
    if(url.includes('/admin-v76/api/state')||url.includes('/admin-v123/api/state'))setTimeout(()=>load(true),120);
    return response;
  };

  installUi();load(true);
  runtime.timer=setInterval(()=>{
    const ids=selectedIds(),key=`${ids.chat_id}:${ids.user_id}`;
    if(key!==runtime.lastKey)load(true);
  },1500);
})();