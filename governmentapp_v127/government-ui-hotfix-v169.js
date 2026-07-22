(()=>{
  'use strict';
  if(window.__governmentUiHotfixV172)return;
  window.__governmentUiHotfixV172=true;

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
  let posting=false;

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=String(text||'Готово.');
    node.className=`toast show ${type}`;
    clearTimeout(node.__ui172Toast);
    node.__ui172Toast=setTimeout(()=>node.className='toast',3800);
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

  function powersActive(){return Boolean(document.querySelector('.screen[data-screen="powers"]')?.classList.contains('active'))}
  function userOptions(selected=0){return (state?.eligible_users||[]).map(user=>`<option value="${Number(user.user_id)||0}" ${Number(selected)===Number(user.user_id)?'selected':''}>${esc(user.name)} · ⭐ ${fmt(user.career_points)}</option>`).join('')}
  function complaintOptions(selected=''){
    const complaints=(state?.oversight_deputy_v167?.complaints||[]).filter(item=>['pending','investigating'].includes(item.status));
    return `<option value="">Без привязки к жалобе</option>`+complaints.map(item=>`<option value="${esc(item.complaint_id)}" ${String(selected)===String(item.complaint_id)?'selected':''}>${esc(item.target_name)} · ${esc(String(item.reason||'').slice(0,70))}</option>`).join('');
  }
  function caseOptions(selected=''){
    const cases=(state?.oversight_deputy_v167?.cases||[]).filter(item=>['open','referred'].includes(item.status));
    return cases.map(item=>`<option value="${esc(item.case_id)}" ${String(selected)===String(item.case_id)?'selected':''}>${esc(item.title)} · ${esc(item.target_name)}</option>`).join('');
  }
  function statusTitle(status){return ({pending:'ОЖИДАЕТ',investigating:'ПРОВЕРЯЕТСЯ',closed:'ЗАКРЫТО',referred:'ПРОКУРАТУРА',sanction_bill:'В ГОСДУМЕ',open:'ОТКРЫТО'})[status]||String(status||'')}
  function statusClass(status){if(status==='closed')return 'green';if(status==='referred'||status==='sanction_bill')return 'gold';return 'red'}

  function complaintCard(item,canManage){
    const action=canManage&&item.status==='pending'?`<button class="action" type="button" data-od172-inspect-complaint="${esc(item.complaint_id)}" data-target="${Number(item.target_user_id)||0}">🔍 ОТКРЫТЬ ПРОВЕРКУ</button>`:'';
    return `<article class="od172-item"><div class="card-head"><div><b>📨 Жалоба на ${esc(item.target_name)}</b><small>${date(item.created_at)} · заявитель ${esc(item.author_name)}</small></div><span class="badge ${statusClass(item.status)}">${esc(statusTitle(item.status))}</span></div><p>${esc(item.reason)}</p>${item.evidence?`<div class="od172-evidence"><b>Материалы:</b> ${esc(item.evidence)}</div>`:''}${action}</article>`;
  }
  function caseCard(item,canManage){
    const actions=canManage&&['open','referred'].includes(item.status)?`<div class="od172-row-actions">${item.status==='open'?`<button class="secondary" type="button" data-od172-case-refer="${esc(item.case_id)}">🛡 В ПРОКУРАТУРУ</button>`:''}<button class="positive" type="button" data-od172-case-close="${esc(item.case_id)}">✅ ЗАКРЫТЬ</button></div>`:'';
    return `<article class="od172-item"><div class="card-head"><div><b>🔍 ${esc(item.title)}</b><small>${esc(item.target_name)} · ${date(item.created_at)}</small></div><span class="badge ${statusClass(item.status)}">${esc(statusTitle(item.status))}</span></div><p>${esc(item.facts)}</p>${item.conclusion?`<div class="od172-evidence"><b>Заключение:</b> ${esc(item.conclusion)}</div>`:''}${actions}</article>`;
  }
  function warningCard(item){return `<article class="od172-warning ${item.active?'active':''}"><b>${item.active?'⚠️ Подозреваемый гондон':'⚪ Статус завершён'} · ${esc(item.target_name)}</b><small>${esc(item.reason)} · ${item.active?`до ${date(item.expires_at)}`:date(item.created_at)}</small></article>`}

  function restoreLegacyPanel(){
    const legacy=document.getElementById('oversightDeputyV167');
    const oversight=document.querySelector('.screen[data-screen="oversight"]');
    if(!legacy||!oversight||oversight.contains(legacy))return;
    const head=oversight.querySelector('.section-head');
    if(head)head.insertAdjacentElement('afterend',legacy);else oversight.prepend(legacy);
    legacy.classList.remove('od-mounted-powers-v170');
  }

  function compactAction(key,emoji,title,hint,disabled=false){return `<button class="power-action od172-action" type="button" data-od172-action="${key}" ${disabled?'disabled':''}><span>${emoji}</span><b>${esc(title)}</b><small>${esc(hint)}</small></button>`}

  function renderDeputyPanel(){
    const hero=document.getElementById('powerHero');
    if(!hero||!state)return null;
    const od=state.oversight_deputy_v167||{};
    const canManage=Boolean(od.can_manage);
    const canAppoint=Boolean(od.can_propose_appointment);
    let panel=document.getElementById('oversightDeputyPowersV172');
    if(!(canManage||canAppoint)){panel?.remove();return null}
    if(!panel){panel=document.createElement('section');panel.id='oversightDeputyPowersV172';panel.className='od172-panel'}
    if(panel.previousElementSibling!==hero)hero.insertAdjacentElement('afterend',panel);

    const complaints=Array.isArray(od.complaints)?od.complaints:[];
    const cases=Array.isArray(od.cases)?od.cases:[];
    const warnings=Array.isArray(od.warnings)?od.warnings:[];
    const holder=(state.offices||[]).find(item=>item.office_key==='oversight_deputy');
    const limit=Number(od.inspection_limit_24h)>=999?'∞':fmt(od.inspection_limit_24h);
    const actions=[];
    if(canAppoint)actions.push(compactAction('appointment','🎖',holder?'Сменить заместителя':'Назначить заместителя','Кандидатура проходит через Госдуму'));
    if(canManage){
      actions.push(compactAction('inspection','🔍','Открыть проверку',`Использовано ${fmt(od.inspection_used_24h)}/${limit} за 24 часа`));
      actions.push(compactAction('warning','⚠️','Выдать предупреждение','Статус на 24 часа'));
      actions.push(compactAction('sanction','🏛','Предложить санкции',cases.length?'По открытому делу':'Сначала откройте дело',cases.length===0));
      actions.push(compactAction('report','📊','Опубликовать отчёт','Сводка работы за 7 дней'));
    }

    panel.innerHTML=`<article class="power-card od172-power-card"><div class="power-card-head"><span>🕵️</span><div><b>Заместитель главы Надзора за гондонами</b><small>${holder?`Должность занимает ${esc(holder.name)} · ${esc(holder.remaining||'действует')}`:'Должность свободна'} · компактная панель управления</small></div></div><div class="power-actions od172-power-actions">${actions.join('')}</div></article><div class="od172-registers"><details><summary>📨 Жалобы · ${complaints.length}</summary><div class="od172-list">${complaints.length?complaints.map(item=>complaintCard(item,canManage)).join(''):'<div class="empty">Жалоб пока нет.</div>'}</div></details><details><summary>📁 Дела · ${cases.length}</summary><div class="od172-list">${cases.length?cases.map(item=>caseCard(item,canManage)).join(''):'<div class="empty">Открытых дел пока нет.</div>'}</div></details><details><summary>⚠️ Реестр · ${warnings.filter(item=>item.active).length}</summary><div class="od172-list">${warnings.length?warnings.map(warningCard).join(''):'<div class="empty">В реестре пока никого нет.</div>'}</div></details></div>`;
    return panel;
  }

  function modalNodes(){return {modal:document.getElementById('powerModal'),form:document.getElementById('powerForm'),fields:document.getElementById('powerFormFields'),title:document.getElementById('powerModalTitle'),office:document.getElementById('powerModalOffice'),submit:document.querySelector('#powerForm button[type="submit"]')}}
  function closeDeputyModal(){const {modal,form}=modalNodes();modal?.classList.remove('open');if(form){delete form.dataset.od172Action;delete form.dataset.action}document.body.style.overflow=''}
  function modalFields(action,prefill={}){
    if(action==='appointment')return `<div class="field"><label>КАНДИДАТ</label><select name="target_user_id">${userOptions(prefill.target_user_id||0)}</select></div><div class="field"><label>ОБОСНОВАНИЕ</label><textarea name="reason" minlength="10" maxlength="600" placeholder="Почему кандидат подходит для полевой работы Надзора"></textarea></div>`;
    if(action==='inspection')return `<div class="field"><label>ЖАЛОБА</label><select name="complaint_id">${complaintOptions(prefill.complaint_id||'')}</select></div><div class="field"><label>ПРОВЕРЯЕМЫЙ</label><select name="target_user_id">${userOptions(prefill.target_user_id||0)}</select></div><div class="field"><label>НАЗВАНИЕ</label><input name="title" maxlength="140" value="Проверка на гондонизм"></div><div class="field"><label>МАТЕРИАЛЫ</label><textarea name="facts" minlength="10" maxlength="1200" placeholder="Факты и основания проверки">${esc(prefill.facts||'')}</textarea></div>`;
    if(action==='warning')return `<div class="field"><label>УЧАСТНИК</label><select name="target_user_id">${userOptions(prefill.target_user_id||0)}</select></div><div class="field"><label>ПРИЧИНА</label><textarea name="reason" minlength="5" maxlength="500" placeholder="За что выдаётся предупреждение"></textarea></div>`;
    if(action==='sanction')return `<div class="field"><label>ДЕЛО</label><select name="case_id">${caseOptions(prefill.case_id||'')||'<option value="">Сначала откройте дело</option>'}</select></div><div class="check-grid od172-check-grid"><label class="check"><input type="checkbox" name="types" value="gambling"><span>🎲 Азартные игры</span></label><label class="check"><input type="checkbox" name="types" value="finance"><span>💸 Финансы</span></label><label class="check"><input type="checkbox" name="types" value="miniapp"><span>🎮 Mini App</span></label><label class="check"><input type="checkbox" name="types" value="career_freeze"><span>⭐ Карьера</span></label><label class="check"><input type="checkbox" name="types" value="full_game"><span>🔒 Полный бан</span></label></div><div class="field"><label>СРОК</label><select name="duration"><option value="3600">1 час</option><option value="21600">6 часов</option><option value="86400" selected>24 часа</option><option value="259200">3 дня</option><option value="604800">7 дней</option></select></div><div class="field"><label>ОБОСНОВАНИЕ</label><textarea name="reason" minlength="5" maxlength="500" placeholder="Почему дело требует санкций"></textarea></div>`;
    return '';
  }
  function openDeputyModal(action,prefill={}){
    if(action==='report'){post({action:'weekly_report'},'Опубликовать отчёт Надзора за последние 7 дней?');return}
    const labels={appointment:['Назначить заместителя','Кандидатура будет передана в Госдуму','🎖 ПЕРЕДАТЬ КАНДИДАТУРУ'],inspection:['Открыть проверку','Официальное внеплановое расследование','🔍 ОТКРЫТЬ ПРОВЕРКУ'],warning:['Выдать предупреждение','Статус «Подозреваемый гондон» на 24 часа','⚠️ ВЫДАТЬ ПРЕДУПРЕЖДЕНИЕ'],sanction:['Предложить санкции','Решение принимает Госдума','🏛 ПЕРЕДАТЬ В ГОСДУМУ']};
    const config=labels[action];const {modal,form,fields,title,office,submit}=modalNodes();
    if(!config||!modal||!form||!fields)return;
    form.dataset.od172Action=action;delete form.dataset.action;fields.innerHTML=modalFields(action,prefill);
    if(title)title.textContent=config[0];if(office)office.textContent=config[1];if(submit)submit.textContent=config[2];
    modal.classList.add('open');document.body.style.overflow='hidden';
  }

  function deputyCard(){
    const grid=document.getElementById('institutionGrid');if(!grid||!state)return;
    document.getElementById('oversightDeputyInstitutionV169')?.remove();
    const spec=state.office_specs?.oversight_deputy||{emoji:'🕵️',title:'Заместитель главы Надзора за гондонами',threshold:200000};
    const holder=(state.offices||[]).find(item=>item.office_key==='oversight_deputy');
    const card=document.createElement('article');card.id='oversightDeputyInstitutionV169';card.className=`institution-card ${holder?'active':''}`;card.tabIndex=0;card.setAttribute('role','button');card.setAttribute('aria-label','Открыть полномочия заместителя главы Надзора');
    card.innerHTML=`<span>${esc(spec.emoji||'🕵️')}</span><b>${esc(spec.title)}</b><small>${holder?`${esc(holder.name)} · ещё ${esc(holder.remaining||'действует')}`:`Свободно · порог ${fmt(spec.threshold)} карьеры · назначение через Госдуму`}</small>`;
    card.addEventListener('click',openDeputyPanel);card.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();openDeputyPanel()}});grid.prepend(card);
  }
  function patchAppointmentSelect(){
    const select=document.querySelector('#powerFormFields select[name="office_key"]');if(!select||select.querySelector('option[value="oversight_deputy"]'))return;
    const spec=state?.office_specs?.oversight_deputy||{emoji:'🕵️',title:'Заместитель главы Надзора за гондонами'};const option=document.createElement('option');option.value='oversight_deputy';option.textContent=`${spec.emoji||'🕵️'} ${spec.title}`;
    const oversight=select.querySelector('option[value="oversight"]');if(oversight)oversight.insertAdjacentElement('afterend',option);else select.appendChild(option);
  }
  function repairCrisisDom(){document.querySelectorAll('#crisisV131 .crisis-grid>div,#crisisV131 .crisis-panel').forEach(node=>{node.style.height='auto';node.style.minHeight='0'})}
  async function load(force=false){
    if(!chatId||loading)return;loading=true;
    try{state=await api(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_ui172=${Date.now()}`);restoreLegacyPanel();deputyCard();renderDeputyPanel();patchAppointmentSelect()}
    catch(error){if(force)toast(error.message||'Не удалось загрузить полномочия Надзора.','error')}
    finally{loading=false}
  }
  async function post(payload,confirmation=''){
    if(posting)return;if(confirmation&&!confirm(confirmation))return;posting=true;
    try{const result=await api('/government-v167/api/action',{method:'POST',body:JSON.stringify({chat_id:chatId,...payload})});closeDeputyModal();toast(result.message||'Действие выполнено.');tg?.HapticFeedback?.notificationOccurred?.('success');await load(true);document.getElementById('refreshButton')?.click()}
    catch(error){toast(error.message||'Действие не выполнено.','error');tg?.HapticFeedback?.notificationOccurred?.('error')}
    finally{posting=false}
  }
  async function openDeputyPanel(){
    if(!powersActive()){document.querySelector('[data-tab="powers"]')?.click();await new Promise(resolve=>setTimeout(resolve,220))}
    if(!state)await load(true);const panel=renderDeputyPanel();if(panel)panel.scrollIntoView({behavior:'smooth',block:'start'});else toast('Панель доступна главе Надзора, назначенному заместителю и Президенту для назначения.','error');
  }

  document.addEventListener('submit',event=>{
    const form=event.target;const action=form?.dataset?.od172Action;if(!action)return;
    event.preventDefault();event.stopImmediatePropagation();const data=Object.fromEntries(new FormData(form).entries());
    if(action==='appointment')post({action:'appointment_propose',target_user_id:Number(data.target_user_id)||0,reason:String(data.reason||'')},'Передать кандидатуру заместителя в Госдуму?');
    else if(action==='inspection')post({action:'inspection_open',complaint_id:String(data.complaint_id||''),target_user_id:Number(data.target_user_id)||0,title:String(data.title||''),facts:String(data.facts||'')},'Открыть официальную внеплановую проверку?');
    else if(action==='warning')post({action:'warning_issue',target_user_id:Number(data.target_user_id)||0,reason:String(data.reason||'')},'Выдать участнику статус «Подозреваемый гондон» на 24 часа?');
    else if(action==='sanction'){const types=[...form.querySelectorAll('input[name="types"]:checked')].map(input=>input.value);post({action:'sanction_propose',case_id:String(data.case_id||''),types,duration:Number(data.duration)||86400,reason:String(data.reason||'')},'Передать санкционное предложение в Госдуму?')}
  },true);

  document.addEventListener('click',event=>{
    const actionButton=event.target.closest?.('[data-od172-action]');
    if(actionButton){event.preventDefault();event.stopImmediatePropagation();openDeputyModal(actionButton.dataset.od172Action||'');return}
    if(event.target.closest?.('[data-tab="powers"]'))setTimeout(()=>{repairCrisisDom();restoreLegacyPanel();deputyCard();renderDeputyPanel();load(false)},180);
    if(event.target.closest?.('[data-power-action="appointment"]')){setTimeout(patchAppointmentSelect,30);setTimeout(patchAppointmentSelect,180)}
    const inspect=event.target.closest?.('[data-od172-inspect-complaint]');
    if(inspect){openDeputyModal('inspection',{complaint_id:String(inspect.dataset.od172InspectComplaint||''),target_user_id:Number(inspect.dataset.target)||0,facts:'Проверить изложенные в жалобе факты'});return}
    const refer=event.target.closest?.('[data-od172-case-refer]');
    if(refer){const note=prompt('Комментарий для прокуратуры:','Требуется дополнительная проверка и оценка доказательств');if(note!==null)post({action:'case_refer',case_id:String(refer.dataset.od172CaseRefer||''),note},'Передать материалы Генеральному прокурору?');return}
    const close=event.target.closest?.('[data-od172-case-close]');
    if(close){const conclusion=prompt('Заключение по делу:','Нарушение не подтверждено');if(conclusion!==null)post({action:'case_close',case_id:String(close.dataset.od172CaseClose||''),conclusion});return}
    if(event.target.closest?.('[data-power-close]'))closeDeputyModal();
    if(event.target.closest?.('#refreshButton'))setTimeout(()=>load(false),260);
  },true);

  repairCrisisDom();load(false);
  const observer=new MutationObserver(()=>{repairCrisisDom();if(state&&document.getElementById('institutionGrid')&&!document.getElementById('oversightDeputyInstitutionV169'))deputyCard();if(state&&powersActive()&&!document.getElementById('oversightDeputyPowersV172'))renderDeputyPanel();patchAppointmentSelect()});
  observer.observe(document.documentElement,{childList:true,subtree:true});
})();
