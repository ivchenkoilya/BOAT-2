(()=>{
  'use strict';
  if(window.__oversightDeputyV167)return;
  window.__oversightDeputyV167=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';

  let state=null;
  let loading=false;

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=String(text||'Готово.');
    node.className=`toast show ${type}`;
    clearTimeout(node.__od167Timer);
    node.__od167Timer=setTimeout(()=>node.className='toast',3800);
  }

  async function api(path,options={}){
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),15000);
    try{
      const response=await fetch(path,{cache:'no-store',...options,signal:controller.signal,headers:{...headers,...(options.headers||{})}});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      return data;
    }catch(error){
      if(error.name==='AbortError')throw new Error('Сервер долго не отвечает.');
      throw error;
    }finally{clearTimeout(timer)}
  }

  function oversightActive(){
    return Boolean(document.querySelector('.screen[data-screen="oversight"]')?.classList.contains('active'));
  }

  function userOptions(selected=0){
    return (state?.eligible_users||[]).map(user=>
      `<option value="${user.user_id}" ${Number(selected)===Number(user.user_id)?'selected':''}>${esc(user.name)} · ⭐ ${fmt(user.career_points)}</option>`
    ).join('');
  }

  function complaintOptions(){
    const items=(state?.oversight_deputy_v167?.complaints||[]).filter(item=>['pending','investigating'].includes(item.status));
    return `<option value="">Без привязки к жалобе</option>`+items.map(item=>
      `<option value="${esc(item.complaint_id)}">${esc(item.target_name)} · ${esc(item.reason.slice(0,70))}</option>`
    ).join('');
  }

  function caseOptions(){
    const items=(state?.oversight_deputy_v167?.cases||[]).filter(item=>['open','referred'].includes(item.status));
    return items.map(item=>
      `<option value="${esc(item.case_id)}">${esc(item.title)} · ${esc(item.target_name)}</option>`
    ).join('');
  }

  function ensureMount(){
    const screen=document.querySelector('.screen[data-screen="oversight"]');
    if(!screen)return null;
    let node=document.getElementById('oversightDeputyV167');
    if(node)return node;
    node=document.createElement('div');
    node.id='oversightDeputyV167';
    node.className='oversight-deputy-v167';
    const head=screen.querySelector('.section-head');
    if(head)head.insertAdjacentElement('afterend',node);
    else screen.prepend(node);
    return node;
  }

  function addHomeOffice(){
    if(!state)return;
    const spec=state.office_specs?.oversight_deputy;
    const grid=document.getElementById('officeGrid');
    if(!spec||!grid)return;
    document.getElementById('oversightDeputyOfficeV167')?.remove();
    const office=(state.offices||[]).find(item=>item.office_key==='oversight_deputy');
    const card=document.createElement('article');
    card.id='oversightDeputyOfficeV167';
    card.className=`office-card ${office?'':'vacant'}`;
    card.innerHTML=office
      ? `<div class="office-title"><span>${spec.emoji}</span><div><b>${esc(spec.title)}</b><small>Полномочия: ещё ${esc(office.remaining)}</small></div></div><div class="office-person">${esc(office.name)}</div><div class="office-meta">⭐ ${fmt(office.career_points)} · доверие ${fmt(office.trust)}%</div><div class="trust"><i style="width:${Math.max(0,Math.min(100,Number(office.trust)||0))}%"></i></div>`
      : `<div class="office-title"><span>${spec.emoji}</span><div><b>${esc(spec.title)}</b><small>Порог: ${fmt(spec.threshold)} карьеры</small></div></div><div class="office-person">Должность свободна</div><div class="office-meta">Кандидатуру предлагает Президент или глава Надзора, решение принимает Госдума.</div>`;
    grid.append(card);
  }

  function statusTitle(status){
    return ({
      pending:'ОЖИДАЕТ',
      investigating:'ПРОВЕРЯЕТСЯ',
      closed:'ЗАКРЫТО',
      referred:'ПРОКУРАТУРА',
      sanction_bill:'В ГОСДУМЕ',
      open:'ОТКРЫТО'
    })[status]||String(status||'');
  }

  function statusClass(status){
    if(status==='closed')return 'green';
    if(status==='referred'||status==='sanction_bill')return 'gold';
    return 'red';
  }

  function complaintCard(item,canManage){
    const action=canManage&&item.status==='pending'
      ? `<button class="action" data-complaint-inspect="${esc(item.complaint_id)}" data-target="${item.target_user_id}">🔍 ОТКРЫТЬ ПРОВЕРКУ</button>`
      :'';
    return `<article class="od-card-v167">
      <div class="card-head"><div><b>📨 Жалоба на ${esc(item.target_name)}</b><small>${date(item.created_at)} · заявитель ${esc(item.author_name)}</small></div><span class="badge ${statusClass(item.status)}">${esc(statusTitle(item.status))}</span></div>
      <p>${esc(item.reason)}</p>
      ${item.evidence?`<div class="od-evidence-v167"><b>Материалы:</b> ${esc(item.evidence)}</div>`:''}
      ${action}
    </article>`;
  }

  function caseCard(item,canManage){
    const actions=canManage&&['open','referred'].includes(item.status)?`<div class="od-actions-v167">
      ${item.status==='open'?`<button class="secondary" data-case-refer="${esc(item.case_id)}">🛡 В ПРОКУРАТУРУ</button>`:''}
      <button class="positive" data-case-close="${esc(item.case_id)}">✅ ЗАКРЫТЬ</button>
    </div>`:'';
    return `<article class="od-card-v167">
      <div class="card-head"><div><b>🔍 ${esc(item.title)}</b><small>${esc(item.target_name)} · ${date(item.created_at)}</small></div><span class="badge ${statusClass(item.status)}">${esc(statusTitle(item.status))}</span></div>
      <p>${esc(item.facts)}</p>
      ${item.conclusion?`<div class="od-evidence-v167"><b>Заключение:</b> ${esc(item.conclusion)}</div>`:''}
      ${item.bill_id?`<small class="od-bill-v167">Санкционный законопроект: ${esc(item.bill_id)}</small>`:''}
      ${actions}
    </article>`;
  }

  function warningCard(item){
    return `<article class="od-warning-v167 ${item.active?'active':''}">
      <div><b>${item.active?'⚠️ Подозреваемый гондон':'⚪ Статус завершён'} · ${esc(item.target_name)}</b><small>${esc(item.reason)} · ${item.active?`до ${date(item.expires_at)}`:date(item.created_at)}</small></div>
    </article>`;
  }

  function render(){
    const mount=ensureMount();
    if(!mount||!state)return;
    const od=state.oversight_deputy_v167||{};
    const complaints=Array.isArray(od.complaints)?od.complaints:[];
    const cases=Array.isArray(od.cases)?od.cases:[];
    const warnings=Array.isArray(od.warnings)?od.warnings:[];
    const canManage=Boolean(od.can_manage);
    const canAppoint=Boolean(od.can_propose_appointment);
    const inspectionNote=canManage
      ? `Проверок за 24 часа: ${fmt(od.inspection_used_24h)}/${od.inspection_limit_24h>=999?'∞':fmt(od.inspection_limit_24h)}${od.inspection_available_at?` · следующая ${date(od.inspection_available_at)}`:''}`
      :'Доступно главе Надзора и его заместителю';

    const complaintForm=`<article class="panel od-hero-v167">
      <div class="panel-title"><span>🕵️</span><div><b>Заместитель главы Надзора за гондонами</b><small>Жалобы, проверки, предупреждения и публичный реестр</small></div></div>
      <div class="od-duty-grid-v167">
        <div><b>📨 Жалобы</b><small>принимает обращения участников</small></div>
        <div><b>🔍 Проверки</b><small>1 внеплановая проверка в сутки</small></div>
        <div><b>⚠️ Реестр</b><small>статус подозреваемого на 24 часа</small></div>
        <div><b>🏛 Санкции</b><small>только через голосование Госдумы</small></div>
      </div>
      <form id="odComplaintFormV167">
        <div class="field"><label>НА КОГО ЖАЛОБА</label><select name="target_user_id">${userOptions()}</select></div>
        <div class="field"><label>СУТЬ ЖАЛОБЫ</label><textarea name="reason" minlength="10" maxlength="500" placeholder="Что произошло и какое правило нарушено"></textarea></div>
        <div class="field"><label>ДОКАЗАТЕЛЬСТВА</label><textarea name="evidence" maxlength="700" placeholder="Ссылки на сообщения, свидетели, факты"></textarea></div>
        <button class="action wide" type="submit">📨 ПЕРЕДАТЬ ЖАЛОБУ В НАДЗОР</button>
      </form>
    </article>`;

    const managePanel=canManage?`<article class="panel">
      <div class="panel-title"><span>🔍</span><div><b>Полевое управление Надзора</b><small>${esc(inspectionNote)}</small></div></div>
      <div class="od-tabs-v167">
        <form id="odInspectionFormV167">
          <h3>Открыть проверку</h3>
          <div class="field"><label>ЖАЛОБА</label><select name="complaint_id">${complaintOptions()}</select></div>
          <div class="field"><label>ПРОВЕРЯЕМЫЙ</label><select name="target_user_id">${userOptions()}</select></div>
          <div class="field"><label>НАЗВАНИЕ</label><input name="title" maxlength="140" value="Проверка на гондонизм"></div>
          <div class="field"><label>МАТЕРИАЛЫ</label><textarea name="facts" maxlength="1200" placeholder="Факты и основания проверки"></textarea></div>
          <button class="action wide" type="submit">🔍 ОТКРЫТЬ ПРОВЕРКУ</button>
        </form>
        <form id="odWarningFormV167">
          <h3>Выдать предупреждение</h3>
          <div class="field"><label>УЧАСТНИК</label><select name="target_user_id">${userOptions()}</select></div>
          <div class="field"><label>ПРИЧИНА</label><textarea name="reason" maxlength="500" placeholder="За что выдаётся предупреждение"></textarea></div>
          <button class="danger wide" type="submit">⚠️ СТАТУС НА 24 ЧАСА</button>
        </form>
      </div>
      <form id="odSanctionFormV167" class="od-sanction-form-v167">
        <h3>Предложить санкции по делу</h3>
        <div class="field"><label>ДЕЛО</label><select name="case_id">${caseOptions()}</select></div>
        <div class="check-grid">
          <label class="check"><input type="checkbox" name="types" value="gambling"><span>🎲 Азартные игры</span></label>
          <label class="check"><input type="checkbox" name="types" value="finance"><span>💸 Финансы</span></label>
          <label class="check"><input type="checkbox" name="types" value="miniapp"><span>🎮 Mini App</span></label>
          <label class="check"><input type="checkbox" name="types" value="career_freeze"><span>⭐ Карьера</span></label>
          <label class="check"><input type="checkbox" name="types" value="full_game"><span>🔒 Полный бан</span></label>
        </div>
        <div class="field"><label>СРОК</label><select name="duration"><option value="3600">1 час</option><option value="21600">6 часов</option><option value="86400" selected>24 часа</option><option value="259200">3 дня</option><option value="604800">7 дней</option></select></div>
        <div class="field"><label>ОБОСНОВАНИЕ</label><textarea name="reason" maxlength="500" placeholder="Почему дело требует санкций"></textarea></div>
        <button class="danger wide" type="submit">🏛 ПЕРЕДАТЬ ПРЕДЛОЖЕНИЕ В ГОСДУМУ</button>
      </form>
      <button class="secondary wide" id="odWeeklyReportV167" type="button">📊 ОПУБЛИКОВАТЬ ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ</button>
    </article>`:'';

    const appointment=canAppoint?`<article class="panel">
      <div class="panel-title"><span>🎖</span><div><b>Назначить заместителя</b><small>Кандидатуру предлагает Президент или глава Надзора, голосует Госдума</small></div></div>
      <form id="odAppointmentFormV167">
        <div class="field"><label>КАНДИДАТ</label><select name="target_user_id">${userOptions()}</select></div>
        <div class="field"><label>ОБОСНОВАНИЕ</label><textarea name="reason" maxlength="600" placeholder="Почему кандидат подходит для полевой работы Надзора"></textarea></div>
        <button class="positive wide" type="submit">🎖 ВНЕСТИ КАНДИДАТУРУ В ГОСДУМУ</button>
      </form>
    </article>`:'';

    mount.innerHTML=`${complaintForm}${managePanel}${appointment}
      <div class="section-head"><div><small>ОЧЕРЕДЬ НАДЗОРА</small><h2>Жалобы участников</h2></div></div>
      <div class="od-list-v167">${complaints.length?complaints.map(item=>complaintCard(item,canManage)).join(''):'<div class="empty">Жалоб пока нет.</div>'}</div>
      <div class="section-head"><div><small>СЛЕДСТВЕННАЯ РАБОТА</small><h2>Проверки и дела</h2></div></div>
      <div class="od-list-v167">${cases.length?cases.map(item=>caseCard(item,canManage)).join(''):'<div class="empty">Открытых проверок пока нет.</div>'}</div>
      <div class="section-head"><div><small>ПУБЛИЧНЫЙ РЕЕСТР</small><h2>Предупреждения Надзора</h2></div></div>
      <div class="od-list-v167">${warnings.length?warnings.map(warningCard).join(''):'<div class="empty">В реестре пока никого нет.</div>'}</div>`;

    addHomeOffice();
    const brand=document.querySelector('.brand small');
    if(brand)brand.textContent='REALITY 167';
  }

  async function load(force=false){
    if(!chatId||loading)return;
    loading=true;
    try{
      state=await api(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_od167=${Date.now()}`);
      render();
    }catch(error){
      if(force||oversightActive())toast(error.message||'Не удалось загрузить Надзор.','error');
    }finally{loading=false}
  }

  async function post(payload,confirmation=''){
    if(confirmation&&!confirm(confirmation))return;
    try{
      const result=await api('/government-v167/api/action',{method:'POST',body:JSON.stringify({chat_id:chatId,...payload})});
      toast(result.message||'Готово.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      document.getElementById('refreshButton')?.click();
      setTimeout(()=>load(true),240);
    }catch(error){
      toast(error.message||'Действие не выполнено.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }
  }

  document.addEventListener('submit',event=>{
    const form=event.target;
    if(!form?.id?.startsWith('od'))return;
    event.preventDefault();
    const data=Object.fromEntries(new FormData(form).entries());
    if(form.id==='odComplaintFormV167'){
      post({action:'complaint_create',target_user_id:Number(data.target_user_id)||0,reason:String(data.reason||''),evidence:String(data.evidence||'')});
    }else if(form.id==='odInspectionFormV167'){
      post({action:'inspection_open',complaint_id:String(data.complaint_id||''),target_user_id:Number(data.target_user_id)||0,title:String(data.title||''),facts:String(data.facts||'')},'Открыть официальную внеплановую проверку?');
    }else if(form.id==='odWarningFormV167'){
      post({action:'warning_issue',target_user_id:Number(data.target_user_id)||0,reason:String(data.reason||'')},'Выдать участнику статус «Подозреваемый гондон» на 24 часа?');
    }else if(form.id==='odSanctionFormV167'){
      const types=[...form.querySelectorAll('input[name="types"]:checked')].map(input=>input.value);
      post({action:'sanction_propose',case_id:String(data.case_id||''),types,duration:Number(data.duration)||86400,reason:String(data.reason||'')},'Передать санкционное предложение в Госдуму?');
    }else if(form.id==='odAppointmentFormV167'){
      post({action:'appointment_propose',target_user_id:Number(data.target_user_id)||0,reason:String(data.reason||'')},'Внести кандидатуру заместителя в Госдуму?');
    }
  },true);

  document.addEventListener('click',event=>{
    if(event.target.closest?.('[data-tab="oversight"]'))setTimeout(()=>load(true),160);
    if(event.target.closest?.('#refreshButton'))setTimeout(()=>load(true),220);
    const inspect=event.target.closest?.('[data-complaint-inspect]');
    if(inspect){
      const facts=prompt('Материалы проверки:','Проверить изложенные в жалобе факты');
      if(facts!==null)post({action:'inspection_open',complaint_id:inspect.dataset.complaintInspect,target_user_id:Number(inspect.dataset.target)||0,title:'Проверка по жалобе',facts},'Открыть проверку по этой жалобе?');
      return;
    }
    const close=event.target.closest?.('[data-case-close]');
    if(close){
      const conclusion=prompt('Заключение по делу:','Нарушение не подтверждено');
      if(conclusion!==null)post({action:'case_close',case_id:close.dataset.caseClose,conclusion});
      return;
    }
    const refer=event.target.closest?.('[data-case-refer]');
    if(refer){
      const note=prompt('Комментарий для прокуратуры:','Требуется дополнительная проверка и оценка доказательств');
      if(note!==null)post({action:'case_refer',case_id:refer.dataset.caseRefer,note},'Передать материалы Генеральному прокурору?');
      return;
    }
    if(event.target.closest?.('#odWeeklyReportV167')){
      post({action:'weekly_report'},'Опубликовать публичный отчёт Надзора за последние 7 дней?');
    }
  },true);

  const observer=new MutationObserver(()=>{
    if(document.getElementById('officeGrid')&&!document.getElementById('oversightDeputyOfficeV167')&&state)addHomeOffice();
  });
  observer.observe(document.documentElement,{childList:true,subtree:true});

  setTimeout(()=>load(false),450);
})();