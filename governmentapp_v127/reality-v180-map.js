(()=>{
  'use strict';
  if(window.__governmentRealityV180Map)return;
  window.__governmentRealityV180Map=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'X-Telegram-Init-Data':tg?.initData||''};
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';

  let state=null;
  let loading=false;
  let renderTimers=[];
  const camera={x:0,y:0,scale:1};
  const pointers=new Map();
  let gesture=null;

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=String(text||'Готово');
    node.className=`toast show ${type}`;
    clearTimeout(node.__r180);
    node.__r180=setTimeout(()=>node.className='toast',3800);
  }

  function ensureModal(){
    if(document.getElementById('r177Modal'))return;
    document.body.insertAdjacentHTML('beforeend',`
      <div class="r177-modal" id="r177Modal" aria-hidden="true">
        <section class="r177-sheet">
          <header><div><small id="r177ModalKicker">REALITY 180</small><h3 id="r177ModalTitle">Карта</h3></div><button type="button" data-r177-close>×</button></header>
          <div class="r177-modal-body" id="r177ModalBody"></div>
        </section>
      </div>`);
  }

  function openModal(title,kicker,content){
    ensureModal();
    const modal=document.getElementById('r177Modal');
    document.getElementById('r177ModalTitle').textContent=String(title||'Объект');
    document.getElementById('r177ModalKicker').textContent=String(kicker||'КАРТА ГОСУДАРСТВА');
    document.getElementById('r177ModalBody').innerHTML=content;
    modal.classList.add('open');
    modal.setAttribute('aria-hidden','false');
    document.body.classList.add('r177-modal-open');
  }

  function ensureLayout(){
    const stack=document.querySelector('.screen-stack');
    const nav=document.getElementById('bottomNav');
    if(stack&&!document.querySelector('.screen[data-screen="map180"]')){
      stack.insertAdjacentHTML('beforeend',`
        <section class="screen r180-screen" data-screen="map180">
          <div class="section-head r180-head">
            <div><small>REALITY 180 · ЖИВОЕ ГОСУДАРСТВО</small><h2>Карта государства</h2></div>
            <button type="button" class="secondary r180-refresh" data-r180-refresh>↻</button>
          </div>
          <div id="r180Map"></div>
        </section>`);
    }
    if(nav&&!nav.querySelector('[data-tab="map180"]')){
      const construction=nav.querySelector('[data-tab="construction179"]');
      const button=document.createElement('button');
      button.type='button';
      button.dataset.tab='map180';
      button.innerHTML='<span>🗺</span><small>Карта</small>';
      nav.insertBefore(button,construction||null);
    }
  }

  async function load(){
    if(!chatId||loading)return;
    loading=true;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_r180=${Date.now()}`,{cache:'no-store',headers});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось загрузить карту государства.');
      state=data;
      scheduleRender();
    }catch(error){
      toast(error.message||'Не удалось загрузить карту государства.','error');
    }finally{
      loading=false;
    }
  }

  function scheduleRender(){
    renderTimers.forEach(clearTimeout);
    renderTimers=[];
    [0,120,360].forEach(delay=>renderTimers.push(setTimeout(render,delay)));
  }

  function statusLabel(status){
    return ({
      awaiting_vote:'Ожидает голосования',
      awaiting_funding:'Собирает финансирование',
      building:'Строится',
      completed:'Построено',
      active:'Работает',
      underfunded:'Нет финансирования',
      frozen:'Заморожено',
    })[status]||String(status||'Неизвестно');
  }

  function metricCard(emoji,title,value,sub=''){
    return `<article><span>${emoji}</span><div><small>${esc(title)}</small><b>${esc(value)}</b>${sub?`<em>${esc(sub)}</em>`:''}</div></article>`;
  }

  function metrics(data){
    const m=data.metrics||{};
    return `<div class="r180-metrics">
      ${metricCard('💰','Общая казна',fmt(m.treasury),'свободные средства')}
      ${metricCard('⭐','Доверие',`${fmt(m.trust)} / 100`,m.trust_label)}
      ${metricCard('🏗','Развитие',`${fmt(m.development)}%`,`${fmt(m.built)} объектов`)}
      ${metricCard('😊','Благополучие',`${fmt(m.welfare)}%`,m.underfunded?`${fmt(m.underfunded)} без финансирования`:'объекты работают')}
    </div>`;
  }

  function programStrip(data){
    const rows=data.active_programs||[];
    if(!rows.length)return '<div class="r180-program-empty">Активных государственных программ на карте сейчас нет.</div>';
    return `<div class="r180-programs">${rows.map(item=>`<span class="district-${esc(item.district)}">${esc(item.emoji)} ${esc(item.title)}<small>до ${date(item.ends_at)}</small></span>`).join('')}</div>`;
  }

  function districtZones(data){
    const zones={
      government:[25,3,51,39],
      industrial:[1,48,38,48],
      social:[40,47,38,49],
      security:[79,36,20,60],
      culture:[1,2,23,44],
    };
    return (data.districts||[]).map(item=>{
      const pos=zones[item.key]||[1,1,20,20];
      return `<section class="r180-zone district-${esc(item.key)}" style="left:${pos[0]}%;top:${pos[1]}%;width:${pos[2]}%;height:${pos[3]}%">
        <header><span>${esc(item.emoji)}</span><div><b>${esc(item.title)}</b><small>${fmt(item.objects)} объектов</small></div></header>
      </section>`;
    }).join('');
  }

  function landmarkNode(item){
    return `<button type="button" class="r180-landmark district-${esc(item.district)}" style="left:${Number(item.x)}%;top:${Number(item.y)}%" data-r180-landmark="${esc(item.key)}" data-title="${esc(item.title)}">
      <span>${esc(item.emoji)}</span><small>${esc(item.title)}</small>
    </button>`;
  }

  function buildingDecor(key,status){
    const extra=key==='factory'?'<i class="r180-smoke"></i>':key==='power_plant'?'<i class="r180-energy"></i>':key==='police'?'<i class="r180-siren"></i>':key==='hospital'?'<i class="r180-cross">+</i>':'';
    const scaffold=['awaiting_vote','awaiting_funding','building'].includes(status)?'<i class="r180-crane">🏗</i>':'';
    return `${extra}${scaffold}`;
  }

  function objectNode(item){
    const status=String(item.status||'');
    const isProject=!item.building_id;
    const warning=status==='underfunded'||Number(item.maintenance_debt)>0;
    return `<button type="button" class="r180-object district-${esc(item.district)} status-${esc(status)} ${isProject?'project':'building'}" style="left:${Number(item.x)}%;top:${Number(item.y)}%" data-r180-object="${esc(item.plot_id)}" aria-label="${esc(item.title)}">
      <span class="r180-building-emoji">${esc(item.emoji)}${buildingDecor(item.building_key,status)}</span>
      <b>${esc(item.title)}</b>
      <small>${esc(statusLabel(status))}</small>
      ${isProject?`<i class="r180-node-progress"><u style="width:${Math.max(0,Math.min(100,Number(item.progress)||0))}%"></u></i>`:''}
      ${warning?'<em>⚠</em>':''}
    </button>`;
  }

  function emptyPlotNode(item){
    return `<span class="r180-empty-plot district-${esc(item.district)}" style="left:${Number(item.x)}%;top:${Number(item.y)}%" title="Свободный государственный участок"><i></i></span>`;
  }

  function legend(data){
    return `<div class="r180-legend">${(data.districts||[]).map(item=>`<span class="district-${esc(item.key)}">${esc(item.emoji)} ${esc(item.title)}</span>`).join('')}</div>`;
  }

  function mapWorld(data){
    return `<div class="r180-map-toolbar">
      <div><b>Перемещай карту одним пальцем</b><small>Масштаб — двумя пальцами</small></div>
      <button type="button" class="secondary" data-r180-center>⌖ ЦЕНТР</button>
    </div>
    <div class="r180-map-viewport" id="r180Viewport">
      <div class="r180-map-world" id="r180World">
        <div class="r180-water"></div>
        <div class="r180-roads"></div>
        ${districtZones(data)}
        ${(data.empty_plots||[]).map(emptyPlotNode).join('')}
        ${(data.landmarks||[]).map(landmarkNode).join('')}
        ${(data.objects||[]).map(objectNode).join('')}
      </div>
    </div>`;
  }

  function render(){
    ensureLayout();
    const mount=document.getElementById('r180Map');
    const data=state?.reality180?.map;
    if(!mount||!data)return;
    mount.innerHTML=`${metrics(data)}
      <article class="r180-program-panel"><div><small>АКТИВНЫЕ СОБЫТИЯ НА КАРТЕ</small><b>Государственные программы</b></div>${programStrip(data)}</article>
      ${mapWorld(data)}
      ${legend(data)}
      <article class="r180-summary">
        <div><small>РАБОТАЕТ</small><b>${fmt(data.metrics?.active)}</b></div>
        <div><small>СТРОИТСЯ</small><b>${fmt(data.metrics?.construction)}</b></div>
        <div><small>ДОЛГ СОДЕРЖАНИЯ</small><b>${fmt(data.metrics?.maintenance_debt)}</b></div>
        <div><small>ФИНАНСОВАЯ УСТОЙЧИВОСТЬ</small><b>${fmt(data.metrics?.financial_stability)}%</b></div>
      </article>`;
    applyCamera();
    bindMapGestures();
  }

  function applyCamera(){
    const world=document.getElementById('r180World');
    if(!world)return;
    world.style.transform=`translate3d(${camera.x}px,${camera.y}px,0) scale(${camera.scale})`;
  }

  function resetCamera(){
    camera.x=0;camera.y=0;camera.scale=1;applyCamera();
  }

  function pointerDistance(){
    const values=[...pointers.values()];
    if(values.length<2)return 0;
    return Math.hypot(values[0].x-values[1].x,values[0].y-values[1].y);
  }

  function pointerCenter(){
    const values=[...pointers.values()];
    if(values.length<2)return {x:0,y:0};
    return {x:(values[0].x+values[1].x)/2,y:(values[0].y+values[1].y)/2};
  }

  function bindMapGestures(){
    const viewport=document.getElementById('r180Viewport');
    if(!viewport||viewport.__r180Bound)return;
    viewport.__r180Bound=true;

    viewport.addEventListener('pointerdown',event=>{
      viewport.setPointerCapture?.(event.pointerId);
      pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
      if(pointers.size===1){
        gesture={mode:'pan',startX:event.clientX,startY:event.clientY,baseX:camera.x,baseY:camera.y};
      }else if(pointers.size===2){
        gesture={mode:'pinch',distance:pointerDistance(),scale:camera.scale,center:pointerCenter(),baseX:camera.x,baseY:camera.y};
      }
    });

    viewport.addEventListener('pointermove',event=>{
      if(!pointers.has(event.pointerId))return;
      pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
      if(pointers.size>=2&&gesture){
        if(gesture.mode!=='pinch')gesture={mode:'pinch',distance:pointerDistance(),scale:camera.scale,center:pointerCenter(),baseX:camera.x,baseY:camera.y};
        const distance=Math.max(1,pointerDistance());
        const next=Math.max(.72,Math.min(2.5,gesture.scale*distance/Math.max(1,gesture.distance)));
        const center=pointerCenter();
        camera.scale=next;
        camera.x=gesture.baseX+(center.x-gesture.center.x);
        camera.y=gesture.baseY+(center.y-gesture.center.y);
        applyCamera();
        event.preventDefault();
      }else if(pointers.size===1&&gesture?.mode==='pan'){
        camera.x=gesture.baseX+(event.clientX-gesture.startX);
        camera.y=gesture.baseY+(event.clientY-gesture.startY);
        applyCamera();
        event.preventDefault();
      }
    },{passive:false});

    const finish=event=>{
      pointers.delete(event.pointerId);
      if(pointers.size===1){
        const point=[...pointers.values()][0];
        gesture={mode:'pan',startX:point.x,startY:point.y,baseX:camera.x,baseY:camera.y};
      }else if(!pointers.size){
        gesture=null;
      }
    };
    viewport.addEventListener('pointerup',finish);
    viewport.addEventListener('pointercancel',finish);
  }

  function objectDetails(item){
    const contributors=(item.contributors||[]).map((row,index)=>`<div class="r180-contributor"><span>${index+1}. ${esc(row.name)}</span><b>${fmt(row.amount)}</b></div>`).join('')||'<div class="empty">Добровольных вкладчиков пока нет.</div>';
    const project=!item.building_id;
    const timing=project
      ? `<span>Собрано <b>${fmt(item.funded_amount)} / ${fmt(item.total_cost)}</b></span><span>Готовность <b>${fmt(item.progress)}%</b></span>${item.completes_at?`<span>Завершение <b>${date(item.completes_at)}</b></span>`:''}`
      : `<span>Построено <b>${date(item.completed_at)}</b></span><span>Содержание <b>${fmt(item.maintenance)}</b></span><span>Следующая оплата <b>${date(item.next_maintenance_at)}</b></span>${item.next_income_at?`<span>Следующий доход <b>${date(item.next_income_at)}</b></span>`:''}`;
    const actions=`<div class="button-grid r180-modal-actions">
      ${project?'<button type="button" class="action" data-map-open-construction>🏗 ОТКРЫТЬ СТРОИТЕЛЬСТВО</button>':''}
      ${Number(item.maintenance_debt)>0?`<button type="button" class="positive" data-r179-debt="${esc(item.building_id)}" data-building="${esc(item.building_key)}">🧾 ПОГАСИТЬ ДОЛГ</button>`:''}
    </div>`;
    return `<article class="r180-detail status-${esc(item.status)}">
      <div class="r180-detail-head"><span>${esc(item.emoji)}</span><div><small>${esc(statusLabel(item.status))}</small><b>${esc(item.title)}</b><em>${esc(item.source_title||'Государственное финансирование')}</em></div></div>
      <p>${esc(item.effect)}</p>
      <div class="r180-detail-grid">
        <span>Инициатор <b>${esc(item.initiator_name||'Государство')}</b></span>
        <span>Стоимость <b>${fmt(item.cost)}</b></span>
        ${timing}
        ${Number(item.maintenance_debt)>0?`<span class="danger">Долг <b>${fmt(item.maintenance_debt)}</b></span>`:''}
      </div>
      <div class="r180-detail-section"><small>ГЛАВНЫЕ ВКЛАДЧИКИ</small>${contributors}</div>
      ${actions}
    </article>`;
  }

  document.addEventListener('click',event=>{
    const refresh=event.target.closest?.('[data-r180-refresh]');
    if(refresh){load();return}
    const center=event.target.closest?.('[data-r180-center]');
    if(center){resetCamera();return}
    const node=event.target.closest?.('[data-r180-object]');
    if(node){
      const item=(state?.reality180?.map?.objects||[]).find(row=>String(row.plot_id)===String(node.dataset.r180Object));
      if(item)openModal(item.title,'🗺 ОБЪЕКТ НА КАРТЕ',objectDetails(item));
      return;
    }
    const landmark=event.target.closest?.('[data-r180-landmark]');
    if(landmark){
      openModal(landmark.dataset.title,'🏛 ГОСУДАРСТВЕННЫЙ ЦЕНТР',`<article class="r177-info"><p>Постоянное государственное учреждение. Оно отображается как ориентир и не является строительным объектом Reality 179.</p></article>`);
      return;
    }
    const openConstruction=event.target.closest?.('[data-map-open-construction]');
    if(openConstruction){
      document.querySelector('[data-tab="construction179"]')?.click();
      document.getElementById('r177Modal')?.classList.remove('open');
      document.body.classList.remove('r177-modal-open');
      return;
    }
    const nav=event.target.closest?.('[data-tab="map180"]');
    if(nav)setTimeout(()=>{render();load()},80);
  });

  window.addEventListener('pageshow',()=>load());
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)load()});
  ensureLayout();
  load();
})();