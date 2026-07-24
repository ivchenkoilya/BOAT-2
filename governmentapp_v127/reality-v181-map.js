(()=>{
  'use strict';
  if(window.__governmentRealityV181Map)return;
  window.__governmentRealityV181Map=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
  const requestId=()=>crypto?.randomUUID?.()||`r181-${Date.now()}-${Math.random().toString(36).slice(2)}`;

  let state=null;
  let busy=false;
  let fullscreen=false;
  let activeDistrict='all';
  let activeFilter='all';
  let selectedPlot='';
  let cameraInitialized=false;
  let transformFrame=0;
  let renderFrame=0;
  let camera={x:0,y:0,scale:1};
  const pointers=new Map();
  let gesture=null;

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=String(text||'Готово');
    node.className=`toast show ${type}`;
    clearTimeout(node.__r181Timer);
    node.__r181Timer=setTimeout(()=>node.className='toast',3800);
  }

  function ensureLayout(){
    document.querySelector('.screen[data-screen="map180"]')?.remove();
    document.querySelector('[data-tab="map180"]')?.remove();
    const stack=document.querySelector('.screen-stack');
    const nav=document.getElementById('bottomNav');
    if(stack&&!document.querySelector('.screen[data-screen="map181"]')){
      stack.insertAdjacentHTML('beforeend',`
        <section class="screen r181-screen" data-screen="map181">
          <div class="r181-screen-head">
            <div><small>REALITY 181 · КАРТА ГОСУДАРСТВА 2.0</small><h2>Живое государство</h2></div>
            <div class="r181-head-actions">
              <button type="button" class="secondary" data-r181-refresh aria-label="Обновить">↻</button>
              <button type="button" class="action" data-r181-fullscreen>⛶ <span>НА ВЕСЬ ЭКРАН</span></button>
            </div>
          </div>
          <div id="r181Map"></div>
        </section>`);
    }
    if(nav&&!nav.querySelector('[data-tab="map181"]')){
      const construction=nav.querySelector('[data-tab="construction179"]');
      const button=document.createElement('button');
      button.type='button';
      button.dataset.tab='map181';
      button.innerHTML='<span>🗺</span><small>Карта</small>';
      nav.insertBefore(button,construction||null);
    }
    ensureSheet();
  }

  function ensureSheet(){
    if(document.getElementById('r181Sheet'))return;
    document.body.insertAdjacentHTML('beforeend',`
      <div class="r181-sheet-backdrop" id="r181SheetBackdrop" data-r181-sheet-close></div>
      <aside class="r181-sheet" id="r181Sheet" aria-hidden="true">
        <div class="r181-sheet-grip"></div>
        <header><div><small id="r181SheetKicker">ОБЪЕКТ НА КАРТЕ</small><h3 id="r181SheetTitle">Государственный объект</h3></div><button type="button" data-r181-sheet-close>×</button></header>
        <div class="r181-sheet-body" id="r181SheetBody"></div>
      </aside>`);
  }

  async function load(){
    if(!chatId||busy)return;
    busy=true;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_r181=${Date.now()}`,{cache:'no-store',headers});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось загрузить карту государства.');
      state=data;
      scheduleRender();
    }catch(error){
      toast(error.message||'Не удалось загрузить карту государства.','error');
    }finally{
      busy=false;
    }
  }

  async function post179(action,payload={}){
    if(busy)return false;
    busy=true;
    try{
      const response=await fetch('/government-v179/api/action',{
        method:'POST',cache:'no-store',headers,
        body:JSON.stringify({action,chat_id:chatId,...payload}),
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      toast(data.message||'Готово.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      await load();
      return true;
    }catch(error){
      toast(error.message||'Действие не выполнено.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
      return false;
    }finally{
      busy=false;
    }
  }

  function scheduleRender(){
    cancelAnimationFrame(renderFrame);
    renderFrame=requestAnimationFrame(render);
  }

  function mapData(){return state?.reality181?.map||null}
  function worldSize(){const w=mapData()?.world||{};return {width:Number(w.width)||1200,height:Number(w.height)||760}}

  function metric(emoji,title,value,sub=''){
    return `<article><span>${emoji}</span><div><small>${esc(title)}</small><b>${esc(value)}</b>${sub?`<em>${esc(sub)}</em>`:''}</div></article>`;
  }

  function renderMetrics(data){
    const m=data.metrics||{};
    return `<div class="r181-metrics">
      ${metric('💰','Казна',fmt(m.treasury),'свободные средства')}
      ${metric('⭐','Доверие',`${fmt(m.trust)} / 100`,m.trust_label||'')}
      ${metric('🏗','Развитие',`${fmt(m.development)}%`,`${fmt(m.built)} построено`)}
      ${metric('⚠','Проблемы',fmt(m.problems||0),m.maintenance_debt?`долг ${fmt(m.maintenance_debt)}`:'долгов нет')}
    </div>`;
  }

  function districtButtons(data){
    const allCount=(data.objects||[]).length;
    const rows=[{key:'all',emoji:'🌐',title:'Всё государство',objects:allCount},...(data.districts||[])];
    return `<div class="r181-districts">${rows.map(item=>`<button type="button" class="${activeDistrict===item.key?'active':''}" data-r181-district="${esc(item.key)}"><span>${esc(item.emoji)}</span><b>${esc(item.title)}</b><em>${fmt(item.objects||0)}</em></button>`).join('')}</div>`;
  }

  function filterButtons(data){
    return `<div class="r181-filters">${(data.filters||[]).map(item=>`<button type="button" class="${activeFilter===item.key?'active':''}" data-r181-filter="${esc(item.key)}"><span>${esc(item.emoji)}</span>${esc(item.title)}</button>`).join('')}</div>`;
  }

  function activeProgramStrip(data){
    const rows=data.active_programs||[];
    if(!rows.length)return '<div class="r181-event-empty">На карте нет активных государственных программ.</div>';
    return `<div class="r181-events">${rows.map(item=>`<button type="button" data-r181-program-district="${esc(item.district)}"><span>${esc(item.emoji)}</span><b>${esc(item.title)}</b><small>до ${date(item.ends_at)}</small></button>`).join('')}</div>`;
  }

  function roadLayer(data){
    return `<svg class="r181-roads" viewBox="0 0 1200 760" aria-hidden="true">
      <defs><filter id="r181RoadShadow"><feDropShadow dx="0" dy="3" stdDeviation="3" flood-opacity=".42"/></filter></defs>
      ${(data.roads||[]).map(path=>`<path class="road-edge" d="${esc(path)}"></path><path class="road-main" d="${esc(path)}"></path>`).join('')}
    </svg>`;
  }

  function districtLayer(data){
    return (data.district_bounds||[]).map(item=>`<section class="r181-district-zone district-${esc(item.key)}" data-r181-zone="${esc(item.key)}" style="left:${Number(item.x)}px;top:${Number(item.y)}px;width:${Number(item.width)}px;height:${Number(item.height)}px">
      <header><span>${esc(item.emoji)}</span><div><b>${esc(item.title)}</b><small>${fmt(item.active)} работает · ${fmt(item.construction)} строится${item.problems?` · ⚠ ${fmt(item.problems)}`:''}</small></div></header>
      <i class="r181-zone-glow"></i>
    </section>`).join('');
  }

  function decorationNode(item){
    const icons={tree:'♣',lamp:'•',park:'✿',fountain:'◉',parking:'P',truck:'▰',pipe:'⌁',car:'◆',barrier:'═',flag:'⚑'};
    return `<i class="r181-decoration decor-${esc(item.type)} district-${esc(item.district)}" style="left:${Number(item.x)}px;top:${Number(item.y)}px;--decor-scale:${Number(item.scale)||1};--decor-rotate:${Number(item.rotation)||0}deg">${esc(icons[item.type]||'•')}</i>`;
  }

  function stageClass(item){
    if(item.is_problem)return 'problem';
    if(item.is_construction)return 'construction';
    if(item.is_active)return 'active';
    return String(item.status||'idle');
  }

  function objectNode(item){
    return `<button type="button" class="r181-object visual-${esc(item.visual_class)} stage-${esc(stageClass(item))}" style="left:${Number(item.x)}px;top:${Number(item.y)}px" data-r181-object="${esc(item.plot_id)}" data-district="${esc(item.district)}" data-status="${esc(item.status)}" data-construction="${item.is_construction?'1':'0'}" data-problem="${item.is_problem?'1':'0'}" data-active="${item.is_active?'1':'0'}">
      <span class="r181-building">
        <i class="roof"></i><i class="front"></i><i class="side"></i><strong>${esc(item.visual_symbol)}</strong>
        ${item.is_construction?'<u class="crane">⌁</u>':''}
        ${item.is_problem?'<u class="alert">!</u>':''}
        ${item.visual_class==='factory'&&item.is_active?'<u class="smoke"></u>':''}
        ${item.visual_class==='police'&&item.is_active?'<u class="siren"></u>':''}
        ${item.visual_class==='power'&&item.is_active?'<u class="energy"></u>':''}
      </span>
      <b class="r181-object-label">${esc(item.short_title)}</b>
      <small>${esc(statusLabel(item.status))}</small>
      ${item.is_construction?`<em class="r181-progress"><i style="width:${Math.max(0,Math.min(100,Number(item.progress)||0))}%"></i></em>`:''}
    </button>`;
  }

  function landmarkNode(item){
    return `<button type="button" class="r181-landmark visual-${esc(item.visual_class)}" style="left:${Number(item.x)}px;top:${Number(item.y)}px" data-r181-landmark="${esc(item.key)}" data-district="${esc(item.district)}">
      <span><i class="roof"></i><i class="front"></i><i class="side"></i><strong>${esc(item.visual_symbol)}</strong></span>
      <b>${esc(item.short_title)}</b>
    </button>`;
  }

  function minimap(data){
    const size=worldSize();
    return `<div class="r181-minimap" id="r181Minimap" aria-label="Мини-карта">
      ${(data.district_bounds||[]).map(item=>`<i class="district-${esc(item.key)}" style="left:${Number(item.x)/size.width*100}%;top:${Number(item.y)/size.height*100}%;width:${Number(item.width)/size.width*100}%;height:${Number(item.height)/size.height*100}%"></i>`).join('')}
      ${(data.objects||[]).map(item=>`<b style="left:${Number(item.x)/size.width*100}%;top:${Number(item.y)/size.height*100}%"></b>`).join('')}
      <u id="r181MiniViewport"></u>
    </div>`;
  }

  function world(data){
    const size=worldSize();
    return `<div class="r181-viewport" id="r181Viewport">
      <div class="r181-world" id="r181World" style="width:${size.width}px;height:${size.height}px">
        <div class="r181-terrain"></div>
        ${districtLayer(data)}
        ${roadLayer(data)}
        ${(data.decorations||[]).map(decorationNode).join('')}
        ${(data.landmarks||[]).map(landmarkNode).join('')}
        ${(data.objects||[]).map(objectNode).join('')}
      </div>
      ${minimap(data)}
    </div>`;
  }

  function districtObjectList(data){
    if(activeDistrict==='all')return '';
    const district=(data.districts||[]).find(item=>item.key===activeDistrict);
    const rows=(data.objects||[]).filter(item=>item.district===activeDistrict&&matchesFilter(item));
    return `<div class="r181-district-list">
      <header><div><small>${esc(district?.emoji||'🗺')} ВЫБРАННЫЙ РАЙОН</small><b>${esc(district?.title||activeDistrict)}</b></div><button type="button" data-r181-district="all">Показать всё</button></header>
      <div>${rows.length?rows.map(item=>`<button type="button" data-r181-list-object="${esc(item.plot_id)}"><span class="visual-${esc(item.visual_class)}">${esc(item.visual_symbol)}</span><div><b>${esc(item.short_title)}</b><small>${esc(statusLabel(item.status))}</small></div>${item.is_problem?'<em>⚠</em>':''}</button>`).join(''):'<p>Объектов с выбранным фильтром в этом районе нет.</p>'}</div>
    </div>`;
  }

  function mapToolbar(){
    return `<div class="r181-map-toolbar">
      <div class="r181-toolbar-left"><button type="button" data-r181-center>⌖ <span>ПОКАЗАТЬ ВСЁ</span></button><button type="button" data-r181-zoom-out>−</button><button type="button" data-r181-zoom-in>＋</button></div>
      <div class="r181-toolbar-right"><button type="button" data-r181-refresh>↻</button><button type="button" data-r181-fullscreen>${fullscreen?'✕':'⛶'} <span>${fullscreen?'ЗАКРЫТЬ':'НА ВЕСЬ ЭКРАН'}</span></button></div>
    </div>`;
  }

  function statusLabel(status){
    return ({awaiting_vote:'Ожидает голосования',awaiting_funding:'Собирает финансирование',building:'Строится',completed:'Построено',active:'Работает',underfunded:'Нет финансирования',frozen:'Заморожено',cancelled:'Отменено'})[status]||String(status||'Неизвестно');
  }

  function render(){
    ensureLayout();
    const data=mapData();
    const mount=document.getElementById('r181Map');
    if(!data||!mount)return;
    mount.innerHTML=`
      ${renderMetrics(data)}
      <section class="r181-control-panel">
        <div><small>РАЙОНЫ ГОСУДАРСТВА</small>${districtButtons(data)}</div>
        <div><small>РЕЖИМ КАРТЫ</small>${filterButtons(data)}</div>
      </section>
      <section class="r181-event-panel"><header><small>АКТИВНЫЕ ПРОГРАММЫ</small><b>События на карте</b></header>${activeProgramStrip(data)}</section>
      ${mapToolbar()}
      ${districtObjectList(data)}
      ${world(data)}
      <footer class="r181-map-summary"><span>✅ Работает <b>${fmt(data.metrics?.active)}</b></span><span>🏗 Строится <b>${fmt(data.metrics?.construction)}</b></span><span>⚠ Проблемы <b>${fmt(data.metrics?.problems)}</b></span><span>💸 Долг <b>${fmt(data.metrics?.maintenance_debt)}</b></span></footer>`;
    bindGestures();
    if(!cameraInitialized){fitAll(false);cameraInitialized=true}else scheduleTransform();
    applyVisibility();
  }

  function viewport(){return document.getElementById('r181Viewport')}
  function worldNode(){return document.getElementById('r181World')}

  function scheduleTransform(){
    cancelAnimationFrame(transformFrame);
    transformFrame=requestAnimationFrame(applyTransform);
  }

  function applyTransform(){
    const node=worldNode();
    const view=viewport();
    if(!node||!view)return;
    node.style.transform=`translate3d(${camera.x}px,${camera.y}px,0) scale(${camera.scale})`;
    node.classList.toggle('zoom-far',camera.scale<.82);
    node.classList.toggle('zoom-near',camera.scale>1.28);
    updateMiniViewport();
  }

  function fitBounds(bounds,animate=true){
    const view=viewport();
    if(!view||!bounds)return;
    const pad=fullscreen?34:22;
    const scale=Math.max(.58,Math.min(2.25,Math.min((view.clientWidth-pad*2)/Number(bounds.width),(view.clientHeight-pad*2)/Number(bounds.height))));
    camera.scale=scale;
    camera.x=Math.round(view.clientWidth/2-(Number(bounds.x)+Number(bounds.width)/2)*scale);
    camera.y=Math.round(view.clientHeight/2-(Number(bounds.y)+Number(bounds.height)/2)*scale);
    if(animate)worldNode()?.classList.add('camera-animate');
    scheduleTransform();
    if(animate)setTimeout(()=>worldNode()?.classList.remove('camera-animate'),360);
  }

  function fitAll(animate=true){
    const size=worldSize();
    fitBounds({x:0,y:0,width:size.width,height:size.height},animate);
  }

  function focusDistrict(key){
    const data=mapData();
    if(!data)return;
    if(key==='all'){
      activeDistrict='all';
      fitAll();
    }else if(activeDistrict===key){
      activeDistrict='all';
      fitAll();
    }else{
      activeDistrict=key;
      const bounds=(data.district_bounds||[]).find(item=>item.key===key);
      fitBounds(bounds);
    }
    updateControlsAndVisibility();
  }

  function focusObject(item){
    const view=viewport();
    if(!view||!item)return;
    camera.scale=Math.max(1.18,camera.scale);
    camera.x=Math.round(view.clientWidth/2-Number(item.x)*camera.scale);
    camera.y=Math.round(view.clientHeight/2-Number(item.y)*camera.scale);
    scheduleTransform();
  }

  function zoomBy(multiplier){
    const view=viewport();
    if(!view)return;
    const centerX=(view.clientWidth/2-camera.x)/camera.scale;
    const centerY=(view.clientHeight/2-camera.y)/camera.scale;
    camera.scale=Math.max(.58,Math.min(2.5,camera.scale*multiplier));
    camera.x=Math.round(view.clientWidth/2-centerX*camera.scale);
    camera.y=Math.round(view.clientHeight/2-centerY*camera.scale);
    scheduleTransform();
  }

  function matchesFilter(item){
    if(activeFilter==='construction')return Boolean(item.is_construction);
    if(activeFilter==='active')return Boolean(item.is_active);
    if(activeFilter==='problems')return Boolean(item.is_problem);
    if(activeFilter==='institutions')return false;
    return true;
  }

  function applyVisibility(){
    document.querySelectorAll('.r181-object').forEach(node=>{
      const item=(mapData()?.objects||[]).find(row=>String(row.plot_id)===String(node.dataset.r181Object));
      const filterVisible=item&&matchesFilter(item);
      const districtVisible=activeDistrict==='all'||node.dataset.district===activeDistrict;
      node.classList.toggle('r181-hidden',!filterVisible);
      node.classList.toggle('r181-dim',filterVisible&&!districtVisible);
    });
    document.querySelectorAll('.r181-landmark').forEach(node=>{
      const filterVisible=activeFilter==='all'||activeFilter==='institutions';
      const districtVisible=activeDistrict==='all'||node.dataset.district===activeDistrict;
      node.classList.toggle('r181-hidden',!filterVisible);
      node.classList.toggle('r181-dim',filterVisible&&!districtVisible);
    });
    document.querySelectorAll('.r181-district-zone').forEach(node=>{
      const chosen=activeDistrict==='all'||node.dataset.r181Zone===activeDistrict;
      node.classList.toggle('r181-dim',!chosen);
      node.classList.toggle('selected',activeDistrict!=='all'&&node.dataset.r181Zone===activeDistrict);
    });
  }

  function updateControlsAndVisibility(){
    document.querySelectorAll('[data-r181-district]').forEach(button=>button.classList.toggle('active',button.dataset.r181District===activeDistrict));
    document.querySelectorAll('[data-r181-filter]').forEach(button=>button.classList.toggle('active',button.dataset.r181Filter===activeFilter));
    applyVisibility();
    const old=document.querySelector('.r181-district-list');
    if(old){
      const wrapper=document.createElement('div');
      wrapper.innerHTML=districtObjectList(mapData());
      old.replaceWith(wrapper.firstElementChild||document.createComment(''));
    }else if(activeDistrict!=='all'){
      document.querySelector('.r181-map-toolbar')?.insertAdjacentHTML('afterend',districtObjectList(mapData()));
    }
  }

  function toggleFullscreen(force){
    fullscreen=typeof force==='boolean'?force:!fullscreen;
    const screen=document.querySelector('.r181-screen');
    screen?.classList.toggle('r181-fullscreen',fullscreen);
    document.body.classList.toggle('r181-map-fullscreen',fullscreen);
    if(fullscreen){tg?.expand?.();tg?.requestFullscreen?.()}else tg?.exitFullscreen?.();
    closeSheet();
    setTimeout(()=>{
      if(activeDistrict==='all')fitAll(false);
      else{
        const bounds=(mapData()?.district_bounds||[]).find(item=>item.key===activeDistrict);
        fitBounds(bounds,false);
      }
      scheduleRender();
    },80);
  }

  function updateMiniViewport(){
    const mini=document.getElementById('r181Minimap');
    const box=document.getElementById('r181MiniViewport');
    const view=viewport();
    if(!mini||!box||!view)return;
    const size=worldSize();
    const left=Math.max(0,Math.min(size.width,-camera.x/camera.scale));
    const top=Math.max(0,Math.min(size.height,-camera.y/camera.scale));
    const width=Math.min(size.width,view.clientWidth/camera.scale);
    const height=Math.min(size.height,view.clientHeight/camera.scale);
    box.style.left=`${left/size.width*100}%`;
    box.style.top=`${top/size.height*100}%`;
    box.style.width=`${width/size.width*100}%`;
    box.style.height=`${height/size.height*100}%`;
  }

  function bindGestures(){
    const view=viewport();
    if(!view||view.__r181Bound)return;
    view.__r181Bound=true;
    view.addEventListener('pointerdown',event=>{
      if(event.target.closest('button,.r181-minimap'))return;
      view.setPointerCapture?.(event.pointerId);
      pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
      if(pointers.size===1)gesture={mode:'pan',x:event.clientX,y:event.clientY,baseX:camera.x,baseY:camera.y};
      if(pointers.size===2)gesture={mode:'pinch',distance:pointerDistance(),scale:camera.scale,center:pointerCenter(),baseX:camera.x,baseY:camera.y};
    });
    view.addEventListener('pointermove',event=>{
      if(!pointers.has(event.pointerId))return;
      pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
      if(pointers.size>=2){
        if(gesture?.mode!=='pinch')gesture={mode:'pinch',distance:pointerDistance(),scale:camera.scale,center:pointerCenter(),baseX:camera.x,baseY:camera.y};
        const next=Math.max(.58,Math.min(2.5,gesture.scale*pointerDistance()/Math.max(1,gesture.distance)));
        const center=pointerCenter();
        camera.scale=next;
        camera.x=gesture.baseX+(center.x-gesture.center.x);
        camera.y=gesture.baseY+(center.y-gesture.center.y);
        scheduleTransform();
        event.preventDefault();
      }else if(pointers.size===1&&gesture?.mode==='pan'){
        camera.x=gesture.baseX+(event.clientX-gesture.x);
        camera.y=gesture.baseY+(event.clientY-gesture.y);
        scheduleTransform();
        event.preventDefault();
      }
    },{passive:false});
    const finish=event=>{
      pointers.delete(event.pointerId);
      if(pointers.size===1){const point=[...pointers.values()][0];gesture={mode:'pan',x:point.x,y:point.y,baseX:camera.x,baseY:camera.y}}
      else if(!pointers.size)gesture=null;
    };
    view.addEventListener('pointerup',finish);
    view.addEventListener('pointercancel',finish);
  }

  function pointerDistance(){
    const rows=[...pointers.values()];
    return rows.length<2?1:Math.hypot(rows[0].x-rows[1].x,rows[0].y-rows[1].y);
  }
  function pointerCenter(){
    const rows=[...pointers.values()];
    return rows.length<2?{x:0,y:0}:{x:(rows[0].x+rows[1].x)/2,y:(rows[0].y+rows[1].y)/2};
  }

  function objectHistory(item){
    const rows=(state?.reality179?.construction?.history||[]).filter(row=>String(row.project_id||'')===String(item.project_id||'')||String(row.building_id||'')===String(item.building_id||''));
    if(!rows.length)return '<div class="empty">История объекта пока пуста.</div>';
    return `<div class="r181-history">${rows.slice(0,16).map(row=>`<article><span>${date(row.created_at)}</span><b>${esc(row.detail||row.operation_type||'Операция')}</b>${Number(row.amount)?`<em>${fmt(row.amount)}</em>`:''}</article>`).join('')}</div>`;
  }

  function sheetContent(item){
    const project=!item.building_id;
    const canManage=Boolean(state?.reality179?.construction?.can_propose);
    const contributors=(item.contributors||[]).map((row,index)=>`<div class="r181-contributor"><span>${index+1}. ${esc(row.name)}</span><b>${fmt(row.amount)}</b></div>`).join('')||'<div class="empty">Добровольных вкладчиков пока нет.</div>';
    return `<article class="r181-object-detail">
      <div class="r181-detail-hero visual-${esc(item.visual_class)} stage-${esc(stageClass(item))}">
        <span><i class="roof"></i><i class="front"></i><i class="side"></i><strong>${esc(item.visual_symbol)}</strong></span>
        <div><small>${esc(statusLabel(item.status))} · ${esc((mapData()?.districts||[]).find(row=>row.key===item.district)?.title||item.district)}</small><b>${esc(item.title)}</b><em>${esc(item.source_title||'Государственное финансирование')}</em></div>
      </div>
      <p>${esc(item.effect)}</p>
      <div class="r181-detail-grid">
        <span>Инициатор<b>${esc(item.initiator_name||'Государство')}</b></span>
        <span>Стоимость<b>${fmt(item.cost)}</b></span>
        ${project?`<span>Финансирование<b>${fmt(item.funded_amount)} / ${fmt(item.total_cost)}</b></span><span>Готовность<b>${fmt(item.progress)}%</b></span>${item.completes_at?`<span>Завершение<b>${date(item.completes_at)}</b></span>`:''}`:`<span>Построено<b>${date(item.completed_at)}</b></span><span>Содержание<b>${fmt(item.maintenance)}</b></span><span>Следующая оплата<b>${date(item.next_maintenance_at)}</b></span>${item.next_income_at?`<span>Следующий доход<b>${date(item.next_income_at)}</b></span>`:''}`}
        ${Number(item.maintenance_debt)>0?`<span class="problem">Долг<b>${fmt(item.maintenance_debt)}</b></span>`:''}
      </div>
      <section><small>ГЛАВНЫЕ ВКЛАДЧИКИ</small>${contributors}</section>
      <div class="r181-sheet-actions">
        ${project&&item.status==='awaiting_funding'?`<button type="button" class="positive" data-r181-contribute="${esc(item.plot_id)}">🤝 ВЛОЖИТЬСЯ</button>`:''}
        ${project&&item.status==='awaiting_funding'&&canManage?`<button type="button" class="action" data-r181-fund="${esc(item.plot_id)}">💰 НАПРАВИТЬ СРЕДСТВА</button>`:''}
        ${project?'<button type="button" class="secondary" data-r181-open-construction>🏗 ОТКРЫТЬ ПРОЕКТ</button>':''}
        ${Number(item.maintenance_debt)>0&&canManage?`<button type="button" class="danger" data-r181-pay-debt="${esc(item.plot_id)}">🧾 ПОГАСИТЬ ДОЛГ</button>`:''}
        <button type="button" class="secondary" data-r181-history="${esc(item.plot_id)}">📜 ИСТОРИЯ</button>
        <button type="button" class="secondary" data-r181-show="${esc(item.plot_id)}">⌖ ПОКАЗАТЬ НА КАРТЕ</button>
      </div>
      <div id="r181ObjectHistory"></div>
    </article>`;
  }

  function openObject(item){
    if(!item)return;
    selectedPlot=String(item.plot_id);
    ensureSheet();
    document.getElementById('r181SheetTitle').textContent=item.title;
    document.getElementById('r181SheetKicker').textContent=`${statusLabel(item.status)} · карта государства`;
    document.getElementById('r181SheetBody').innerHTML=sheetContent(item);
    document.getElementById('r181Sheet').classList.add('open');
    document.getElementById('r181Sheet').setAttribute('aria-hidden','false');
    document.getElementById('r181SheetBackdrop').classList.add('open');
    document.body.classList.add('r181-sheet-open');
    tg?.HapticFeedback?.impactOccurred?.('light');
  }

  function closeSheet(){
    document.getElementById('r181Sheet')?.classList.remove('open');
    document.getElementById('r181Sheet')?.setAttribute('aria-hidden','true');
    document.getElementById('r181SheetBackdrop')?.classList.remove('open');
    document.body.classList.remove('r181-sheet-open');
  }

  function itemByPlot(plot){return (mapData()?.objects||[]).find(item=>String(item.plot_id)===String(plot))}

  async function contribute(item){
    const max=Math.max(0,Number(item.remaining)||0);
    const value=Number(prompt(`Сколько влияния вложить в «${item.short_title}»?\nОсталось собрать: ${fmt(max)}`,String(Math.min(10000,max))));
    if(!Number.isFinite(value)||value<100)return;
    await post179('construction_contribute',{project_id:item.project_id,amount:Math.floor(value),request_id:requestId()});
    closeSheet();
  }

  async function fund(item){
    const max=Math.max(0,Number(item.remaining)||0);
    const value=Number(prompt(`Сколько направить из «${item.source_title}»?\nОсталось: ${fmt(max)}`,String(max)));
    if(!Number.isFinite(value)||value<=0)return;
    await post179('construction_fund',{project_id:item.project_id,source_key:item.source_key,amount:Math.floor(value),request_id:requestId()});
    closeSheet();
  }

  async function payDebt(item){
    if(!confirm(`Погасить долг объекта ${fmt(item.maintenance_debt)} влияния из «${item.source_title}»?`))return;
    await post179('construction_debt_pay',{building_id:item.building_id,source_key:item.source_key,request_id:requestId()});
    closeSheet();
  }

  function openConstruction(){
    closeSheet();
    if(fullscreen)toggleFullscreen(false);
    document.querySelector('[data-tab="construction179"]')?.click();
  }

  document.addEventListener('click',event=>{
    const tab=event.target.closest?.('[data-tab="map181"]');
    if(tab)setTimeout(()=>{scheduleRender();load()},70);

    const district=event.target.closest?.('[data-r181-district]');
    if(district){focusDistrict(String(district.dataset.r181District));return}
    const program=event.target.closest?.('[data-r181-program-district]');
    if(program){focusDistrict(String(program.dataset.r181ProgramDistrict));return}
    const filter=event.target.closest?.('[data-r181-filter]');
    if(filter){activeFilter=String(filter.dataset.r181Filter);updateControlsAndVisibility();return}
    if(event.target.closest?.('[data-r181-center]')){activeDistrict='all';fitAll();updateControlsAndVisibility();return}
    if(event.target.closest?.('[data-r181-zoom-in]')){zoomBy(1.2);return}
    if(event.target.closest?.('[data-r181-zoom-out]')){zoomBy(1/1.2);return}
    if(event.target.closest?.('[data-r181-refresh]')){load();return}
    if(event.target.closest?.('[data-r181-fullscreen]')){toggleFullscreen();return}
    if(event.target.closest?.('[data-r181-sheet-close]')){closeSheet();return}

    const object=event.target.closest?.('[data-r181-object]');
    if(object){openObject(itemByPlot(object.dataset.r181Object));return}
    const listObject=event.target.closest?.('[data-r181-list-object]');
    if(listObject){const item=itemByPlot(listObject.dataset.r181ListObject);focusObject(item);openObject(item);return}
    const landmark=event.target.closest?.('[data-r181-landmark]');
    if(landmark){
      const item=(mapData()?.landmarks||[]).find(row=>String(row.key)===String(landmark.dataset.r181Landmark));
      if(item){
        document.getElementById('r181SheetTitle').textContent=item.title;
        document.getElementById('r181SheetKicker').textContent='ПОСТОЯННОЕ ГОСУДАРСТВЕННОЕ УЧРЕЖДЕНИЕ';
        document.getElementById('r181SheetBody').innerHTML=`<article class="r181-institution-detail visual-${esc(item.visual_class)}"><span>${esc(item.visual_symbol)}</span><p>${esc(item.title)} является постоянным ориентиром карты. Учреждение не создаёт отдельного баланса и работает через существующие полномочия Правительства.</p><button type="button" class="secondary" data-r181-sheet-close>ЗАКРЫТЬ</button></article>`;
        document.getElementById('r181Sheet').classList.add('open');document.getElementById('r181SheetBackdrop').classList.add('open');document.body.classList.add('r181-sheet-open');
      }
      return;
    }
    const contributeButton=event.target.closest?.('[data-r181-contribute]');
    if(contributeButton){contribute(itemByPlot(contributeButton.dataset.r181Contribute));return}
    const fundButton=event.target.closest?.('[data-r181-fund]');
    if(fundButton){fund(itemByPlot(fundButton.dataset.r181Fund));return}
    const debtButton=event.target.closest?.('[data-r181-pay-debt]');
    if(debtButton){payDebt(itemByPlot(debtButton.dataset.r181PayDebt));return}
    if(event.target.closest?.('[data-r181-open-construction]')){openConstruction();return}
    const historyButton=event.target.closest?.('[data-r181-history]');
    if(historyButton){const item=itemByPlot(historyButton.dataset.r181History);const mount=document.getElementById('r181ObjectHistory');if(mount)mount.innerHTML=objectHistory(item);return}
    const showButton=event.target.closest?.('[data-r181-show]');
    if(showButton){const item=itemByPlot(showButton.dataset.r181Show);closeSheet();focusObject(item);return}

    const mini=event.target.closest?.('#r181Minimap');
    if(mini&&event.target.id!=='r181MiniViewport'){
      const rect=mini.getBoundingClientRect();
      const size=worldSize();
      const worldX=(event.clientX-rect.left)/rect.width*size.width;
      const worldY=(event.clientY-rect.top)/rect.height*size.height;
      const view=viewport();
      camera.x=view.clientWidth/2-worldX*camera.scale;
      camera.y=view.clientHeight/2-worldY*camera.scale;
      scheduleTransform();
    }
  });

  window.addEventListener('resize',()=>{if(cameraInitialized){if(activeDistrict==='all')fitAll(false);else focusDistrict(activeDistrict)}});
  window.addEventListener('pageshow',()=>load());
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)load()});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'){if(document.getElementById('r181Sheet')?.classList.contains('open'))closeSheet();else if(fullscreen)toggleFullscreen(false)}});

  ensureLayout();
  load();
})();