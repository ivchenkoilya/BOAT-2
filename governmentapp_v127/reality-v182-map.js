(()=>{
  'use strict';
  if(window.__governmentRealityV182Map)return;
  window.__governmentRealityV182Map=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
  const requestId=()=>globalThis.crypto?.randomUUID?.()||`r182-${Date.now()}-${Math.random().toString(36).slice(2)}`;

  let state=null,busy=false,fullscreen=false,filtersOpen=false,miniVisible=true;
  let activeDistrict='all',activeFilter='all',selectedPlot='',layoutMode='mobile',fitMode='cover';
  let camera={x:0,y:0,scale:1},gesture=null,renderFrame=0,transformFrame=0,resizeTimer=0;
  const pointers=new Map();

  const mapData=()=>state?.reality182?.map||null;
  const viewport=()=>document.getElementById('r182Viewport');
  const worldNode=()=>document.getElementById('r182World');
  const currentLayout=()=>mapData()?.layouts?.[layoutMode]||null;
  const worldSize=()=>currentLayout()?.world||{width:720,height:1120};
  const itemByPlot=id=>(mapData()?.objects||[]).find(item=>String(item.plot_id)===String(id));
  const statusLabel=status=>({awaiting_vote:'Ожидает голосования',awaiting_funding:'Собирает средства',building:'Строится',completed:'Построено',active:'Работает',underfunded:'Нет финансирования',frozen:'Заморожено',cancelled:'Отменено'})[status]||String(status||'Неизвестно');

  function toast(text,type='success'){
    const node=document.getElementById('toast');if(!node)return;
    node.textContent=String(text||'Готово');node.className=`toast show ${type}`;
    clearTimeout(node.__r182);node.__r182=setTimeout(()=>node.className='toast',3600);
  }

  function ensureSheet(){
    if(document.getElementById('r182Sheet'))return;
    document.body.insertAdjacentHTML('beforeend',`<div class="r182-sheet-backdrop" id="r182SheetBackdrop" data-r182-sheet-close></div><aside class="r182-sheet" id="r182Sheet" aria-hidden="true"><div class="r182-sheet-grip"></div><header><div><small id="r182SheetKicker">ОБЪЕКТ НА КАРТЕ</small><h3 id="r182SheetTitle">Государственный объект</h3></div><button type="button" data-r182-sheet-close>×</button></header><div class="r182-sheet-body" id="r182SheetBody"></div></aside>`);
  }

  function ensureLayout(){
    document.querySelector('.screen[data-screen="map180"]')?.remove();
    document.querySelector('.screen[data-screen="map181"]')?.remove();
    document.querySelector('[data-tab="map180"]')?.remove();
    document.querySelector('[data-tab="map181"]')?.remove();
    const stack=document.querySelector('.screen-stack'),nav=document.getElementById('bottomNav');
    if(stack&&!document.querySelector('.screen[data-screen="map182"]')){
      stack.insertAdjacentHTML('beforeend',`<section class="screen r182-screen" data-screen="map182"><div class="r182-screen-head"><div><small>REALITY 182 · КАРТА ГОСУДАРСТВА 3.0</small><h2>Живое государство</h2></div><div><button type="button" class="secondary" data-r182-refresh>↻</button><button type="button" class="action" data-r182-fullscreen>⛶ НА ВЕСЬ ЭКРАН</button></div></div><div id="r182Map"></div></section>`);
    }
    if(nav&&!nav.querySelector('[data-tab="map182"]')){
      const button=document.createElement('button');button.type='button';button.dataset.tab='map182';button.innerHTML='<span>🗺</span><small>Карта</small>';
      nav.insertBefore(button,nav.querySelector('[data-tab="construction179"]')||null);
    }
    ensureSheet();
  }

  async function load(force=false){
    if(!chatId||(busy&&!force))return;
    const own=!busy;if(own)busy=true;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_r182=${Date.now()}`,{cache:'no-store',headers});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось загрузить карту государства.');
      state=data;scheduleRender();
    }catch(error){toast(error.message||'Не удалось загрузить карту.','error')}
    finally{if(own)busy=false}
  }

  async function post179(action,payload={}){
    if(busy)return false;busy=true;
    try{
      const response=await fetch('/government-v179/api/action',{method:'POST',cache:'no-store',headers,body:JSON.stringify({action,chat_id:chatId,...payload})});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      toast(data.message||'Готово.');tg?.HapticFeedback?.notificationOccurred?.('success');await load(true);return true;
    }catch(error){toast(error.message||'Действие не выполнено.','error');tg?.HapticFeedback?.notificationOccurred?.('error');return false}
    finally{busy=false}
  }

  function chooseLayout(){
    const view=viewport();
    const width=view?.clientWidth||window.innerWidth,height=view?.clientHeight||window.innerHeight;
    return width<760||height>width*1.08?'mobile':'wide';
  }

  function districtStats(key){return (mapData()?.districts||[]).find(row=>row.key===key)||{objects:0,active:0,construction:0,problems:0}}
  function districtRows(){
    const layout=currentLayout();if(!layout)return[];
    return Object.entries(layout.districts||{}).map(([key,value])=>({key,...value,...districtStats(key)}));
  }

  function renderTop(data){
    const m=data.metrics||{};
    return `<div class="r182-fullscreen-bar"><button type="button" data-r182-close-fullscreen>✕ <span>Закрыть</span></button><strong>🗺 Государство</strong><div><span>⭐ ${fmt(m.trust)}</span><span>🏗 ${fmt(m.building)}</span><span>⚠ ${fmt(m.problems||0)}</span></div><button type="button" data-r182-refresh>↻</button></div>`;
  }

  function metrics(data){
    const m=data.metrics||{};
    return `<div class="r182-metrics"><article><span>💰</span><div><small>КАЗНА</small><b>${fmt(m.treasury)}</b></div></article><article><span>⭐</span><div><small>ДОВЕРИЕ</small><b>${fmt(m.trust)} / 100</b></div></article><article><span>🏗</span><div><small>РАЗВИТИЕ</small><b>${fmt(m.development)}%</b></div></article><article><span>⚠</span><div><small>ПРОБЛЕМЫ</small><b>${fmt(m.problems||0)}</b></div></article></div>`;
  }

  function districtButtons(){
    const rows=[{key:'all',emoji:'🌐',title:'Всё',objects:(mapData()?.objects||[]).length},...districtRows()];
    return `<div class="r182-districts">${rows.map(row=>`<button type="button" class="${activeDistrict===row.key?'active':''}" data-r182-district="${esc(row.key)}"><span>${esc(row.emoji)}</span><b>${esc(row.title)}</b><em>${fmt(row.objects||0)}</em></button>`).join('')}</div>`;
  }

  function filters(){
    const rows=mapData()?.filters||[];
    return `<div class="r182-filter-wrap ${filtersOpen?'open':''}"><button type="button" class="r182-filter-toggle ${filtersOpen?'active':''}" data-r182-filter-toggle>☰ ФИЛЬТРЫ</button><div class="r182-filters">${rows.map(row=>`<button type="button" class="${activeFilter===row.key?'active':''}" data-r182-filter="${esc(row.key)}"><span>${esc(row.emoji)}</span>${esc(row.title)}</button>`).join('')}</div></div>`;
  }

  function toolbar(){
    return `<div class="r182-toolbar"><div><button type="button" data-r182-fill>▣ <span>ЗАПОЛНИТЬ</span></button><button type="button" data-r182-fit>⌖ <span>ВСЯ КАРТА</span></button><button type="button" data-r182-zoom-out>−</button><button type="button" data-r182-zoom-in>＋</button></div><div><button type="button" class="${miniVisible?'active':''}" data-r182-mini>▤</button><button type="button" data-r182-refresh>↻</button></div></div>`;
  }

  function districtLayer(){
    return districtRows().map(row=>`<section class="r182-zone district-${esc(row.key)}" data-r182-zone="${esc(row.key)}" style="left:${row.x}px;top:${row.y}px;width:${row.width}px;height:${row.height}px"><div class="r182-zone-title"><span>${esc(row.emoji)}</span><div><b>${esc(row.title)}</b><small>${fmt(row.active)} работает · ${fmt(row.construction)} строится${row.problems?` · ⚠ ${fmt(row.problems)}`:''}</small></div></div><i></i></section>`).join('');
  }

  function roadLayer(){
    const size=worldSize(),roads=currentLayout()?.roads||[];
    return `<svg class="r182-roads" viewBox="0 0 ${size.width} ${size.height}" aria-hidden="true"><defs><filter id="r182RoadShadow"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity=".45"/></filter></defs>${roads.map(path=>`<path class="road-edge" d="${esc(path)}"></path><path class="road-main" d="${esc(path)}"></path><path class="road-mark" d="${esc(path)}"></path>`).join('')}</svg>`;
  }

  function decorationNode(item){
    const icons={tree:'♣',lamp:'•',park:'✿',fountain:'◉',parking:'P',truck:'▰',pipe:'⌁',car:'◆',barrier:'═',flag:'⚑'};
    return `<i class="r182-decor decor-${esc(item.type)}" style="left:${item.x}px;top:${item.y}px;--s:${item.scale};--r:${item.rotation}deg">${esc(icons[item.type]||'•')}</i>`;
  }

  function visualPosition(item){return currentLayout()?.plots?.[item.plot_id]||{x:item.x||0,y:item.y||0}}
  function landmarkPosition(item){return currentLayout()?.landmarks?.[item.key]||{x:item.x||0,y:item.y||0}}
  function filterMatches(item){if(activeFilter==='construction')return item.is_construction;if(activeFilter==='active')return item.is_active;if(activeFilter==='problems')return item.is_problem;if(activeFilter==='institutions')return false;return true}

  function buildingNode(item){
    const pos=visualPosition(item),selected=selectedPlot===String(item.plot_id),stage=String(item.construction_stage||'complete');
    return `<button type="button" class="r182-object visual-${esc(item.visual_class)} stage-${esc(stage)} ${selected?'selected':''} ${item.is_problem?'problem':''}" style="left:${pos.x}px;top:${pos.y}px" data-r182-object="${esc(item.plot_id)}" data-district="${esc(item.district)}"><span class="r182-shape"><i class="base"></i><i class="body"></i><i class="roof"></i><i class="detail"></i><strong>${esc(item.visual_symbol)}</strong>${item.is_active&&item.visual_class==='factory'?'<u class="smoke"></u>':''}${item.is_active&&item.visual_class==='police'?'<u class="siren"></u>':''}${item.is_active&&item.visual_class==='power'?'<u class="energy"></u>':''}${item.is_problem?'<u class="warning">!</u>':''}${item.is_construction?`<u class="build-stage">${esc(item.progress_label||'')}</u>`:''}</span><b>${esc(item.short_title)}</b><small>${esc(statusLabel(item.status))}</small></button>`;
  }

  function landmarkNode(item){
    const pos=landmarkPosition(item);
    return `<button type="button" class="r182-landmark visual-${esc(item.visual_class)}" style="left:${pos.x}px;top:${pos.y}px" data-r182-landmark="${esc(item.key)}" data-district="${esc(item.district)}"><span class="r182-shape"><i class="base"></i><i class="body"></i><i class="roof"></i><i class="detail"></i><strong>${esc(item.visual_symbol)}</strong></span><b>${esc(item.short_title)}</b></button>`;
  }

  function traffic(){return `<i class="r182-vehicle vehicle-a">▰</i><i class="r182-vehicle vehicle-b">◆</i><i class="r182-vehicle vehicle-c">▰</i>`}

  function minimap(){
    const layout=currentLayout(),size=worldSize();if(!layout)return'';
    return `<div class="r182-minimap ${miniVisible&&fitMode!=='contain'?'':'hidden'}" id="r182Minimap"><button type="button" data-r182-mini-close>×</button>${Object.entries(layout.districts).map(([key,row])=>`<i class="district-${esc(key)}" style="left:${row.x/size.width*100}%;top:${row.y/size.height*100}%;width:${row.width/size.width*100}%;height:${row.height/size.height*100}%"></i>`).join('')}<u id="r182MiniView"></u></div>`;
  }

  function world(){
    const data=mapData(),layout=currentLayout(),size=worldSize();if(!data||!layout)return'';
    const hour=new Date().getHours(),night=hour<7||hour>=20;
    return `<div class="r182-viewport ${night?'night':'day'}" id="r182Viewport"><div class="r182-world" id="r182World" style="width:${size.width}px;height:${size.height}px"><div class="r182-terrain"></div>${districtLayer()}${roadLayer()}${(layout.decorations||[]).map(decorationNode).join('')}${traffic()}${(data.landmarks||[]).map(landmarkNode).join('')}${(data.objects||[]).map(buildingNode).join('')}</div>${minimap()}</div>`;
  }

  function selectedDistrictList(){
    if(activeDistrict==='all')return'';
    const district=districtRows().find(row=>row.key===activeDistrict),rows=(mapData()?.objects||[]).filter(row=>row.district===activeDistrict&&filterMatches(row));
    return `<section class="r182-district-list"><header><div><small>ВЫБРАННЫЙ РАЙОН</small><b>${esc(district?.emoji||'')} ${esc(district?.title||activeDistrict)}</b></div><button type="button" data-r182-district="all">Показать всё</button></header><div>${rows.length?rows.map(row=>`<button type="button" data-r182-list-object="${esc(row.plot_id)}"><span>${esc(row.visual_symbol)}</span><div><b>${esc(row.short_title)}</b><small>${esc(statusLabel(row.status))}</small></div>${row.is_problem?'<em>⚠</em>':''}</button>`).join(''):'<p>Объектов с выбранным фильтром нет.</p>'}</div></section>`;
  }

  function scheduleRender(){cancelAnimationFrame(renderFrame);renderFrame=requestAnimationFrame(render)}
  function render(){
    ensureLayout();const data=mapData(),mount=document.getElementById('r182Map');if(!data||!mount)return;
    const oldMode=layoutMode;layoutMode=chooseLayout();if(oldMode!==layoutMode)fitMode='cover';
    mount.innerHTML=`${renderTop(data)}${metrics(data)}<section class="r182-controls"><div><small>РАЙОНЫ</small>${districtButtons()}</div>${filters()}</section>${toolbar()}${selectedDistrictList()}${world()}<footer class="r182-summary"><span>✅ Работает <b>${fmt(data.metrics?.working)}</b></span><span>🏗 Строится <b>${fmt(data.metrics?.building)}</b></span><span>💸 Долг <b>${fmt(data.metrics?.maintenance_debt)}</b></span></footer>`;
    bindGestures();
    if(activeDistrict==='all')fitWorld(fitMode,false);else focusDistrict(activeDistrict,false);
    applyVisibility();
  }

  function scheduleTransform(){cancelAnimationFrame(transformFrame);transformFrame=requestAnimationFrame(applyTransform)}
  function applyTransform(){
    const node=worldNode(),view=viewport();if(!node||!view)return;
    node.style.transform=`translate3d(${camera.x}px,${camera.y}px,0) scale(${camera.scale})`;
    node.classList.toggle('zoom-far',camera.scale<.78);node.classList.toggle('zoom-near',camera.scale>1.25);
    updateMini();
  }

  function fitBounds(bounds,mode='contain',animate=true){
    const view=viewport();if(!view||!bounds)return;
    const pad=fullscreen?18:15;
    const sx=(view.clientWidth-pad*2)/Number(bounds.width),sy=(view.clientHeight-pad*2)/Number(bounds.height);
    const scale=mode==='cover'?Math.max(sx,sy):Math.min(sx,sy);
    camera.scale=Math.max(.52,Math.min(2.6,scale));
    camera.x=Math.round(view.clientWidth/2-(Number(bounds.x)+Number(bounds.width)/2)*camera.scale);
    camera.y=Math.round(view.clientHeight/2-(Number(bounds.y)+Number(bounds.height)/2)*camera.scale);
    if(animate)worldNode()?.classList.add('camera-animate');scheduleTransform();
    if(animate)setTimeout(()=>worldNode()?.classList.remove('camera-animate'),350);
  }

  function fitWorld(mode='cover',animate=true){const size=worldSize();fitMode=mode;fitBounds({x:0,y:0,width:size.width,height:size.height},mode,animate);scheduleRenderMiniOnly()}
  function focusDistrict(key,animate=true){
    activeDistrict=key;
    if(key==='all'){fitWorld('cover',animate);return}
    const bounds=currentLayout()?.districts?.[key];if(bounds){fitMode='district';fitBounds(bounds,'contain',animate)}
    updateControls();
  }
  function focusObject(item){
    const view=viewport(),pos=visualPosition(item);if(!view)return;
    camera.scale=Math.max(1.18,camera.scale);camera.x=Math.round(view.clientWidth/2-pos.x*camera.scale);camera.y=Math.round(view.clientHeight/2-pos.y*camera.scale);scheduleTransform();
  }
  function zoomBy(mult){
    const view=viewport();if(!view)return;const cx=(view.clientWidth/2-camera.x)/camera.scale,cy=(view.clientHeight/2-camera.y)/camera.scale;
    camera.scale=Math.max(.52,Math.min(2.8,camera.scale*mult));camera.x=Math.round(view.clientWidth/2-cx*camera.scale);camera.y=Math.round(view.clientHeight/2-cy*camera.scale);fitMode='manual';scheduleTransform();
  }

  function applyVisibility(){
    document.querySelectorAll('.r182-object').forEach(node=>{const item=itemByPlot(node.dataset.r182Object);const show=Boolean(item&&filterMatches(item));const district=activeDistrict==='all'||item?.district===activeDistrict;node.classList.toggle('hidden',!show);node.classList.toggle('dim',show&&!district)});
    document.querySelectorAll('.r182-landmark').forEach(node=>{const show=activeFilter==='all'||activeFilter==='institutions';const district=activeDistrict==='all'||node.dataset.district===activeDistrict;node.classList.toggle('hidden',!show);node.classList.toggle('dim',show&&!district)});
    document.querySelectorAll('.r182-zone').forEach(node=>{const selected=activeDistrict==='all'||node.dataset.r182Zone===activeDistrict;node.classList.toggle('dim',!selected);node.classList.toggle('selected',activeDistrict!=='all'&&node.dataset.r182Zone===activeDistrict)});
  }
  function updateControls(){scheduleRender()}
  function scheduleRenderMiniOnly(){setTimeout(()=>{const mini=document.getElementById('r182Minimap');if(mini)mini.classList.toggle('hidden',!miniVisible||fitMode==='contain')},0)}

  function toggleFullscreen(force){
    fullscreen=typeof force==='boolean'?force:!fullscreen;
    document.querySelector('.r182-screen')?.classList.toggle('r182-fullscreen',fullscreen);document.body.classList.toggle('r182-map-fullscreen',fullscreen);closeSheet();
    try{if(fullscreen){tg?.expand?.();tg?.requestFullscreen?.()}else tg?.exitFullscreen?.()}catch(_error){}
    setTimeout(()=>{layoutMode=chooseLayout();if(activeDistrict==='all')fitWorld('cover',false);else focusDistrict(activeDistrict,false);scheduleRender()},100);
  }

  function updateMini(){
    const mini=document.getElementById('r182Minimap'),box=document.getElementById('r182MiniView'),view=viewport();if(!mini||!box||!view)return;
    const size=worldSize(),left=Math.max(0,Math.min(size.width,-camera.x/camera.scale)),top=Math.max(0,Math.min(size.height,-camera.y/camera.scale));
    box.style.left=`${left/size.width*100}%`;box.style.top=`${top/size.height*100}%`;box.style.width=`${Math.min(size.width,view.clientWidth/camera.scale)/size.width*100}%`;box.style.height=`${Math.min(size.height,view.clientHeight/camera.scale)/size.height*100}%`;
  }

  function bindGestures(){
    const view=viewport();if(!view||view.__r182Bound)return;view.__r182Bound=true;
    view.addEventListener('pointerdown',event=>{if(event.target.closest('button,.r182-minimap'))return;view.setPointerCapture?.(event.pointerId);pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});if(pointers.size===1)gesture={mode:'pan',x:event.clientX,y:event.clientY,baseX:camera.x,baseY:camera.y};if(pointers.size===2)gesture={mode:'pinch',distance:pointerDistance(),scale:camera.scale,center:pointerCenter(),baseX:camera.x,baseY:camera.y}});
    view.addEventListener('pointermove',event=>{if(!pointers.has(event.pointerId))return;pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});fitMode='manual';if(pointers.size>=2){if(gesture?.mode!=='pinch')gesture={mode:'pinch',distance:pointerDistance(),scale:camera.scale,center:pointerCenter(),baseX:camera.x,baseY:camera.y};const next=Math.max(.52,Math.min(2.8,gesture.scale*pointerDistance()/Math.max(1,gesture.distance))),center=pointerCenter();camera.scale=next;camera.x=gesture.baseX+(center.x-gesture.center.x);camera.y=gesture.baseY+(center.y-gesture.center.y);scheduleTransform();event.preventDefault()}else if(pointers.size===1&&gesture?.mode==='pan'){camera.x=gesture.baseX+(event.clientX-gesture.x);camera.y=gesture.baseY+(event.clientY-gesture.y);scheduleTransform();event.preventDefault()}},{passive:false});
    const finish=event=>{pointers.delete(event.pointerId);if(pointers.size===1){const point=[...pointers.values()][0];gesture={mode:'pan',x:point.x,y:point.y,baseX:camera.x,baseY:camera.y}}else if(!pointers.size)gesture=null};
    view.addEventListener('pointerup',finish);view.addEventListener('pointercancel',finish);
  }
  function pointerDistance(){const rows=[...pointers.values()];return rows.length<2?1:Math.hypot(rows[0].x-rows[1].x,rows[0].y-rows[1].y)}
  function pointerCenter(){const rows=[...pointers.values()];return rows.length<2?{x:0,y:0}:{x:(rows[0].x+rows[1].x)/2,y:(rows[0].y+rows[1].y)/2}}

  function sheetContent(item){
    const project=!item.building_id,canManage=Boolean(state?.reality179?.construction?.can_propose),district=districtRows().find(row=>row.key===item.district);
    const contributors=(item.contributors||[]).map((row,index)=>`<div class="r182-contributor"><span>${index+1}. ${esc(row.name)}</span><b>${fmt(row.amount)}</b></div>`).join('')||'<div class="empty">Вкладчиков пока нет.</div>';
    return `<article class="r182-detail"><div class="r182-detail-hero visual-${esc(item.visual_class)}"><span class="r182-shape"><i class="base"></i><i class="body"></i><i class="roof"></i><i class="detail"></i><strong>${esc(item.visual_symbol)}</strong></span><div><small>${esc(statusLabel(item.status))} · ${esc(district?.title||item.district)}</small><b>${esc(item.title)}</b><em>${esc(item.source_title||'Государственное финансирование')}</em></div></div><p>${esc(item.effect)}</p><div class="r182-detail-grid"><span>Инициатор<b>${esc(item.initiator_name||'Государство')}</b></span><span>Стоимость<b>${fmt(item.cost)}</b></span>${project?`<span>Финансирование<b>${fmt(item.funded_amount)} / ${fmt(item.total_cost)}</b></span><span>Готовность<b>${fmt(item.progress)}%</b></span>`:`<span>Содержание<b>${fmt(item.maintenance)}</b></span><span>Следующая оплата<b>${date(item.next_maintenance_at)}</b></span>`}${Number(item.maintenance_debt)>0?`<span class="problem">Долг<b>${fmt(item.maintenance_debt)}</b></span>`:''}</div><section><small>ГЛАВНЫЕ ВКЛАДЧИКИ</small>${contributors}</section><div class="r182-sheet-actions">${project&&item.status==='awaiting_funding'?`<button type="button" class="positive" data-r182-contribute="${esc(item.plot_id)}">🤝 ВЛОЖИТЬСЯ</button>`:''}${project&&item.status==='awaiting_funding'&&canManage?`<button type="button" class="action" data-r182-fund="${esc(item.plot_id)}">💰 НАПРАВИТЬ СРЕДСТВА</button>`:''}${project?'<button type="button" class="secondary" data-r182-open-construction>🏗 ОТКРЫТЬ ПРОЕКТ</button>':''}${Number(item.maintenance_debt)>0&&canManage?`<button type="button" class="danger" data-r182-pay-debt="${esc(item.plot_id)}">🧾 ПОГАСИТЬ ДОЛГ</button>`:''}<button type="button" class="secondary" data-r182-show="${esc(item.plot_id)}">⌖ ПОКАЗАТЬ</button></div></article>`;
  }
  function openObject(item){
    if(!item)return;selectedPlot=String(item.plot_id);document.querySelectorAll('.r182-object').forEach(node=>node.classList.toggle('selected',node.dataset.r182Object===selectedPlot));
    ensureSheet();document.getElementById('r182SheetTitle').textContent=item.title;document.getElementById('r182SheetKicker').textContent=`${statusLabel(item.status)} · карта государства`;document.getElementById('r182SheetBody').innerHTML=sheetContent(item);document.getElementById('r182Sheet').classList.add('open');document.getElementById('r182SheetBackdrop').classList.add('open');document.body.classList.add('r182-sheet-open');focusObject(item);tg?.HapticFeedback?.impactOccurred?.('light');
  }
  function closeSheet(){document.getElementById('r182Sheet')?.classList.remove('open');document.getElementById('r182SheetBackdrop')?.classList.remove('open');document.body.classList.remove('r182-sheet-open')}
  async function contribute(item){const max=Math.max(0,Number(item.remaining)||0),value=Number(prompt(`Сколько влияния вложить?\nОсталось: ${fmt(max)}`,String(Math.min(10000,max))));if(!Number.isFinite(value)||value<100)return;await post179('construction_contribute',{project_id:item.project_id,amount:Math.floor(value),request_id:requestId()});closeSheet()}
  async function fund(item){const max=Math.max(0,Number(item.remaining)||0),value=Number(prompt(`Сколько направить из фонда?\nОсталось: ${fmt(max)}`,String(max)));if(!Number.isFinite(value)||value<=0)return;await post179('construction_fund',{project_id:item.project_id,source_key:item.source_key,amount:Math.floor(value),request_id:requestId()});closeSheet()}
  async function payDebt(item){if(!confirm(`Погасить долг ${fmt(item.maintenance_debt)} влияния?`))return;await post179('construction_debt_pay',{building_id:item.building_id,source_key:item.source_key,request_id:requestId()});closeSheet()}

  document.addEventListener('click',event=>{
    if(event.target.closest?.('[data-tab="map182"]'))setTimeout(()=>{scheduleRender();load()},60);
    const district=event.target.closest?.('[data-r182-district]');if(district){const key=String(district.dataset.r182District);if(activeDistrict===key&&key!=='all')focusDistrict('all');else focusDistrict(key);return}
    const filter=event.target.closest?.('[data-r182-filter]');if(filter){activeFilter=String(filter.dataset.r182Filter);scheduleRender();return}
    if(event.target.closest?.('[data-r182-filter-toggle]')){filtersOpen=!filtersOpen;scheduleRender();return}
    if(event.target.closest?.('[data-r182-fill]')){activeDistrict='all';fitWorld('cover');scheduleRender();return}
    if(event.target.closest?.('[data-r182-fit]')){activeDistrict='all';fitWorld('contain');scheduleRender();return}
    if(event.target.closest?.('[data-r182-zoom-in]')){zoomBy(1.2);return}if(event.target.closest?.('[data-r182-zoom-out]')){zoomBy(1/1.2);return}
    if(event.target.closest?.('[data-r182-refresh]')){load();return}
    if(event.target.closest?.('[data-r182-fullscreen]')){toggleFullscreen(true);return}if(event.target.closest?.('[data-r182-close-fullscreen]')){toggleFullscreen(false);return}
    if(event.target.closest?.('[data-r182-mini]')){miniVisible=!miniVisible;scheduleRender();return}if(event.target.closest?.('[data-r182-mini-close]')){miniVisible=false;scheduleRender();return}
    const object=event.target.closest?.('[data-r182-object]');if(object){openObject(itemByPlot(object.dataset.r182Object));return}
    const list=event.target.closest?.('[data-r182-list-object]');if(list){openObject(itemByPlot(list.dataset.r182ListObject));return}
    const landmark=event.target.closest?.('[data-r182-landmark]');if(landmark){focusDistrict(String(landmark.dataset.district));return}
    if(event.target.closest?.('[data-r182-sheet-close]')){closeSheet();return}
    const show=event.target.closest?.('[data-r182-show]');if(show){const item=itemByPlot(show.dataset.r182Show);closeSheet();focusObject(item);return}
    const contributeButton=event.target.closest?.('[data-r182-contribute]');if(contributeButton){contribute(itemByPlot(contributeButton.dataset.r182Contribute));return}
    const fundButton=event.target.closest?.('[data-r182-fund]');if(fundButton){fund(itemByPlot(fundButton.dataset.r182Fund));return}
    const debtButton=event.target.closest?.('[data-r182-pay-debt]');if(debtButton){payDebt(itemByPlot(debtButton.dataset.r182PayDebt));return}
    if(event.target.closest?.('[data-r182-open-construction]')){closeSheet();if(fullscreen)toggleFullscreen(false);document.querySelector('[data-tab="construction179"]')?.click();return}
    const mini=event.target.closest?.('#r182Minimap');if(mini&&!event.target.closest('button')){const rect=mini.getBoundingClientRect(),size=worldSize(),x=(event.clientX-rect.left)/rect.width*size.width,y=(event.clientY-rect.top)/rect.height*size.height,view=viewport();camera.x=view.clientWidth/2-x*camera.scale;camera.y=view.clientHeight/2-y*camera.scale;fitMode='manual';scheduleTransform()}
  });

  document.addEventListener('keydown',event=>{if(event.key==='Escape'){if(document.getElementById('r182Sheet')?.classList.contains('open'))closeSheet();else if(fullscreen)toggleFullscreen(false)}});
  const onResize=()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{const next=chooseLayout();if(next!==layoutMode){layoutMode=next;activeDistrict='all';fitMode='cover'}scheduleRender()},140)};
  window.addEventListener('resize',onResize);window.visualViewport?.addEventListener('resize',onResize);
  window.addEventListener('pageshow',()=>load());document.addEventListener('visibilitychange',()=>{if(!document.hidden)load()});
  ensureLayout();load();
})();