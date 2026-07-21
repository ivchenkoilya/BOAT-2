(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  let state=null,busy=false,timer=null;

  function ensureRoot(){
    let root=document.getElementById('crisisV131');
    if(root)return root;
    const hero=document.getElementById('powerHero');
    if(!hero)return null;
    root=document.createElement('section');root.id='crisisV131';root.className='crisis-v131';
    root.innerHTML=`
      <div class="section-head crisis-heading"><div><small>ТЕНЕВАЯ ПОЛИТИКА · REALITY 131</small><h2>Казна и борьба за власть</h2></div><span class="crisis-live">● LIVE</span></div>
      <div id="crisisCouncil"></div>
      <div class="crisis-grid"><div id="crisisTheft"></div><div id="crisisConflict"></div></div>
      <div class="section-head"><div><small>ПОДОЗРИТЕЛЬНЫЕ ОПЕРАЦИИ</small><h2>Расследования казны</h2></div></div>
      <div id="crisisTheftLog"></div>`;
    hero.insertAdjacentElement('afterend',root);return root;
  }

  function toast(text,type='success'){
    const node=document.getElementById('toast');if(!node)return;
    node.textContent=text;node.className=`toast show ${type}`;
    clearTimeout(node._crisisTimer);node._crisisTimer=setTimeout(()=>node.className='toast',3600);
  }

  async function load(silent=false){
    if(busy)return;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}`,{cache:'no-store',headers:{'X-Telegram-Init-Data':tg?.initData||''}});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось загрузить политический кризис.');
      state=data;render();
    }catch(error){if(!silent)toast(error.message||'Не удалось загрузить Reality 131.','error')}
  }

  async function action(name,payload={},confirmation=''){
    if(busy)return;
    if(confirmation&&!confirm(confirmation))return;
    busy=true;
    try{
      const response=await fetch('/government-v131/api/action',{method:'POST',cache:'no-store',headers,body:JSON.stringify({action:name,chat_id:chatId,...payload})});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      toast(data.message||'Готово.');tg?.HapticFeedback?.notificationOccurred?.('success');await load(true);
      setTimeout(()=>document.getElementById('refreshButton')?.click(),100);
    }catch(error){toast(error.message||'Действие не выполнено.','error');tg?.HapticFeedback?.notificationOccurred?.('error')}
    finally{busy=false}
  }

  const c=()=>state?.crisis_v131||{};
  const rules=()=>c().theft?.rules||[];
  const targetOptions=()=> (c().targets||[]).map(item=>`<option value="${esc(item.office_key)}|${item.seat_no}">${esc(item.title)} · ${esc(item.name)}</option>`).join('');
  const coupOptions=()=> (c().eligible_coup_users||[]).map(item=>`<option value="${item.user_id}">${esc(item.name)}${item.sabotage_hero?' · 💣 саботажный герой':''}${item.offices?.length?` · ${esc(item.offices.join(', '))}`:''}</option>`).join('');

  function renderTheft(){
    const theft=c().theft||{};const node=document.getElementById('crisisTheft');if(!node)return;
    const sabotage=c().sabotage_hero?'<span class="crisis-bonus">💣 Бонус саботажного героя: +15% к успеху и маскировке</span>':'';
    const buttons=rules().map(rule=>`<button type="button" class="theft-risk risk-${rule.percent}" data-steal="${rule.percent}" ${theft.can_attempt?'':'disabled'}><b>${rule.percent}% казны</b><small>Успех ${rule.success}% · риск ${rule.detection}%</small></button>`).join('');
    node.innerHTML=`<article class="panel crisis-panel shadow-panel"><div class="panel-title"><span>🕶</span><div><b>Теневая операция</b><small>Раз в 5 часов · расследование длится 2 часа</small></div></div>${sabotage}<div class="theft-risks">${buttons}</div><p class="hint">${theft.can_attempt?'Выбери долю казны. Чем больше сумма, тем выше шанс немедленного провала и обнаружения.':`Следующая попытка: ${esc(theft.remaining||'недоступна')}`}</p></article>`;
  }

  function theftStatus(item){return ({pending:'ИДЁТ РАССЛЕДОВАНИЕ',escaped:'ВОР СКРЫЛСЯ',caught:'ВИНОВНИК ПОЙМАН'})[item.status]||item.status}
  function renderTheftLog(){
    const node=document.getElementById('crisisTheftLog');if(!node)return;
    const items=c().theft?.items||[];
    node.innerHTML=items.length?`<div class="crisis-list">${items.map(item=>`<article class="crisis-row ${esc(item.status)}"><span class="crisis-icon">${item.status==='pending'?'❓':item.status==='caught'?'🚨':'🕶'}</span><span class="crisis-main"><b>${esc(theftStatus(item))}</b><small>${fmt(item.amount)} влияния · ${item.percent}% казны${item.status==='pending'?` · осталось ${esc(item.remaining)}`:''}</small><small>${item.thief_id?`Участник: ${esc(item.thief_name)}`:'Виновник не установлен'} · проверок ${fmt(item.investigations)}</small></span>${item.can_investigate?`<button type="button" class="investigate" data-investigate="${esc(item.theft_id)}">🔍 Проверить</button>`:item.investigated?'<span class="checked">✓ Проверено</span>':''}</article>`).join('')}</div>`:'<div class="empty">Подозрительных операций пока нет.</div>';
  }

  function memberCounts(conflict){
    const counts={militia:0,loyalist:0,neutral:0};for(const item of conflict.members||[])counts[item.side]=(counts[item.side]||0)+1;return counts;
  }

  function renderNoConflict(){
    const targets=targetOptions();const invitees=coupOptions();
    return `<article class="panel crisis-panel"><div class="panel-title"><span>🔥</span><div><b>Народное ополчение</b><small>Публичное выступление против президента или чиновника</small></div></div>${c().can_create_militia?`<details><summary>Создать ополчение</summary><form id="militiaCreate"><div class="field"><label>ЦЕЛЬ</label><select name="target">${targets||'<option value="">Нет действующих чиновников</option>'}</select></div><div class="field"><label>ПРИЧИНА</label><textarea name="reason" maxlength="600" placeholder="Почему власть должна быть отстранена"></textarea></div><button class="danger wide" type="submit">🔥 СОЗДАТЬ ОПОЛЧЕНИЕ</button></form></details>`:`<p class="hint">Создание конфликта недоступно${c().conflict_ban_remaining?`: ещё ${esc(c().conflict_ban_remaining)}`:''}.</p>`}</article>
    <article class="panel crisis-panel coup-panel"><div class="panel-title"><span>🗡</span><div><b>Дворцовый переворот</b><small>Тайный заговор чиновников и саботажного героя</small></div></div>${c().can_create_coup?`<details><summary>Создать тайный заговор</summary><form id="coupCreate"><div class="field"><label>ПЕРВЫЙ СООБЩНИК</label><select name="target_user_id">${invitees||'<option value="0">Подходящих участников нет</option>'}</select></div><div class="field"><label>ПЛАН</label><textarea name="reason" maxlength="600" placeholder="Зачем и как будет сменена власть"></textarea></div><button class="action wide" type="submit">🗡 НАЧАТЬ ЗАГОВОР</button></form></details>`:'<p class="hint">Нужна государственная должность или активный статус саботажного героя.</p>'}</article>`;
  }

  function renderMilitia(conflict){
    const counts=memberCounts(conflict);const gathering=conflict.stage==='gathering';const side=conflict.my_side;
    const sideButtons=gathering?`<div class="side-grid"><button data-join-side="militia">🔥 Ополчение</button><button data-join-side="loyalist">🛡 За власть</button><button data-join-side="neutral">⚪ Нейтралитет</button></div>`:'';
    let actions='';
    if(conflict.stage==='battle'&&side==='militia')actions=`<div class="battle-actions"><button data-militia-action="agitate">📣 Агитировать</button><button data-militia-action="seize">🔥 Захватить учреждение</button><button data-militia-action="expose">🕵 Компромат</button><button data-militia-action="fund">💰 Финансировать</button></div>`;
    if(conflict.stage==='battle'&&side==='loyalist')actions=`<div class="battle-actions"><button data-militia-action="fortify">🛡 Укрепить власть</button><button data-militia-action="suppress">⚔️ Подавить</button><button data-militia-action="investigate">🔍 Найти лидеров</button><button data-militia-action="fund">💰 Финансировать</button></div>`;
    return `<article class="panel crisis-panel active-conflict"><div class="panel-title"><span>🔥</span><div><b>Ополчение против: ${esc(conflict.target_name)}</b><small>${esc(conflict.reason)} · осталось ${esc(conflict.remaining)}</small></div></div><div class="conflict-metrics"><div><small>ОПОЛЧЕНИЕ</small><b>${counts.militia} / ${conflict.threshold}</b><em>${fmt(conflict.militia_score)} очков</em></div><div><small>ЗАЩИТНИКИ</small><b>${counts.loyalist}</b><em>${fmt(conflict.loyalist_score)} очков</em></div></div>${side?`<p class="my-side">Твоя сторона: <b>${side==='militia'?'🔥 ополчение':side==='loyalist'?'🛡 защитники':'⚪ нейтралитет'}</b></p>`:''}${sideButtons}${actions}</article>`;
  }

  function coupMembers(conflict){return (conflict.members||[]).map(item=>`<div class="coup-member"><b>${esc(item.name)}</b><small>${esc(item.role_key||'участник')} · ${esc(item.status)} · ${fmt(item.points)} очков</small></div>`).join('')}
  function renderCoup(conflict){
    if(conflict.my_status==='invited')return `<article class="panel crisis-panel coup-panel"><div class="panel-title"><span>🗡</span><div><b>Тайное приглашение</b><small>Тебя зовут в заговор против президента</small></div></div><div class="button-grid"><button class="positive" data-coup-response="1">✓ ВСТУПИТЬ</button><button class="danger" data-coup-response="0">✕ ОТКЛОНИТЬ</button></div></article>`;
    if(conflict.is_conspirator){
      const invite=coupOptions();
      return `<article class="panel crisis-panel coup-panel active-conflict"><div class="panel-title"><span>🗡</span><div><b>Тайный заговор</b><small>Этап: ${esc(conflict.stage)} · осталось ${esc(conflict.remaining)}</small></div></div><div class="plot-meter"><span style="width:${Math.min(100,Number(conflict.plot_score)||0)}%"></span></div><p class="hint">Подготовка: <b>${fmt(conflict.plot_score)}</b>. Для досрочного запуска нужно 50.</p><div class="coup-members">${coupMembers(conflict)}</div>${conflict.stage==='preparation'?`<div class="battle-actions"><button data-coup-action="divert">💰 Вывести ресурсы</button><button data-coup-action="forge">📜 Подделать указ</button><button data-coup-action="sway">🛡 Перетянуть силовиков</button><button data-coup-action="kompromat">📣 Компромат</button></div><details><summary>Вербовать ещё участника</summary><form id="coupInvite"><div class="field"><select name="target_user_id">${invite}</select></div><button class="action wide" type="submit">🕵 ОТПРАВИТЬ ПРИГЛАШЕНИЕ</button></form></details><button class="danger wide launch-coup" data-launch-coup>🗡 НАЧАТЬ ПЕРЕВОРОТ</button>`:'<p class="hint">Ожидается согласие приглашённого участника.</p>'}</article>`;
    }
    if(conflict.can_counterintel)return `<article class="panel crisis-panel"><div class="panel-title"><span>🔍</span><div><b>Контрразведка</b><small>Есть признаки внутренней угрозы · защита ${fmt(conflict.defense_score)}</small></div></div><button class="action wide" data-counterintel>🔍 ПРОВЕСТИ СЕКРЕТНУЮ ПРОВЕРКУ</button></article>`;
    return '<div class="empty">В государстве идёт засекреченный политический процесс.</div>';
  }

  function renderConflict(){
    const node=document.getElementById('crisisConflict');if(!node)return;
    const conflict=c().conflict;
    node.innerHTML=conflict?(conflict.type==='militia'?renderMilitia(conflict):renderCoup(conflict)):renderNoConflict();
  }

  function renderCouncil(){
    const node=document.getElementById('crisisCouncil');if(!node)return;const council=c().council;
    if(!council){node.innerHTML='';return}
    const officials=(c().targets||[]).filter(item=>['finance','oversight','supreme_court','prosecutor','central_bank','auditor','cec','ombudsman','security','press'].includes(item.office_key));
    node.innerHTML=`<article class="council-card"><div><small>РЕВОЛЮЦИОННЫЙ СОВЕТ</small><h3>Временная власть · ${esc(council.remaining)}</h3><p>${council.members.map(item=>esc(item.name)).join(' · ')}</p></div>${council.is_member?`<div class="council-actions"><button data-council="council_freeze">🧊 Заморозить операции</button><button data-council="council_amnesty">🕊 Амнистия</button><button data-council="council_call_election">🗳 Досрочные выборы</button>${officials.length?`<details><summary>Снять чиновника</summary><form id="councilRemove"><select name="office_key">${officials.map(item=>`<option value="${esc(item.office_key)}">${esc(item.title)} · ${esc(item.name)}</option>`).join('')}</select><button class="danger" type="submit">Снять</button></form></details>`:''}</div>`:''}</article>`;
  }

  function render(){if(!ensureRoot()||!state?.crisis_v131)return;renderCouncil();renderTheft();renderConflict();renderTheftLog()}
  function isEditing(){const active=document.activeElement;return Boolean(active&&active.matches('#crisisV131 input,#crisisV131 textarea,#crisisV131 select'))}

  document.addEventListener('click',event=>{
    const steal=event.target.closest('[data-steal]');if(steal){action('steal_treasury',{percent:Number(steal.dataset.steal)},`Попытаться вывести ${steal.dataset.steal}% государственной казны?`);return}
    const investigate=event.target.closest('[data-investigate]');if(investigate){action('investigate_theft',{theft_id:investigate.dataset.investigate},'Провести проверку подозрительной операции?');return}
    const side=event.target.closest('[data-join-side]');if(side){action('join_militia',{conflict_id:c().conflict?.conflict_id,side:side.dataset.joinSide},'Зафиксировать выбранную сторону?');return}
    const battle=event.target.closest('[data-militia-action]');if(battle){action('militia_action',{conflict_id:c().conflict?.conflict_id,battle_action:battle.dataset.militiaAction});return}
    const response=event.target.closest('[data-coup-response]');if(response){action('respond_coup_invite',{conflict_id:c().conflict?.conflict_id,accept:response.dataset.coupResponse==='1'},response.dataset.coupResponse==='1'?'Вступить в тайный заговор?':'Отклонить приглашение?');return}
    const coup=event.target.closest('[data-coup-action]');if(coup){action('coup_action',{conflict_id:c().conflict?.conflict_id,coup_action:coup.dataset.coupAction});return}
    if(event.target.closest('[data-counterintel]')){action('counterintel',{},'Начать секретную контрразведывательную проверку?');return}
    if(event.target.closest('[data-launch-coup]')){action('launch_coup',{conflict_id:c().conflict?.conflict_id},'Начать переворот сейчас? Результат будет окончательным.');return}
    const council=event.target.closest('[data-council]');if(council){action(council.dataset.council,{},'Применить полномочие Революционного совета?');return}
    if(event.target.closest('#refreshButton'))setTimeout(()=>load(true),250);
  });

  document.addEventListener('submit',event=>{
    if(event.target.id==='militiaCreate'){
      event.preventDefault();const data=Object.fromEntries(new FormData(event.target).entries());const [officeKey,seatNo]=String(data.target||'|1').split('|');
      action('create_militia',{office_key:officeKey,seat_no:Number(seatNo||1),reason:data.reason||''},'Открыть публичное ополчение против этого чиновника?');return;
    }
    if(event.target.id==='coupCreate'){
      event.preventDefault();const data=Object.fromEntries(new FormData(event.target).entries());
      action('create_coup',{target_user_id:Number(data.target_user_id||0),reason:data.reason||''},'Создать тайный заговор и отправить приглашение?');return;
    }
    if(event.target.id==='coupInvite'){
      event.preventDefault();const data=Object.fromEntries(new FormData(event.target).entries());
      action('coup_invite',{conflict_id:c().conflict?.conflict_id,target_user_id:Number(data.target_user_id||0)});return;
    }
    if(event.target.id==='councilRemove'){
      event.preventDefault();const data=Object.fromEntries(new FormData(event.target).entries());
      action('council_remove_official',{office_key:data.office_key||''},'Снять выбранного чиновника?');return;
    }
  });

  document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!isEditing())load(true)});
  ensureRoot();load();clearInterval(timer);timer=setInterval(()=>{if(!document.hidden&&!busy&&!isEditing())load(true)},30000);
})();
