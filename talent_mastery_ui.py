from __future__ import annotations

from typing import Any

import talent_ux


MASTERY_STYLE = r"""
<style id="talent-mastery-ui-v1">
.master-toolbar{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;padding:0 9px 8px;z-index:19}
.master-tool{min-height:39px;border:1px solid #ffffff14;border-radius:13px;background:linear-gradient(#241934,#110b1e);color:#cabfd6;font-size:8.5px;font-weight:950;letter-spacing:.2px;box-shadow:inset 0 1px #ffffff0b}
.master-tool:active{transform:scale(.97)}.master-tool b{display:block;font-size:15px;line-height:15px;margin-bottom:2px}
.master-overlay{position:fixed;inset:0;z-index:190;display:none;align-items:flex-end;background:#030207c7;backdrop-filter:blur(12px);padding:12px}.master-overlay.show{display:flex}
.master-panel{width:min(100%,620px);max-height:88vh;margin:0 auto;overflow:auto;border-radius:26px 26px 18px 18px;border:1px solid #ffffff20;background:radial-gradient(circle at 50% -8%,rgba(var(--rgb),.24),transparent 32%),linear-gradient(#261a3e,#0d0918);box-shadow:0 30px 90px #000c;padding:15px;color:#fff}
.master-head{display:flex;align-items:center;gap:9px;position:sticky;top:-15px;z-index:4;margin:-15px -15px 11px;padding:15px;background:linear-gradient(#25193ded,#1b122eea);backdrop-filter:blur(13px);border-bottom:1px solid #ffffff12}.master-head h2{flex:1;margin:0;font-size:18px}.master-close{width:38px;height:38px;border-radius:13px;border:1px solid #ffffff1c;background:#130d20;color:white;font-size:18px;font-weight:900}
.master-note{padding:10px 11px;border-radius:14px;background:#ffffff08;border:1px solid #ffffff10;color:#bfb3cb;font-size:10px;line-height:1.42;margin-bottom:10px}
.master-section{margin:15px 0 7px;font-size:10px;color:var(--c);font-weight:950;letter-spacing:.8px;text-transform:uppercase}.master-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.master-card{position:relative;min-height:150px;padding:11px;border-radius:17px;border:1px solid #ffffff14;background:linear-gradient(145deg,#211631,#100b1b);overflow:hidden}.master-card:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 90% 0,rgba(var(--rgb),.12),transparent 45%);pointer-events:none}.master-card h3{position:relative;margin:0 0 5px;font-size:12px}.master-card p{position:relative;margin:4px 0;color:#b7acbf;font-size:9px;line-height:1.35}.master-card .mini{position:relative;color:#e1d6e7;font-size:8.5px}.master-card button{position:relative;width:100%;min-height:34px;margin-top:8px;border:0;border-radius:11px;background:linear-gradient(135deg,var(--c),var(--c2));font-size:9px;font-weight:950}.master-card button:disabled{opacity:.36}.master-card.mystery{filter:saturate(.45)}.master-card.mystery h3{letter-spacing:1px}.master-card.mystery:after{content:"?";position:absolute;right:8px;top:-16px;font-size:76px;font-weight:950;color:#ffffff08}
.master-rarity{display:inline-block;margin-bottom:6px;padding:3px 6px;border-radius:99px;border:1px solid currentColor;font-size:7px;font-weight:950;letter-spacing:.55px;text-transform:uppercase}.rar-common{color:#c5bfca}.rar-rare{color:#66b6ff}.rar-epic{color:#bd72ff}.rar-legendary{color:#ffd36d}.rar-mythic{color:#ff6a9e}
.master-preview{margin-top:8px;padding:8px 9px;border-radius:12px;border:1px solid rgba(var(--rgb),.17);background:rgba(var(--rgb),.07);color:#d7ccdf;font-size:9px;line-height:1.4}.master-preview b{display:block;color:var(--c);font-size:8px;text-transform:uppercase;letter-spacing:.55px;margin-bottom:3px}
.master-actions{display:flex;gap:7px}.master-actions button{flex:1}.master-danger{background:linear-gradient(135deg,#7f2b49,#d94a70)!important}.master-secondary{background:#2b203b!important;border:1px solid #ffffff18!important}
.build-slot{padding:11px;border:1px solid #ffffff12;border-radius:15px;background:#130d20;margin:7px 0}.build-slot strong{font-size:11px}.build-slot small{display:block;color:#9f94aa;margin-top:3px}.build-slot .master-actions{margin-top:8px}.build-slot button{min-height:34px;border:0;border-radius:11px;color:white;font-size:9px;font-weight:900;background:linear-gradient(135deg,#8757e8,#d15bc7)}
.set-card{display:flex;gap:9px;align-items:flex-start;padding:10px;border-radius:14px;border:1px solid #ffffff12;background:#130d20;margin:7px 0;opacity:.55}.set-card.active{opacity:1;border-color:#ffd36d55;box-shadow:0 0 19px #ffd36d14}.set-card .set-emoji{font-size:24px}.set-card b{font-size:11px}.set-card p{margin:3px 0;color:#a99dad;font-size:9px}
.nodewrap.rarity-rare .node{border-color:#66b6ff99!important;box-shadow:0 15px 32px #0008,0 0 24px #66b6ff32!important}.nodewrap.rarity-epic .node{border-color:#bd72ffb0!important;box-shadow:0 15px 32px #0008,0 0 27px #bd72ff3c!important}.nodewrap.rarity-legendary .node{border-color:#ffd36dc7!important;box-shadow:0 15px 32px #0008,0 0 30px #ffd36d45!important}.nodewrap.rarity-mythic .node{border-color:#ff6a9ed6!important;box-shadow:0 15px 32px #0008,0 0 34px #ff6a9e52!important}.rarity-dot{position:absolute;left:-7px;bottom:-6px;z-index:4;padding:3px 5px;border-radius:99px;background:#0e0918;border:1px solid currentColor;font-size:6px;font-weight:950;letter-spacing:.35px}.hide-locked .nodewrap.locked{display:none!important}
#talentMinimap{position:absolute;left:9px;bottom:13px;z-index:11;width:96px;height:112px;border-radius:13px;border:1px solid #ffffff16;background:#0b0713c9;backdrop-filter:blur(7px);box-shadow:0 9px 28px #0007;pointer-events:none}.completion-chip{display:inline-block;margin-left:5px;padding:3px 6px;border-radius:99px;background:rgba(var(--rgb),.1);border:1px solid rgba(var(--rgb),.2);font-size:8px;color:var(--c)}
.card-master-preview{margin-top:9px;padding:10px;border-radius:14px;border:1px solid rgba(var(--rgb),.18);background:rgba(var(--rgb),.075);font-size:10px;line-height:1.42;color:#d9cee1}.card-master-preview b{display:block;color:var(--c);margin-bottom:4px;font-size:8px;text-transform:uppercase;letter-spacing:.6px}.card-rarity{margin-top:4px;font-size:8px;font-weight:950;text-transform:uppercase;letter-spacing:.55px}
@media(max-width:390px){.master-toolbar{gap:4px}.master-tool{font-size:7.7px}.master-grid{grid-template-columns:1fr 1fr}.master-panel{padding:13px}.master-head{margin:-13px -13px 10px;padding:13px}}
</style>
"""


MASTERY_SCRIPT = r"""
<script id="talent-mastery-ui-v1-script">
(()=>{
const wait=setInterval(()=>{if(typeof state!=='undefined'&&state?.points&&typeof tree==='function'){clearInterval(wait);bootMastery()}},120);
let masterMode='special',masterOverlay,masterBody,hideLocked=false;
const rarityClass=r=>'rar-'+(r||'common');
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmtTime=s=>{s=Math.max(0,Number(s)||0);if(!s)return'готово';const h=Math.floor(s/3600),m=Math.ceil((s%3600)/60);return h?`${h} ч ${m} мин`:`${m} мин`};

function bootMastery(){
 const viewport=document.getElementById('viewport');
 const toolbar=document.createElement('div');toolbar.className='master-toolbar';toolbar.innerHTML=`
  <button class="master-tool" data-mode="special"><b>✨</b>Особые</button>
  <button class="master-tool" data-mode="active"><b>⚡</b>Способности</button>
  <button class="master-tool" data-mode="builds"><b>🧩</b>Билды</button>
  <button class="master-tool" data-mode="community"><b>🏛</b>Беседа</button>`;
 viewport.parentNode.insertBefore(toolbar,viewport);
 toolbar.querySelectorAll('button').forEach(b=>b.onclick=()=>openMaster(b.dataset.mode));
 masterOverlay=document.createElement('div');masterOverlay.className='master-overlay';masterOverlay.innerHTML='<div class="master-panel"><div class="master-head"><h2 id="masterTitle">Мастерство</h2><button class="master-close">✕</button></div><div id="masterBody"></div></div>';
 document.body.appendChild(masterOverlay);masterBody=masterOverlay.querySelector('#masterBody');masterOverlay.querySelector('.master-close').onclick=closeMaster;masterOverlay.onclick=e=>{if(e.target===masterOverlay)closeMaster()};
 const mini=document.createElement('canvas');mini.id='talentMinimap';mini.width=192;mini.height=224;viewport.appendChild(mini);
 const oldTree=tree;tree=function(...args){const result=oldTree(...args);requestAnimationFrame(()=>{decorateTree();drawMinimap();updateCompletion()});return result};
 const oldOpen=openSkill;openSkill=function(skill){const result=oldOpen(skill);requestAnimationFrame(()=>decorateCard(skill));return result};
 tree();updateCompletion();setInterval(drawMinimap,700);
}

function openMaster(mode){masterMode=mode;masterOverlay.classList.add('show');renderMaster();tg?.HapticFeedback?.impactOccurred?.('light')}
function closeMaster(){masterOverlay?.classList.remove('show')}
function titleFor(mode){return({special:'✨ Особые таланты',active:'⚡ Активные способности',builds:'🧩 Билды и сброс',community:'🏛 Древо беседы'})[mode]||'Мастерство'}
function renderMaster(){document.getElementById('masterTitle').textContent=titleFor(masterMode);if(masterMode==='special')renderSpecial();if(masterMode==='active')renderActive();if(masterMode==='builds')renderBuilds();if(masterMode==='community')renderCommunity()}

function specialCard(item){
 const mystery=!item.visible,level=Number(item.level||0),max=Number(item.max||1),can=item.unlocked&&level<max&&Number(state.points.available)>=Number(item.cost);
 const preview=(item.preview?.lines||[]).map(esc).join('<br>');
 return `<article class="master-card ${mystery?'mystery':''}">
  <span class="master-rarity ${rarityClass(item.rarity)}">${esc(item.rarity_title)}</span>
  <h3>${mystery?'❔ ':''}${esc(item.name)}</h3>
  <p>${esc(mystery?(item.clue||'Условие открытия скрыто.'):item.effect||'Особый талант.')}</p>
  <div class="mini">Уровень ${level}/${max} · стоимость ${item.cost}</div>
  <div class="master-preview"><b>После улучшения</b>${preview}</div>
  <button data-upgrade="${esc(item.id)}" ${can?'':'disabled'}>${level>=max?'МАКСИМУМ':item.blocked_by?'ВЫБРАН ДРУГОЙ ПУТЬ':!item.unlocked?'ЗАБЛОКИРОВАНО':Number(state.points.available)<Number(item.cost)?'НЕ ХВАТАЕТ ОЧКОВ':'ПРОКАЧАТЬ'}</button>
 </article>`;
}
function renderSpecial(){
 const groups=[['hybrid','Связи между ветками'],['mechanic','Новые механики'],['hidden','Скрытые таланты']];
 let html='<div class="master-note">Особые узлы соединяют разные ветки, меняют правила игры и открываются за достижения. Финальные специализации каждой основной ветки взаимоисключающие.<button class="master-secondary" id="toggleLockedNodes" style="width:100%;min-height:34px;margin-top:8px;border-radius:11px;color:white">'+(hideLocked?'ПОКАЗАТЬ ЗАБЛОКИРОВАННЫЕ':'СКРЫТЬ ЗАБЛОКИРОВАННЫЕ')+'</button></div>';
 groups.forEach(([kind,title])=>{const items=(state.special_skills||[]).filter(x=>x.kind===kind);html+=`<div class="master-section">${title}</div><div class="master-grid">${items.map(specialCard).join('')}</div>`});
 html+='<div class="master-section">Комплекты талантов</div>'+renderSetsHtml();
 masterBody.innerHTML=html;masterBody.querySelectorAll('[data-upgrade]').forEach(b=>b.onclick=()=>upgradeSpecial(b.dataset.upgrade));const toggle=document.getElementById('toggleLockedNodes');if(toggle)toggle.onclick=()=>{hideLocked=!hideLocked;document.body.classList.toggle('hide-locked',hideLocked);renderSpecial()};
}
async function upgradeSpecial(id){try{state=await api('upgrade',{skill_id:id});tree(id);renderMaster();toastShow('Особый талант улучшен');tg?.HapticFeedback?.notificationOccurred?.('success')}catch(e){toastShow(e.message);tg?.HapticFeedback?.notificationOccurred?.('error')}}

function renderActive(){
 const cards=(state.active_abilities||[]).map(item=>{const level=Number(item.level||0),ready=Number(item.ready_in||0),active=item.active_effect;return `<article class="master-card">
  <span class="master-rarity ${rarityClass(item.rarity)}">${esc(item.rarity_title)}</span><h3>⚡ ${esc(item.real_name||item.name)}</h3>
  <p>${esc(item.effect)}</p><div class="mini">${active?`Эффект заряжен · ${fmtTime(active.expires_in)}`:ready?`Восстановление: ${fmtTime(ready)}`:level?'Готово к активации':'Сначала открой талант'}</div>
  <button data-activate="${esc(item.id)}" ${level&&ready===0&&!active?'':'disabled'}>${active?'ЗАРЯЖЕНО':ready?fmtTime(ready):level?'АКТИВИРОВАТЬ':'НЕ ОТКРЫТО'}</button></article>`}).join('');
 masterBody.innerHTML='<div class="master-note">Активные способности нужно включать вручную. Заряд сохраняется до срабатывания или до истечения суток.</div><div class="master-grid">'+cards+'</div>';
 masterBody.querySelectorAll('[data-activate]').forEach(b=>b.onclick=()=>activateTalent(b.dataset.activate));
}
async function activateTalent(id){try{const r=await api('activate',{ability_id:id});state=r.state;renderMaster();toastShow('Способность заряжена');tg?.HapticFeedback?.notificationOccurred?.('success')}catch(e){toastShow(e.message)}}

function renderBuilds(){
 const b=state.builds||{slots:[]};let html='<div class="master-note">Сохрани до трёх вариантов прокачки. Первое обнуление бесплатно, следующие стоят очки влияния. Между переключениями билдов действует часовой откат.</div>';
 (b.slots||[]).forEach(slot=>{html+=`<div class="build-slot"><strong>Слот ${slot.slot}: ${esc(slot.name)}</strong><small>${slot.empty?'Пока пусто':b.active_slot===slot.slot?'Активный билд':'Сохранённый билд'}</small><div class="master-actions"><button data-save="${slot.slot}">СОХРАНИТЬ</button><button class="master-secondary" data-load="${slot.slot}" ${slot.empty||b.switch_ready_in?'disabled':''}>${b.switch_ready_in?fmtTime(b.switch_ready_in):'ЗАГРУЗИТЬ'}</button></div></div>`});
 html+=`<div class="master-section">Текущая специализация</div>${renderBuildSummary()}<div class="master-actions"><button class="master-danger" id="resetTalentBuild">СБРОСИТЬ ДРЕВО · ${b.free_reset?'БЕСПЛАТНО':b.reset_price+' ВЛИЯНИЯ'}</button></div>`;
 masterBody.innerHTML=html;masterBody.querySelectorAll('[data-save]').forEach(x=>x.onclick=()=>saveBuild(Number(x.dataset.save)));masterBody.querySelectorAll('[data-load]').forEach(x=>x.onclick=()=>loadBuild(Number(x.dataset.load)));document.getElementById('resetTalentBuild').onclick=resetBuild;
}
function renderBuildSummary(){const specs=state.specializations||{},names={damage:'Урон',influence:'Влияние',defense:'Защита',rewards:'Награды'};return '<div class="master-card">'+Object.entries(names).map(([k,n])=>`<p><b>${n}:</b> ${esc(specs[k]||'специализация не выбрана')}</p>`).join('')+`<p><b>Свободно очков:</b> ${state.points.available}</p></div>`}
async function saveBuild(slot){const name=prompt('Название билда',`Билд ${slot}`)||`Билд ${slot}`;try{const r=await api('save-build',{slot,name});state.builds=r.builds;renderMaster();toastShow('Билд сохранён')}catch(e){toastShow(e.message)}}
async function loadBuild(slot){try{state=await api('load-build',{slot});tree();centerTree();renderMaster();toastShow('Билд загружен')}catch(e){toastShow(e.message)}}
async function resetBuild(){if(!confirm('Сбросить все вложенные очки талантов?'))return;try{state=await api('reset',{});tree();centerTree();renderMaster();toastShow('Очки талантов возвращены')}catch(e){toastShow(e.message)}}

function renderCommunity(){const c=state.community||{points:{available:0},skills:[]};masterBody.innerHTML=`<div class="master-note">Общие очки появляются за личную прокачку участников и победы над Центром Вселенной. Улучшения работают для всей беседы.</div><div class="master-section">Свободно общих очков: ${c.points.available}</div><div class="master-grid">${(c.skills||[]).map(item=>`<article class="master-card"><h3>${esc(item.emoji)} ${esc(item.title)}</h3><p>${esc(item.effect)}</p><div class="mini">Уровень ${item.level}/${item.max}</div><button data-community="${esc(item.id)}" ${item.level>=item.max||c.points.available<item.cost?'disabled':''}>${item.level>=item.max?'МАКСИМУМ':'УЛУЧШИТЬ'}</button></article>`).join('')}</div>`;masterBody.querySelectorAll('[data-community]').forEach(b=>b.onclick=()=>communityUpgrade(b.dataset.community))}
async function communityUpgrade(id){try{const r=await api('community-upgrade',{skill_id:id});state.community=r.community;renderMaster();toastShow('Общее древо улучшено')}catch(e){toastShow(e.message)}}

function renderSetsHtml(){return(state.sets||[]).map(s=>`<div class="set-card ${s.active?'active':''}"><div class="set-emoji">${esc(s.emoji)}</div><div><b>${esc(s.title)} ${s.active?'· АКТИВЕН':''}</b><p>${esc(s.description)}</p><p>${(s.skills||[]).map(id=>esc(state.skill_meta?.[id]?.real_name||id)).join(' · ')}</p></div></div>`).join('')}

function decorateTree(){
 const byName={};Object.values(state.skill_meta||{}).forEach(m=>byName[m.real_name]=m);
 document.body.classList.toggle('hide-locked',hideLocked);
 document.querySelectorAll('.nodewrap').forEach(w=>{const name=w.querySelector('.name')?.textContent?.trim(),m=byName[name];if(!m)return;w.classList.remove('rarity-common','rarity-rare','rarity-epic','rarity-legendary','rarity-mythic');w.classList.add('rarity-'+m.rarity);if(m.blocked_by&&Number(m.level||0)===0){w.classList.add('locked');w.classList.remove('available')}const node=w.querySelector('.node');let dot=node?.querySelector('.rarity-dot');if(!dot&&node){dot=document.createElement('span');dot.className='rarity-dot';node.appendChild(dot)}if(dot){dot.className='rarity-dot '+rarityClass(m.rarity);dot.textContent=(m.rarity_title||'').slice(0,3).toUpperCase()}});
}
function decorateCard(skill){const m=state.skill_meta?.[skill.id];if(!m)return;const card=document.querySelector('#sheet .card'),effect=document.getElementById('cardeffect');if(!card||!effect)return;let rarity=card.querySelector('.card-rarity');if(!rarity){rarity=document.createElement('div');rarity.className='card-rarity';document.getElementById('cardtitle')?.insertAdjacentElement('afterend',rarity)}rarity.className='card-rarity '+rarityClass(m.rarity);rarity.textContent=m.rarity_title+(m.blocked_by?' · путь заблокирован':'');const upgradeButton=document.getElementById('upgrade');if(upgradeButton&&m.blocked_by&&Number(m.level||0)===0){upgradeButton.disabled=true;upgradeButton.textContent='ВЫБРАН ДРУГОЙ ПУТЬ'}let box=card.querySelector('.card-master-preview');if(!box){box=document.createElement('div');box.className='card-master-preview';effect.insertAdjacentElement('afterend',box)}box.innerHTML='<b>Точный результат следующего очка</b>'+((m.preview?.lines||[]).map(esc).join('<br>'))}
function updateCompletion(){const c=state.branch_completion?.[branch],spec=state.specializations?.[branch];if(c){branchBonus.innerHTML=`${c.learned}/${c.total}<span class="completion-chip">${Math.round(c.learned/c.total*100)||0}%</span>`}const base=branchDesc.textContent.replace(/\s*Специализация:.*$/,'').trim();branchDesc.textContent=spec?`${base} Специализация: ${spec}.`:base;decorateTree()}
function drawMinimap(){const cv=document.getElementById('talentMinimap');if(!cv)return;const ctx=cv.getContext('2d'),sx=cv.width/1000,sy=cv.height/1180;ctx.clearRect(0,0,cv.width,cv.height);ctx.fillStyle='rgba(255,255,255,.05)';ctx.fillRect(0,0,cv.width,cv.height);document.querySelectorAll('.nodewrap').forEach(w=>{if(w.offsetParent===null)return;const x=parseFloat(w.style.left)||0,y=parseFloat(w.style.top)||0;ctx.fillStyle=w.classList.contains('maxed')?'#ffd36d':w.classList.contains('learned')?'#c276ff':w.classList.contains('locked')?'#554b60':'#f0e6ff';ctx.beginPath();ctx.arc(x*sx,y*sy,4,0,7);ctx.fill()});const vw=viewport.clientWidth/scale,vh=viewport.clientHeight/scale,x=-tx/scale,y=-ty/scale;ctx.strokeStyle='rgba(255,255,255,.55)';ctx.lineWidth=2;ctx.strokeRect(x*sx,y*sy,vw*sx,vh*sy)}
})();
</script>
"""


def install_mastery_ui(core: Any) -> None:
    if getattr(core, "_talent_mastery_ui_installed", False):
        return
    core._talent_mastery_ui_installed = True
    talent_ux.STYLE += MASTERY_STYLE
    talent_ux.SCRIPT += MASTERY_SCRIPT
