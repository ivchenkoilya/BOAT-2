(()=>{
  'use strict';
  if(window.__governmentRealityV183Map)return;
  window.__governmentRealityV183Map=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const SPRITE='/government-v183/reality-v183-buildings-20260724.svg?build=183-20260724-a';
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
  const duration=value=>{let s=Math.max(0,Number(value)||0);const d=Math.floor(s/86400);s%=86400;const h=Math.floor(s/3600);const m=Math.floor(s%3600/60);return d?`${d} д. ${h} ч.`:h?`${h} ч. ${m} мин.`:`${Math.max(1,m)} мин.`};
  const requestId=()=>globalThis.crypto?.randomUUID?.()||`r183-${Date.now()}-${Math.random().toString(36).slice(2)}`;

  let state=null,loading=false,actionBusy=false,fullscreen=false,districtMenu=false,miniVisible=false;
  let activeDistrict='all',activeFilter='all',selectedPlot='',layoutMode='mobile',cameraReady=false;
  let camera={x:0,y:0,scale:1},gesture=null,renderFrame=0,transformFrame=0,resizeTimer=0;
  const pointers=new Map(),previousStatuses=new Map();

  const mapData=()=>state?.reality183?.map||null;
  const viewport=()=>document.getElementById('r183Viewport');
  const worldNode=()=>document.getElementById('r183World');
  const currentLayout=()=>mapData()?.layouts?.[layoutMode]||null;
  const worldSize=()=>currentLayout()?.world||{width:720,height:1120};
  const itemByPlot=id=>(mapData()?.objects||[]).find(item=>String(item.plot_id)===String(id));
  const statusLabel=status=>({awaiting_vote:'Ожидает голосования',awaiting_funding:'Собирает средства',building:'Строится',completed:'Построено',active:'Работает',underfunded:'Нет финансирования',frozen:'Заморожено',cancelled:'Отменено'})[status]||String(status||'Неизвестно');

  function toast(text,type='success'){
    const node=document.getElementById('toast');if(!node)return;
    node.textContent=String(text||'Готово');node.className=`toast show ${type}`;
    clearTimeout(node.__r183);node.__r183=setTimeout(()=>node.className='toast',3800);
  }

  function ensureSheet(){
    if(document.getElementById('r183Sheet'))return;
    document.body.insertAdjacentHTML('beforeend',`<div class="r183-sheet-backdrop" id="r183SheetBackdrop" data-r183-sheet-close></div><aside class="r183-sheet" id="r183Sheet" aria-hidden="true"><div class="r183-sheet-grip"></div><header><div><small id="r183SheetKicker">ЖИВОЙ ГОРОД</small><h3 id="r183SheetTitle">Объект</h3></div><button type="button" data-r183-sheet-close>×</button></header><div class="r183-sheet-body" id="r183SheetBody"></div></aside>`);
  }

  function openSheet(title,kicker,html){
    ensureSheet();
    document.getElementById('r183SheetTitle').textContent=String(title||'Карта');
    document.getElementById('r183SheetKicker').textContent=String(kicker||'ЖИВОЙ ГОРОД');
    document.getElementById('r183SheetBody').innerHTML=html;
    document.getElementById('r183Sheet').classList.add('open');
    document.getElementById('r183SheetBackdrop').classList.add('open');
    document.body.classList.add('r183-sheet-open');
    document.getElementById('r183Minimap')?.classList.add('sheet-hidden');
  }

  function closeSheet(){
    document.getElementById('r183Sheet')?.classList.remove('open');
    document.getElementById('r183SheetBackdrop')?.classList.remove('open');
    document.body.classList.remove('r183-sheet-open');
    document.getElementById('r183Minimap')?.classList.remove('sheet-hidden');
  }

  function ensureLayout(){
    ['map180','map181','map182'].forEach(key=>{
      document.querySelector(`.screen[data-screen="${key}"]`)?.remove();
      document.querySelector(`[data-tab="${key}"]`)?.remove();
    });
    const stack=document.querySelector('.screen-stack'),nav=document.getElementById('bottomNav');
    if(stack&&!document.querySelector('.screen[data-screen="map183"]')){
      stack.insertAdjacentHTML('beforeend',`<section class="screen r183-screen" data-screen="map183"><header class="r183-screen-head"><div><small>REALITY 183 · ЖИВОЙ ГОРОД</small><h2>Карта государства</h2></div><div><button type="button" class="secondary" data-r183-refresh>↻</button><button type="button" class="action" data-r183-fullscreen>⛶ НА ВЕСЬ ЭКРАН</button></div></header><div id="r183Map"></div></section>`);
    }
    if(nav&&!nav.querySelector('[data-tab="map183"]')){
      const button=document.createElement('button');button.type='button';button.dataset.tab='map183';button.innerHTML='<span>🗺</span><small>Карта</small>';
      nav.insertBefore(button,nav.querySelector('[data-tab="construction179"]')||null);
    }
    ensureSheet();
  }

  function detectCompletions(next){
    const rows=next?.reality183?.map?.objects||[];
    if(previousStatuses.size){
      rows.forEach(item=>{
        const key=String(item.project_id||item.plot_id||'');
        const before=previousStatuses.get(key),after=String(item.status||'');
        if(before&&['building','awaiting_funding'].includes(before)&&['active','completed'].includes(after))celebrate(item);
      });
    }
    previousStatuses.clear();
    rows.forEach(item=>previousStatuses.set(String(item.project_id||item.plot_id||''),String(item.status||'')));
  }

  function celebrate(item){
    toast(`${item.emoji||'🏛'} ${item.title||'Государственный объект'} построен!`);
    const layer=document.createElement('div');layer.className='r183-confetti';
    layer.innerHTML=Array.from({length:18},(_,i)=>`<i style="--x:${(i*37)%100}%;--d:${(i%7)*.07}s;--r:${(i*49)%360}deg"></i>`).join('');
    document.body.appendChild(layer);setTimeout(()=>layer.remove(),2200);
  }

  async function load(force=false){
    if(!chatId||loading)return;loading=true;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_r183=${Date.now()}`,{cache:'no-store',headers:{'X-Telegram-Init-Data':tg?.initData||''}});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось загрузить живой город.');
      detectCompletions(data);state=data;scheduleRender();
    }catch(error){toast(error.message||'Не удалось загрузить карту.','error')}
    finally{loading=false}
  }

  async function post179(action,payload={}){
    if(actionBusy)return false;actionBusy=true;
    try{
      const response=await fetch('/government-v179/api/action',{method:'POST',cache:'no-store',headers,body:JSON.stringify({action,chat_id:chatId,...payload})});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      toast(data.message||'Готово.');tg?.HapticFeedback?.notificationOccurred?.('success');closeSheet();await load(true);return true;
    }catch(error){toast(error.message||'Действие не выполнено.','error');tg?.HapticFeedback?.notificationOccurred?.('error');return false}
    finally{actionBusy=false}
  }

  function chooseLayout(){
    const view=viewport();const width=view?.clientWidth||window.innerWidth,height=view?.clientHeight||window.innerHeight;
    return width<760||height>width*1.08?'mobile':'wide';
  }
  function districtStats(key){return (mapData()?.districts||[]).find(row=>row.key===key)||{objects:0,active:0,construction:0,problems:0,institutions:0}}
  function districtRows(){const layout=currentLayout();if(!layout)return[];return Object.entries(layout.districts||{}).map(([key,value])=>({key,...value,...districtStats(key)}))}
  function sprite(id){return `<svg class="r183-sprite" aria-hidden="true"><use href="${SPRITE}#${esc(id)}"></use></svg>`}

  function topBar(data){
    const m=data.metrics||{};
    return `<div class="r183-fullscreen-bar"><button type="button" data-r183-close-fullscreen>✕ <span>Закрыть</span></button><strong>🗺 Живой город</strong><div><span>⭐ ${fmt(m.trust)}</span><span>🏗 ${fmt(m.building)}</span><span>⚠ ${fmt(m.problems||0)}</span></div><button type="button" data-r183-refresh>↻</button></div>`;
  }
  function metrics(data){
    const m=data.metrics||{};
    return `<div class="r183-metrics"><article><span>💰</span><div><small>КАЗНА</small><b>${fmt(m.treasury)}</b></div></article><article><span>⭐</span><div><small>ДОВЕРИЕ</small><b>${fmt(m.trust)} / 100</b></div></article><article><span>🏗</span><div><small>${esc(m.development_title||'РАЗВИТИЕ')}</small><b>${fmt(m.development)}%</b></div></article><article><span>⚠</span><div><small>ПРОБЛЕМЫ</small><b>${fmt(m.problems||0)}</b></div></article></div>`;
  }

  function compactControls(){
    const filters=[['all','🌐','Всё'],['construction','🏗','Стройки'],['active','✅','Работает'],['problems','⚠','Проблемы'],['institutions','🏛','Учреждения']];
    return `<section class="r183-command"><div class="r183-filter-row">${filters.map(([key,emoji,title])=>`<button type="button" class="${activeFilter===key?'active':''}" data-r183-filter="${key}"><span>${emoji}</span><b>${title}</b></button>`).join('')}<button type="button" class="${districtMenu?'active':''}" data-r183-district-menu>☰ <b>Районы</b></button></div>${districtMenu?districtPanel():''}</section>`;
  }
  function districtPanel(){
    const rows=[{key:'all',emoji:'🌐',title:'Всё государство',objects:(mapData()?.objects||[]).length},...districtRows()];
    return `<div class="r183-district-panel">${rows.map(row=>`<button type="button" class="${activeDistrict===row.key?'active':''}" data-r183-district="${esc(row.key)}"><span>${esc(row.emoji)}</span><div><b>${esc(row.title)}</b><small>${fmt(row.active||0)} работает · ${fmt(row.construction||0)} строится</small></div><em>${fmt(row.objects||0)}</em></button>`).join('')}</div>`;
  }
  function activeDistrictChip(){
    if(activeDistrict==='all')return'';
    const row=districtRows().find(item=>item.key===activeDistrict);
    return `<div class="r183-district-chip"><span>${esc(row?.emoji||'')} <b>${esc(row?.title||activeDistrict)}</b></span><small>${fmt(row?.objects||0)} объектов${row?.problems?` · ⚠ ${fmt(row.problems)}`:''}</small><button type="button" data-r183-district="all">Показать всё</button></div>`;
  }
  function toolbar(){
    return `<div class="r183-toolbar"><div><button type="button" data-r183-fit>⌖ <span>ВЕСЬ ГОРОД</span></button><button type="button" data-r183-zoom-out>−</button><button type="button" data-r183-zoom-in>＋</button></div><div><button type="button" class="${miniVisible?'active':''}" data-r183-mini>▤</button><button type="button" data-r183-refresh>↻</button></div></div>`;
  }

  function districtLayer(){
    return districtRows().map(row=>`<section class="r183-zone district-${esc(row.key)}" data-r183-zone="${esc(row.key)}" style="left:${row.x}px;top:${row.y}px;width:${row.width}px;height:${row.height}px"><div class="r183-zone-title"><span>${esc(row.emoji)}</span><div><b>${esc(row.title)}</b><small>${fmt(row.active)} работает · ${fmt(row.construction)} строится${row.problems?` · ⚠ ${fmt(row.problems)}`:''}</small></div></div><i></i></section>`).join('');
  }
  function roadLayer(){
    const size=worldSize(),roads=currentLayout()?.roads||[];
    return `<svg class="r183-roads" viewBox="0 0 ${size.width} ${size.height}" aria-hidden="true"><defs><filter id="r183RoadShadow"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity=".35"/></filter></defs>${roads.map(path=>`<path class="road-edge" d="${esc(path)}"></path><path class="road-main" d="${esc(path)}"></path><path class="road-mark" d="${esc(path)}"></path>`).join('')}${accessRoads()}</svg>`;
  }
  function accessRoads(){
    const layout=currentLayout();if(!layout)return'';
    return (mapData()?.objects||[]).map(item=>{const p=layout.plots?.[item.plot_id],d=layout.districts?.[item.district];if(!p||!d)return'';const cx=d.x+d.width/2,cy=d.y+d.height/2;const tx=Math.abs(p.x-cx)>Math.abs(p.y-cy)?cx:p.x,ty=Math.abs(p.x-cx)>Math.abs(p.y-cy)?p.y:cy;return `<path class="road-access" d="M ${p.x} ${p.y+24} L ${tx} ${ty}"></path>`}).join('');
  }
  function decorationNode(item){
    const icons={tree:'♣',lamp:'•',park:'✿',fountain:'◉',parking:'P',truck:'▰',pipe:'⌁',car:'◆',barrier:'═',flag:'⚑'};
    return `<i class="r183-decor decor-${esc(item.type)}" style="left:${item.x}px;top:${item.y}px;--s:${item.scale};--r:${item.rotation}deg">${esc(icons[item.type]||'•')}</i>`;
  }
  function visualPosition(item){return currentLayout()?.plots?.[item.plot_id]||{x:item.x||0,y:item.y||0}}
  function landmarkPosition(item){return currentLayout()?.landmarks?.[item.key]||{x:item.x||0,y:item.y||0}}
  function filterMatches(item){if(activeFilter==='construction')return item.is_construction;if(activeFilter==='active')return item.is_active;if(activeFilter==='problems')return item.is_problem;if(activeFilter==='institutions')return false;return true}

  function spriteForObject(item){
    const stage=String(item.construction_stage||'complete');
    if(stage==='plan')return'construction_plan';
    if(stage==='foundation')return'construction_foundation';
    return String(item.building_key||'administration');
  }
  function buildingNode(item){
    const pos=visualPosition(item),selected=selectedPlot===String(item.plot_id),stage=String(item.construction_stage||'complete');
    return `<button type="button" class="r183-object stage-${esc(stage)} ${selected?'selected':''} ${item.is_problem?'problem':''}" style="left:${pos.x}px;top:${pos.y}px" data-r183-object="${esc(item.plot_id)}" data-district="${esc(item.district)}"><span class="r183-building">${sprite(spriteForObject(item))}${['frame','shell','finishing'].includes(stage)?'<i class="scaffold"></i>':''}${item.is_problem?'<u class="warning">!</u>':''}${item.is_construction?`<u class="progress">${esc(item.progress_label||'')}</u>`:''}</span><b>${esc(item.short_title||item.title)}</b><small>${esc(statusLabel(item.status))}</small></button>`;
  }
  function landmarkNode(item){
    const pos=landmarkPosition(item),id=['presidency','duma','finance','court','oversight'].includes(item.key)?item.key:'administration';
    return `<button type="button" class="r183-landmark" style="left:${pos.x}px;top:${pos.y}px" data-r183-landmark="${esc(item.key)}" data-district="${esc(item.district)}">${sprite(id)}<b>${esc(item.short_title||item.title)}</b></button>`;
  }
  function emptyPlotNode(item){
    const pos=currentLayout()?.plots?.[item.plot_id];if(!pos)return'';
    const show=activeFilter==='all'||activeFilter==='construction';
    return `<button type="button" class="r183-empty-plot ${show?'':'hidden'}" style="left:${pos.x}px;top:${pos.y}px" data-r183-empty="${esc(item.plot_id)}" data-district="${esc(item.district)}"><span>＋</span><small>Свободный участок</small></button>`;
  }
  function eventMarker(item,index){
    const d=currentLayout()?.districts?.[item.district];if(!d)return'';
    const x=d.x+d.width-48-(index%2)*52,y=d.y+54+Math.floor(index/2)*50;
    return `<button type="button" class="r183-event event-${esc(item.event_class)}" style="left:${x}px;top:${y}px" data-r183-event="${esc(item.key)}"><span>${esc(item.emoji||'🏛')}</span><i></i></button>`;
  }
  function developmentDecor(){
    const level=Number(mapData()?.development?.level)||1,layout=currentLayout();if(!layout)return'';
    const gov=layout.districts?.government;if(!gov)return'';
    let html='';
    if(level>=2)html+=`<i class="r183-dev fountain" style="left:${gov.x+gov.width/2}px;top:${gov.y+gov.height-58}px">◉</i>`;
    if(level>=3)html+=`<i class="r183-dev monument" style="left:${gov.x+gov.width/2}px;top:${gov.y+gov.height/2}px">★</i>`;
    if(level>=4)html+=`<i class="r183-dev flag-a" style="left:${gov.x+34}px;top:${gov.y+50}px">⚑</i><i class="r183-dev flag-b" style="left:${gov.x+gov.width-34}px;top:${gov.y+50}px">⚑</i>`;
    if(level>=5)html+=`<i class="r183-dev crown" style="left:${gov.x+gov.width/2}px;top:${gov.y+25}px">♛</i>`;
    return html;
  }
  function traffic(){
    const count=Math.max(1,Number(mapData()?.development?.traffic)||1);
    return Array.from({length:count},(_,i)=>`<i class="r183-vehicle vehicle-${i+1}">${i%2?'◆':'▰'}</i>`).join('');
  }
  function minimap(){
    const layout=currentLayout(),size=worldSize();if(!layout)return'';
    return `<div class="r183-minimap ${miniVisible?'':'hidden'}" id="r183Minimap"><button type="button" data-r183-mini-close>×</button>${Object.entries(layout.districts).map(([key,row])=>`<button type="button" class="district-${esc(key)}" data-r183-mini-district="${esc(key)}" style="left:${row.x/size.width*100}%;top:${row.y/size.height*100}%;width:${row.width/size.width*100}%;height:${row.height/size.height*100}%"></button>`).join('')}${(mapData()?.objects||[]).map(item=>{const p=visualPosition(item);return `<i style="left:${p.x/size.width*100}%;top:${p.y/size.height*100}%"></i>`}).join('')}<u id="r183MiniView"></u></div>`;
  }

  function world(){
    const data=mapData(),layout=currentLayout(),size=worldSize();if(!data||!layout)return'';
    const hour=new Date().getHours(),night=hour<7||hour>=20,level=Number(data.development?.level)||1;
    return `<div class="r183-viewport ${night?'night':'day'}" id="r183Viewport"><div class="r183-world dev-tier-${level}" id="r183World" style="width:${size.width}px;height:${size.height}px"><div class="r183-terrain"></div>${districtLayer()}${roadLayer()}${(layout.decorations||[]).map(decorationNode).join('')}${developmentDecor()}${traffic()}${(data.empty_plots||[]).map(emptyPlotNode).join('')}${(data.landmarks||[]).map(landmarkNode).join('')}${(data.objects||[]).map(buildingNode).join('')}${(data.program_events||[]).map(eventMarker).join('')}</div>${minimap()}</div>`;
  }

  function scheduleRender(){cancelAnimationFrame(renderFrame);renderFrame=requestAnimationFrame(render)}
  function render(){
    ensureLayout();const data=mapData(),mount=document.getElementById('r183Map');if(!data||!mount)return;
    const nextMode=chooseLayout();if(nextMode!==layoutMode){layoutMode=nextMode;cameraReady=false}
    mount.innerHTML=`${topBar(data)}${metrics(data)}${compactControls()}${activeDistrictChip()}${toolbar()}${world()}<footer class="r183-summary"><span>✅ Работает <b>${fmt(data.metrics?.working)}</b></span><span>🏗 Строится <b>${fmt(data.metrics?.building)}</b></span><span>💸 Долг <b>${fmt(data.metrics?.maintenance_debt)}</b></span><small>MAP ${esc(data.map_client_version||'183')}</small></footer>`;
    bindGestures();
    if(!cameraReady){fitWorld('contain',false);cameraReady=true}else applyTransform();
    applyVisibility();
  }

  function scheduleTransform(){cancelAnimationFrame(transformFrame);transformFrame=requestAnimationFrame(applyTransform)}
  function applyTransform(){
    const node=worldNode(),view=viewport();if(!node||!view)return;
    node.style.transform=`translate3d(${camera.x}px,${camera.y}px,0) scale(${camera.scale})`;
    node.classList.toggle('zoom-far',camera.scale<.72);node.classList.toggle('zoom-near',camera.scale>1.2);updateMini();
  }
  function fitBounds(bounds,mode='contain',animate=true){
    const view=viewport();if(!view||!bounds)return;const pad=fullscreen?12:14;
    const sx=(view.clientWidth-pad*2)/Number(bounds.width),sy=(view.clientHeight-pad*2)/Number(bounds.height),scale=mode==='cover'?Math.max(sx,sy):Math.min(sx,sy);
    camera.scale=Math.max(.46,Math.min(2.7,scale));camera.x=Math.round(view.clientWidth/2-(Number(bounds.x)+Number(bounds.width)/2)*camera.scale);camera.y=Math.round(view.clientHeight/2-(Number(bounds.y)+Number(bounds.height)/2)*camera.scale);
    if(animate)worldNode()?.classList.add('camera-animate');scheduleTransform();if(animate)setTimeout(()=>worldNode()?.classList.remove('camera-animate'),340);
  }
  function fitWorld(mode='contain',animate=true){const size=worldSize();fitBounds({x:0,y:0,width:size.width,height:size.height},mode,animate)}
  function focusDistrict(key,animate=true){
    activeDistrict=key;districtMenu=false;
    if(key==='all')fitWorld('contain',animate);else{const bounds=currentLayout()?.districts?.[key];if(bounds)fitBounds(bounds,'contain',animate)}
    scheduleRender();
  }
  function focusObject(item){const view=viewport(),pos=visualPosition(item);if(!view)return;camera.scale=Math.max(1.08,camera.scale);camera.x=Math.round(view.clientWidth/2-pos.x*camera.scale);camera.y=Math.round(view.clientHeight/2-pos.y*camera.scale);scheduleTransform()}
  function zoomBy(mult){const view=viewport();if(!view)return;const cx=(view.clientWidth/2-camera.x)/camera.scale,cy=(view.clientHeight/2-camera.y)/camera.scale;camera.scale=Math.max(.46,Math.min(2.8,camera.scale*mult));camera.x=Math.round(view.clientWidth/2-cx*camera.scale);camera.y=Math.round(view.clientHeight/2-cy*camera.scale);scheduleTransform()}

  function applyVisibility(){
    document.querySelectorAll('.r183-object').forEach(node=>{const item=itemByPlot(node.dataset.r183Object),show=Boolean(item&&filterMatches(item)),district=activeDistrict==='all'||item?.district===activeDistrict;node.classList.toggle('hidden',!show);node.classList.toggle('dim',show&&!district)});
    document.querySelectorAll('.r183-landmark').forEach(node=>{const show=activeFilter==='all'||activeFilter==='institutions',district=activeDistrict==='all'||node.dataset.district===activeDistrict;node.classList.toggle('hidden',!show);node.classList.toggle('dim',show&&!district)});
    document.querySelectorAll('.r183-empty-plot').forEach(node=>{const show=(activeFilter==='all'||activeFilter==='construction')&&(activeDistrict==='all'||node.dataset.district===activeDistrict);node.classList.toggle('hidden',!show)});
    document.querySelectorAll('.r183-zone').forEach(node=>{const selected=activeDistrict==='all'||node.dataset.r183Zone===activeDistrict;node.classList.toggle('dim',!selected);node.classList.toggle('selected',activeDistrict!=='all'&&node.dataset.r183Zone===activeDistrict)});
  }
  function updateMini(){
    const mini=document.getElementById('r183Minimap'),box=document.getElementById('r183MiniView'),view=viewport();if(!mini||!box||!view)return;
    const size=worldSize(),left=Math.max(0,Math.min(size.width,-camera.x/camera.scale)),top=Math.max(0,Math.min(size.height,-camera.y/camera.scale));
    box.style.left=`${left/size.width*100}%`;box.style.top=`${top/size.height*100}%`;box.style.width=`${Math.min(size.width,view.clientWidth/camera.scale)/size.width*100}%`;box.style.height=`${Math.min(size.height,view.clientHeight/camera.scale)/size.height*100}%`;
  }
  function toggleFullscreen(force){
    fullscreen=typeof force==='boolean'?force:!fullscreen;document.querySelector('.r183-screen')?.classList.toggle('r183-fullscreen',fullscreen);document.body.classList.toggle('r183-map-fullscreen',fullscreen);closeSheet();
    try{if(fullscreen){tg?.expand?.();tg?.requestFullscreen?.()}else tg?.exitFullscreen?.()}catch(_error){}
    cameraReady=false;setTimeout(scheduleRender,100);
  }

  function bindGestures(){
    const view=viewport();if(!view||view.__r183Bound)return;view.__r183Bound=true;
    view.addEventListener('pointerdown',event=>{if(event.target.closest('button,.r183-minimap'))return;view.setPointerCapture?.(event.pointerId);pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});if(pointers.size===1)gesture={mode:'pan',x:event.clientX,y:event.clientY,baseX:camera.x,baseY:camera.y};if(pointers.size===2)gesture={mode:'pinch',distance:pointerDistance(),scale:camera.scale,center:pointerCenter(),baseX:camera.x,baseY:camera.y}});
    view.addEventListener('pointermove',event=>{if(!pointers.has(event.pointerId))return;pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});if(pointers.size>=2){if(gesture?.mode!=='pinch')gesture={mode:'pinch',distance:pointerDistance(),scale:camera.scale,center:pointerCenter(),baseX:camera.x,baseY:camera.y};const next=Math.max(.46,Math.min(2.8,gesture.scale*pointerDistance()/Math.max(1,gesture.distance))),center=pointerCenter();camera.scale=next;camera.x=gesture.baseX+(center.x-gesture.center.x);camera.y=gesture.baseY+(center.y-gesture.center.y);scheduleTransform();event.preventDefault()}else if(pointers.size===1&&gesture?.mode==='pan'){camera.x=gesture.baseX+(event.clientX-gesture.x);camera.y=gesture.baseY+(event.clientY-gesture.y);scheduleTransform();event.preventDefault()}},{passive:false});
    const finish=event=>{pointers.delete(event.pointerId);if(pointers.size===1){const point=[...pointers.values()][0];gesture={mode:'pan',x:point.x,y:point.y,baseX:camera.x,baseY:camera.y}}else if(!pointers.size)gesture=null};
    view.addEventListener('pointerup',finish);view.addEventListener('pointercancel',finish);
  }
  function pointerDistance(){const rows=[...pointers.values()];return rows.length<2?1:Math.hypot(rows[0].x-rows[1].x,rows[0].y-rows[1].y)}
  function pointerCenter(){const rows=[...pointers.values()];return rows.length<2?{x:0,y:0}:{x:(rows[0].x+rows[1].x)/2,y:(rows[0].y+rows[1].y)/2}}

  function objectSheet(item){
    const project=!item.building_id,canManage=Boolean(mapData()?.can_propose),district=districtRows().find(row=>row.key===item.district),contributors=(item.contributors||[]).map((row,index)=>`<div class="r183-contributor"><span>${index+1}. ${esc(row.name)}</span><b>${fmt(row.amount)}</b></div>`).join('')||'<div class="empty">Вкладчиков пока нет.</div>';
    return `<article class="r183-detail"><div class="r183-detail-hero">${sprite(spriteForObject(item))}<div><small>${esc(statusLabel(item.status))} · ${esc(district?.title||item.district)}</small><b>${esc(item.title)}</b><em>${esc(item.source_title||'Государственное финансирование')}</em></div></div><p>${esc(item.effect)}</p><div class="r183-detail-grid"><span>Инициатор<b>${esc(item.initiator_name||'Государство')}</b></span><span>Стоимость<b>${fmt(item.cost)}</b></span>${project?`<span>Финансирование<b>${fmt(item.funded_amount)} / ${fmt(item.total_cost)}</b></span><span>Готовность<b>${fmt(item.progress)}%</b></span>`:`<span>Содержание<b>${fmt(item.maintenance)}</b></span><span>Следующая оплата<b>${date(item.next_maintenance_at)}</b></span>`}${Number(item.maintenance_debt)>0?`<span class="problem">Долг<b>${fmt(item.maintenance_debt)}</b></span>`:''}</div><section><small>ГЛАВНЫЕ ВКЛАДЧИКИ</small>${contributors}</section><div class="r183-sheet-actions">${project&&item.status==='awaiting_funding'?`<button type="button" class="positive" data-r183-contribute="${esc(item.plot_id)}">🤝 ВЛОЖИТЬСЯ</button>`:''}${project&&item.status==='awaiting_funding'&&canManage?`<button type="button" class="action" data-r183-fund="${esc(item.plot_id)}">💰 НАПРАВИТЬ СРЕДСТВА</button>`:''}${project?'<button type="button" class="secondary" data-r183-open-construction>🏗 ОТКРЫТЬ ПРОЕКТ</button>':''}${Number(item.maintenance_debt)>0&&canManage?`<button type="button" class="danger" data-r183-pay-debt="${esc(item.plot_id)}">🧾 ПОГАСИТЬ ДОЛГ</button>`:''}<button type="button" class="secondary" data-r183-show="${esc(item.plot_id)}">⌖ ПОКАЗАТЬ</button></div></article>`;
  }
  function openObject(item){
    if(!item)return;selectedPlot=String(item.plot_id);document.querySelectorAll('.r183-object').forEach(node=>node.classList.toggle('selected',node.dataset.r183Object===selectedPlot));openSheet(item.title,`${statusLabel(item.status)} · карта государства`,objectSheet(item));focusObject(item);tg?.HapticFeedback?.impactOccurred?.('light');
  }
  function plotSheet(plot){
    const can=Boolean(mapData()?.can_propose),catalog=(mapData()?.construction_catalog||[]).filter(item=>item.district===plot.district),district=districtRows().find(row=>row.key===plot.district);
    if(!can)return `<article class="r183-empty-info"><span>🏗</span><h4>Свободный участок</h4><p>Здесь можно разместить государственный объект района «${esc(district?.title||plot.district)}». Создавать проекты могут уполномоченные чиновники.</p><button type="button" class="secondary wide" data-r183-open-construction>ОТКРЫТЬ СТРОИТЕЛЬСТВО</button></article>`;
    return `<article class="r183-empty-info"><span>🏗</span><h4>Новый объект района</h4><p>Выбери проект. После создания система займёт ближайший свободный участок этого района.</p></article><div class="r183-plot-catalog">${catalog.map(item=>`<form data-r183-propose-form data-building="${esc(item.key)}"><header><span>${esc(item.emoji)}</span><div><b>${esc(item.title)}</b><small>${duration(item.duration)} · ${item.count}/3</small></div><strong>${fmt(item.cost)}</strong></header><p>${esc(item.effect)}</p><select name="source_key">${(item.sources||[]).map(source=>`<option value="${esc(source.key)}">${esc(source.title)} · ${fmt(source.balance)}</option>`).join('')}</select><button type="submit" class="action wide" ${item.available?'':'disabled'}>${item.available?'🏗 СОЗДАТЬ ПРОЕКТ':'ЛИМИТ 3 ОБЪЕКТА'}</button></form>`).join('')||'<div class="empty">Для этого района пока нет доступных типов объектов.</div>'}</div>`;
  }
  function openPlot(plot){const row=districtRows().find(item=>item.key===plot.district);openSheet('Свободный участок',`${row?.emoji||'🏗'} ${row?.title||plot.district}`,plotSheet(plot))}
  function openEvent(key){const item=(mapData()?.program_events||[]).find(row=>row.key===key);if(!item)return;openSheet(item.event_label||item.title,'🏛 ГОСУДАРСТВЕННОЕ СОБЫТИЕ',`<article class="r183-event-detail"><span>${esc(item.emoji||'🏛')}</span><h4>${esc(item.title)}</h4><p>Программа сейчас действует в этом районе и визуально отображается на карте.</p><small>Завершение: ${date(item.ends_at)}</small></article>`)}

  async function contribute(item){const max=Math.max(0,Number(item.remaining)||0),value=Number(prompt(`Сколько влияния вложить?\nОсталось: ${fmt(max)}`,String(Math.min(10000,max))));if(!Number.isFinite(value)||value<100)return;await post179('construction_contribute',{project_id:item.project_id,amount:Math.floor(value),request_id:requestId()})}
  async function fund(item){const max=Math.max(0,Number(item.remaining)||0),catalog=(mapData()?.construction_catalog||[]).find(row=>row.key===item.building_key),source=catalog?.sources?.[0];if(!source){toast('Нет доступного источника финансирования.','error');return}const value=Number(prompt(`Сколько направить из «${source.title}»?\nОсталось: ${fmt(max)}`,String(max)));if(!Number.isFinite(value)||value<=0)return;await post179('construction_fund',{project_id:item.project_id,source_key:source.key,amount:Math.floor(value),request_id:requestId()})}
  async function payDebt(item){const catalog=(mapData()?.construction_catalog||[]).find(row=>row.key===item.building_key),source=catalog?.sources?.[0];if(!source){toast('Нет доступного источника.','error');return}if(!confirm(`Погасить долг ${fmt(item.maintenance_debt)} из «${source.title}»?`))return;await post179('construction_debt_pay',{building_id:item.building_id,source_key:source.key,request_id:requestId()})}

  document.addEventListener('click',event=>{
    const target=event.target;
    if(target.closest?.('[data-r183-refresh]')){load(true);return}
    if(target.closest?.('[data-r183-fullscreen]')){toggleFullscreen(true);return}
    if(target.closest?.('[data-r183-close-fullscreen]')){toggleFullscreen(false);return}
    if(target.closest?.('[data-r183-fit]')){activeDistrict='all';fitWorld('contain',true);scheduleRender();return}
    if(target.closest?.('[data-r183-zoom-in]')){zoomBy(1.2);return}
    if(target.closest?.('[data-r183-zoom-out]')){zoomBy(.82);return}
    const filter=target.closest?.('[data-r183-filter]');if(filter){activeFilter=filter.dataset.r183Filter;scheduleRender();return}
    if(target.closest?.('[data-r183-district-menu]')){districtMenu=!districtMenu;scheduleRender();return}
    const district=target.closest?.('[data-r183-district]');if(district){focusDistrict(district.dataset.r183District,true);return}
    const miniDistrict=target.closest?.('[data-r183-mini-district]');if(miniDistrict){focusDistrict(miniDistrict.dataset.r183MiniDistrict,true);return}
    if(target.closest?.('[data-r183-mini]')){miniVisible=!miniVisible;scheduleRender();return}
    if(target.closest?.('[data-r183-mini-close]')){miniVisible=false;scheduleRender();return}
    if(target.closest?.('[data-r183-sheet-close]')){closeSheet();return}
    const object=target.closest?.('[data-r183-object]');if(object){openObject(itemByPlot(object.dataset.r183Object));return}
    const empty=target.closest?.('[data-r183-empty]');if(empty){const plot=(mapData()?.empty_plots||[]).find(row=>row.plot_id===empty.dataset.r183Empty);if(plot)openPlot(plot);return}
    const eventNode=target.closest?.('[data-r183-event]');if(eventNode){openEvent(eventNode.dataset.r183Event);return}
    const landmark=target.closest?.('[data-r183-landmark]');if(landmark){const item=(mapData()?.landmarks||[]).find(row=>row.key===landmark.dataset.r183Landmark);if(item)openSheet(item.title,'🏛 ГОСУДАРСТВЕННОЕ УЧРЕЖДЕНИЕ',`<article class="r183-institution">${sprite(item.key)}<p>Постоянный государственный центр. Он служит ориентиром карты и не занимает лимит строительных объектов.</p></article>`);return}
    if(target.closest?.('[data-r183-open-construction]')){document.querySelector('[data-tab="construction179"]')?.click();closeSheet();return}
    const contributeButton=target.closest?.('[data-r183-contribute]');if(contributeButton){contribute(itemByPlot(contributeButton.dataset.r183Contribute));return}
    const fundButton=target.closest?.('[data-r183-fund]');if(fundButton){fund(itemByPlot(fundButton.dataset.r183Fund));return}
    const debtButton=target.closest?.('[data-r183-pay-debt]');if(debtButton){payDebt(itemByPlot(debtButton.dataset.r183PayDebt));return}
    const showButton=target.closest?.('[data-r183-show]');if(showButton){const item=itemByPlot(showButton.dataset.r183Show);closeSheet();if(item)focusObject(item);return}
    const nav=target.closest?.('[data-tab="map183"]');if(nav){cameraReady=false;setTimeout(()=>{load(true);scheduleRender()},80)}
  });

  document.addEventListener('submit',event=>{
    const form=event.target;if(!form.matches?.('[data-r183-propose-form]'))return;
    event.preventDefault();const values=Object.fromEntries(new FormData(form).entries()),button=form.querySelector('button');
    if(button){button.disabled=true;button.textContent='⌛ СОЗДАЁМ…'}
    post179('construction_propose',{building_key:form.dataset.building,source_key:values.source_key,request_id:requestId()}).finally(()=>{if(button?.isConnected){button.disabled=false;button.textContent='🏗 СОЗДАТЬ ПРОЕКТ'}});
  });

  document.addEventListener('keydown',event=>{if(event.key==='Escape'){if(document.getElementById('r183Sheet')?.classList.contains('open'))closeSheet();else if(fullscreen)toggleFullscreen(false)}});
  window.addEventListener('pageshow',()=>{cameraReady=false;load(true)});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)load(true)});
  const resizeHandler=()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{cameraReady=false;scheduleRender()},180)};
  window.addEventListener('resize',resizeHandler);window.visualViewport?.addEventListener('resize',resizeHandler);
  ensureLayout();load();
})();
