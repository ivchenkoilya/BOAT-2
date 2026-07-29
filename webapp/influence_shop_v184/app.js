(() => {
  'use strict';
  const tg = window.Telegram?.WebApp;
  tg?.ready(); tg?.expand();
  tg?.setHeaderColor?.('#09070d'); tg?.setBackgroundColor?.('#09070d');
  const $ = id => document.getElementById(id);
  const fmt = value => new Intl.NumberFormat('ru-RU').format(Number(value) || 0);
  const params = new URLSearchParams(location.search);
  const initData = tg?.initData || '';
  const startParam = String(tg?.initDataUnsafe?.start_param || params.get('tgWebAppStartParam') || params.get('startapp') || '');
  const headers = {'Content-Type':'application/json','X-Telegram-Init-Data':initData};
  const rarityNames = {common:'ОБЫЧНЫЙ',rare:'РЕДКИЙ',epic:'ЭПИЧЕСКИЙ',legendary:'ЛЕГЕНДАРНЫЙ',secret:'СЕКРЕТНЫЙ'};
  const reasonNames = {
    shop_custom_title:'Покупка титула',shop_roast_member:'Заказ прожарки',shop_extended_stats:'Расширенная статистика',
    shop_profile_frame:'Рамка профиля',shop_sabotage_shield:'Защита от саботажа',shop_mission_boost:'Усиление задания',
    shop_chat_event:'Запуск события',shop_hide_losses:'Скрытие поражений',shop_reroll_today_type:'Переброс типажа',
    shop_story_insurance:'Сюжетная страховка',intervention_cost:'Вмешательство',inactive_return:'Возвращение персонажа',
    inactive_return_caller:'Призыв персонажа',achievement_reward:'Награда достижения'
  };
  let state=null, category='all', selectedItem=null, periodDays=7, historyMode='all', busy=false, toastTimer=null;

  function esc(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function requestId(){return crypto?.randomUUID?.() || `v184-${Date.now()}-${Math.random().toString(36).slice(2)}`;}
  function initials(name){return String(name||'Г').trim().split(/\s+/).slice(0,2).map(x=>Array.from(x)[0]||'').join('').toUpperCase()||'Г';}
  function notify(text,type='info'){$('toast').textContent=text;$('toast').className=`toast show ${type}`;clearTimeout(toastTimer);toastTimer=setTimeout(()=>{$('toast').className='toast';},2800);}
  async function api(path,options={}){
    const controller=new AbortController(), timeout=setTimeout(()=>controller.abort(),12000);
    try{
      const response=await fetch(`/influence-shop-v184/api/${path}`,{...options,signal:controller.signal,headers:{...headers,...(options.headers||{})}});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      return data;
    }catch(error){if(error.name==='AbortError')throw new Error('Сервер долго не отвечает. Попробуйте ещё раз.');throw error;}finally{clearTimeout(timeout);}
  }
  function animateNumber(element,from,to){const start=performance.now(),diff=Number(to)-Number(from);function frame(now){const k=Math.min(1,(now-start)/650),e=1-Math.pow(1-k,3);element.textContent=fmt(Math.round(Number(from)+diff*e));if(k<1)requestAnimationFrame(frame);}requestAnimationFrame(frame);}

  function renderProfile(previous=null){
    const p=state.profile||{};$('profileName').textContent=p.name||'Главный герой';$('avatar').textContent=initials(p.name);
    $('roleEmoji').textContent=p.role_emoji||'🎭';$('roleName').textContent=p.role||'Участник';$('profileTitle').textContent=p.title?`· ${p.title}`:'';
    $('rank').textContent=`Место ${p.rank||0} из ${p.participants_total||0}`;$('aura').textContent=fmt(p.aura||0);
    $('auraFill').style.width=`${Math.min(100,Math.max(0,Number(p.aura||0)/10))}%`;$('avatarWrap').dataset.frame=p.frame||'';
    previous===null?$('balance').textContent=fmt(p.balance||0):animateNumber($('balance'),previous,p.balance||0);
  }
  function productCard(item,index){
    const affordable=Number(state.profile.balance)>=Number(item.price),seconds=Number(item.duration_seconds||0);
    const duration=seconds>=86400?`${Math.round(seconds/86400)} дн.`:seconds?`${Math.round(seconds/3600)} ч.`:'Навсегда / разово';
    return `<button class="product-card glass rarity-${esc(item.rarity)} ${affordable?'':'locked'}" data-item="${esc(item.item_key)}" style="--delay:${index*45}ms"><span class="product-shine"></span><div class="product-top"><i>${esc(item.icon)}</i><em>${esc(rarityNames[item.rarity]||item.rarity)}</em></div><h3>${esc(item.title)}</h3><p>${esc(item.description)}</p><div class="product-meta"><small>${duration}</small><strong>${fmt(item.price)} <b>✦</b></strong></div></button>`;
  }
  function renderShop(){const items=(state.shop||[]).filter(x=>category==='all'||x.category===category);$('productGrid').innerHTML=items.length?items.map(productCard).join(''):'<div class="empty-state glass">В этой категории пока нет товаров.</div>';document.querySelectorAll('[data-item]').forEach(b=>b.onclick=()=>openPurchase(b.dataset.item));}
  function payloadFields(item){
    if(item.item_key==='custom_title')return '<label class="payload-label">Новый титул<input id="customTitleInput" maxlength="32" placeholder="Например: Орлиный режиссёр"></label>';
    if(item.item_key==='roast_member')return `<label class="payload-label">Кого прожарить<select id="roastTarget"><option value="">Выберите участника</option>${(state.participants||[]).map(p=>`<option value="${Number(p.user_id)}">${esc(p.full_name||p.name)}</option>`).join('')}</select></label>`;
    if(item.item_key==='profile_frame')return `<label class="payload-label">Рамка<select id="frameSelect">${(state.frames||[]).map(f=>`<option value="${esc(f.key)}">${esc(f.icon)} ${esc(f.title)}</option>`).join('')}</select></label>`;
    if(item.item_key==='chat_event')return '<label class="payload-label">Событие<select id="eventSelect"><option value="chaos_hour">Час хаоса</option><option value="double_story">Двойной сюжет</option><option value="ego_storm">Буря эго</option></select></label>';
    return '';
  }
  function openPurchase(key){selectedItem=(state.shop||[]).find(x=>x.item_key===key);if(!selectedItem)return;$('modalIcon').textContent=selectedItem.icon;$('modalRarity').textContent=`${rarityNames[selectedItem.rarity]||selectedItem.rarity} ТОВАР`;$('modalTitle').textContent=selectedItem.title;$('modalDescription').textContent=selectedItem.description;$('modalBalance').textContent=fmt(state.profile.balance);$('modalPrice').textContent=fmt(selectedItem.price);$('modalAfter').textContent=fmt(Math.max(0,state.profile.balance-selectedItem.price));$('confirmPrice').textContent=`${fmt(selectedItem.price)} ✦`;$('payloadFields').innerHTML=payloadFields(selectedItem);$('confirmPurchase').disabled=state.profile.balance<selectedItem.price;$('purchaseModal').classList.add('open');$('purchaseModal').setAttribute('aria-hidden','false');tg?.HapticFeedback?.impactOccurred?.('light');}
  function closePurchase(){$('purchaseModal').classList.remove('open');$('purchaseModal').setAttribute('aria-hidden','true');selectedItem=null;}
  function collectPayload(item){if(item.item_key==='custom_title')return{title:String($('customTitleInput')?.value||'').trim()};if(item.item_key==='roast_member')return{target_id:Number($('roastTarget')?.value||0)};if(item.item_key==='profile_frame')return{frame:String($('frameSelect')?.value||'gold')};if(item.item_key==='chat_event')return{event_key:String($('eventSelect')?.value||'chaos_hour')};return{};}
  async function confirmPurchase(){
    if(!selectedItem||busy)return;const payload=collectPayload(selectedItem);
    if(selectedItem.item_key==='custom_title'&&!payload.title)return notify('Введите новый титул.','error');
    if(selectedItem.item_key==='roast_member'&&!payload.target_id)return notify('Выберите участника.','error');
    busy=true;const button=$('confirmPurchase'),old=Number(state.profile.balance||0);button.disabled=true;button.classList.add('working');tg?.HapticFeedback?.impactOccurred?.('medium');
    try{const result=await api('buy',{method:'POST',body:JSON.stringify({chat_id:state.chat_id,item_key:selectedItem.item_key,request_id:requestId(),payload})});state.profile.balance=Number(result.balance);renderProfile(old);closePurchase();showSuccess(result.message||'Покупка совершена.');tg?.HapticFeedback?.notificationOccurred?.('success');await refreshState(true);}catch(error){button.classList.add('shake');setTimeout(()=>button.classList.remove('shake'),500);notify(error.message,'error');tg?.HapticFeedback?.notificationOccurred?.('error');}finally{busy=false;button.classList.remove('working');button.disabled=false;}
  }
  function showSuccess(text){$('successText').textContent=text;$('successParticles').innerHTML=Array.from({length:18},(_,i)=>`<i style="--i:${i}"></i>`).join('');$('purchaseSuccess').classList.add('show');setTimeout(()=>$('purchaseSuccess').classList.remove('show'),2100);}

  function renderChart(){
    const data=(state.daily||[]).slice(-periodDays),svg=$('influenceChart');if(!data.length){svg.innerHTML='<text x="180" y="78" text-anchor="middle">История пока пуста</text>';$('chartDelta').textContent='0';return;}
    let balance=Number(state.profile.balance||0),back=[balance];[...data].reverse().forEach(r=>{balance-=Number(r.earned||0)-Number(r.lost||0);back.push(balance);});const values=back.reverse().slice(1),min=Math.min(...values),max=Math.max(...values),range=Math.max(1,max-min);
    const points=values.map((v,i)=>[values.length===1?180:10+i*340/(values.length-1),135-(v-min)/range*115]),poly=points.map(([x,y])=>`${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
    svg.innerHTML=`<defs><linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="rgba(215,174,86,.5)"/><stop offset="1" stop-color="rgba(215,174,86,0)"/></linearGradient></defs><polygon points="10,140 ${poly} 350,140" fill="url(#areaGradient)"/><polyline points="${poly}" fill="none" stroke="currentColor" stroke-width="4" vector-effect="non-scaling-stroke"/>${points.map(([x,y])=>`<circle cx="${x}" cy="${y}" r="3.5"/>`).join('')}`;
    const delta=values.at(-1)-values[0];$('chartDelta').textContent=`${delta>=0?'+':'−'}${fmt(Math.abs(delta))}`;$('chartDelta').className=delta>=0?'positive':'negative';
  }
  function renderMetrics(){const s=state.stats||{},wins=Number(s.wins||0),losses=Number(s.losses||0),rate=wins+losses?Math.round(wins/(wins+losses)*100):0;const rows=[['Текущее влияние',fmt(s.current_balance),'✦'],['Место в рейтинге',`${s.rank||0}/${s.participants_total||0}`,'🏆'],['Заработано за неделю',`+${fmt(s.earned_week)}`,'↗'],['Потеряно за неделю',`−${fmt(s.lost_week)}`,'↘'],['Потрачено в магазине',fmt(s.shop_spent),'🛍'],['Победы',fmt(wins),'⚔'],['Поражения',fmt(losses),'☠'],['Процент побед',`${rate}%`,'🎯'],['Серия побед',fmt(s.win_streak||0),'🔥'],['Вмешательства',fmt(s.interventions||0),'🎭'],['Сообщения',fmt(s.message_count||0),'💬'],['Максимальный баланс',fmt(s.max_balance||s.current_balance),'👑']];$('metricGrid').innerHTML=rows.map(([l,v,i])=>`<article class="metric-card glass"><i>${i}</i><span>${esc(l)}</span><strong>${esc(v)}</strong></article>`).join('');}
  function matchTransaction(x){return historyMode==='all'||historyMode==='income'&&x.amount>0||historyMode==='expense'&&x.amount<0||historyMode==='shop'&&String(x.reason).startsWith('shop_')||historyMode==='events'&&x.operation_type==='event';}
  function renderHistory(){const items=(state.transactions||[]).filter(matchTransaction).slice(0,30);$('historyList').innerHTML=items.length?items.map(x=>{const plus=Number(x.amount)>=0,date=new Date(Number(x.created_at)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});return `<div class="history-row"><i class="${plus?'plus':'minus'}">${plus?'↗':'↘'}</i><div><strong>${esc(reasonNames[x.reason]||String(x.reason).replaceAll('_',' '))}</strong><small>${esc(date)}</small></div><b class="${plus?'positive':'negative'}">${plus?'+':'−'}${fmt(Math.abs(x.amount))}</b></div>`;}).join(''):'<div class="empty-state">Операций по этому фильтру пока нет.</div>';}
  function renderStats(){renderChart();renderMetrics();renderHistory();}
  function renderStory(){const search=String($('storySearch').value||'').trim().toLowerCase(),importance=Number($('storyImportance').value||0),items=(state.story||[]).filter(x=>(!search||`${x.title} ${x.description}`.toLowerCase().includes(search))&&(!importance||Number(x.importance)>=importance));$('storyTimeline').innerHTML=items.length?items.map((x,i)=>{const date=new Date(Number(x.created_at)*1000).toLocaleString('ru-RU',{day:'numeric',month:'long',hour:'2-digit',minute:'2-digit'}),rarity=x.importance>=4?'epic':x.importance>=3?'rare':'common';return `<article class="story-entry ${rarity}" style="--delay:${i*35}ms"><span class="timeline-dot"></span><div class="glass"><small>${esc(date)} · важность ${Number(x.importance)}</small><h3>${esc(x.title)}</h3><p>${esc(x.description)}</p></div></article>`;}).join(''):'<div class="empty-state glass">Подходящих сюжетных событий пока нет.</div>';}
  function relationType(x){const s=String(x.status||'').toLowerCase();return s.includes('сопер')?'rival':s.includes('хаот')||s.includes('подозр')?'chaos':'ally';}
  function renderRelations(){const rows=state.relationships||[],map=$('relationMap');map.querySelectorAll('.relation-node,.relation-line').forEach(n=>n.remove());rows.slice(0,8).forEach((x,i)=>{const angle=Math.PI*2*i/Math.max(1,Math.min(8,rows.length))-Math.PI/2,radius=i%2?37:42,type=relationType(x),px=50+Math.cos(angle)*radius,py=50+Math.sin(angle)*radius,line=document.createElement('i'),node=document.createElement('button');line.className=`relation-line ${type}`;line.style.setProperty('--angle',`${angle}rad`);line.style.setProperty('--length',`${radius}%`);map.appendChild(line);node.className=`relation-node ${type}`;node.style.left=`${px}%`;node.style.top=`${py}%`;node.innerHTML=`<b>${esc(initials(x.other_name))}</b><span>${esc(x.other_name)}</span>`;node.onclick=()=>notify(`${x.other_name}: ${x.status}`);map.appendChild(node);});$('relationList').innerHTML=rows.length?rows.map(x=>`<article class="relation-card glass ${relationType(x)}"><div class="relation-avatar">${esc(initials(x.other_name))}</div><div><h3>${esc(x.other_name)}</h3><p>${esc(x.status||'Знакомые')}</p><small>Близость ${fmt(x.closeness)} · Доверие ${fmt(x.trust)} · Соперничество ${fmt(x.rivalry)} · Хаос ${fmt(x.chaos)}</small></div></article>`).join(''):'<div class="empty-state glass">Связи появятся после ответов, реакций, дуэлей и совместных событий.</div>';}
  function renderAchievements(){const rows=state.achievements||[],unlocked=rows.filter(x=>x.unlocked).length;$('achievementCounter').textContent=`${unlocked}/${rows.length}`;$('achievementGrid').innerHTML=rows.map((x,i)=>{const progress=Math.min(100,Number(x.progress||0)/Math.max(1,Number(x.target||1))*100),date=x.awarded_at?new Date(Number(x.awarded_at)*1000).toLocaleDateString('ru-RU'):'';return `<article class="achievement-card glass rarity-${esc(x.rarity)} ${x.unlocked?'unlocked':'locked'}" style="--delay:${i*25}ms"><div class="achievement-icon">${esc(x.icon)}</div><span>${esc(rarityNames[x.rarity]||x.rarity)}</span><h3>${esc(x.title)}</h3><p>${esc(x.description)}</p><div class="progress"><i style="width:${progress}%"></i></div><small>${x.unlocked?`Открыто ${esc(date)} · +${fmt(x.reward)}`:`${fmt(x.progress||0)}/${fmt(x.target||1)}`}</small></article>`;}).join('');}
  function renderAll(previous=null){renderProfile(previous);renderShop();renderStats();renderStory();renderRelations();renderAchievements();}
  async function refreshState(silent=false){const previous=state?.profile?.balance??null,queryChat=params.get('chat_id')||'';state=await api(`state?start_param=${encodeURIComponent(startParam)}&chat_id=${encodeURIComponent(queryChat)}`);renderAll(silent?previous:null);}
  function switchPage(name){document.querySelectorAll('.page').forEach(p=>p.classList.toggle('active',p.dataset.page===name));document.querySelectorAll('[data-page-target]').forEach(b=>b.classList.toggle('active',b.dataset.pageTarget===name));scrollTo({top:0,behavior:'smooth'});tg?.HapticFeedback?.selectionChanged?.();}
  function bind(){
    $('closeButton').onclick=()=>tg?.close?.();$('modalClose').onclick=closePurchase;$('purchaseModal').onclick=e=>{if(e.target===$('purchaseModal'))closePurchase();};$('confirmPurchase').onclick=confirmPurchase;
    $('categoryTabs').onclick=e=>{const b=e.target.closest('[data-category]');if(!b)return;category=b.dataset.category;document.querySelectorAll('[data-category]').forEach(x=>x.classList.toggle('active',x===b));renderShop();tg?.HapticFeedback?.selectionChanged?.();};
    $('bottomNav').onclick=e=>{const b=e.target.closest('[data-page-target]');if(b)switchPage(b.dataset.pageTarget);};$('periodTabs').onclick=e=>{const b=e.target.closest('[data-days]');if(!b)return;periodDays=Number(b.dataset.days);document.querySelectorAll('[data-days]').forEach(x=>x.classList.toggle('active',x===b));renderChart();};
    $('historyFilter').onclick=()=>{const modes=['all','income','expense','shop','events'],labels=['Все операции','Начисления','Списания','Магазин','События'],i=(modes.indexOf(historyMode)+1)%modes.length;historyMode=modes[i];$('historyFilter').textContent=labels[i];renderHistory();};$('storySearch').oninput=renderStory;$('storyImportance').onchange=renderStory;document.addEventListener('keydown',e=>{if(e.key==='Escape')closePurchase();});
  }
  async function start(){bind();try{await refreshState();document.body.classList.add('ready');setTimeout(()=>$('loadingScreen').classList.add('hidden'),250);}catch(error){$('loadingScreen').innerHTML=`<div class="loader-emblem">⚠️</div><p>${esc(error.message)}</p><button id="retryLoad">ПОВТОРИТЬ</button>`;$('retryLoad')?.addEventListener('click',()=>location.reload());}}
  start();
})();
