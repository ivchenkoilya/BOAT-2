(()=>{
  'use strict';
  if(window.__theftQuestV163)return;
  window.__theftQuestV163=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const esc=value=>String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const dt=value=>new Intl.DateTimeFormat('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}).format(new Date(Number(value)*1000));
  let state=null,busy=false,timer=null;

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return alert(text);
    node.textContent=text;node.className=`toast show ${type}`;
    clearTimeout(node._quest163Timer);node._quest163Timer=setTimeout(()=>node.className='toast',4200);
  }

  function ensureRoot(){
    let root=document.getElementById('theftQuestV163');
    if(root)return root;
    root=document.createElement('section');
    root.id='theftQuestV163';root.className='theft-quest-v163';
    const crisis=document.getElementById('crisisV131');
    const hero=document.getElementById('powerHero');
    if(crisis)crisis.insertAdjacentElement('afterend',root);
    else if(hero)hero.insertAdjacentElement('afterend',root);
    else document.querySelector('main')?.appendChild(root);
    return root;
  }

  async function load(silent=true){
    if(!chatId||busy)return;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_q163=${Date.now()}`,{cache:'no-store',headers:{'X-Telegram-Init-Data':tg?.initData||''}});
      const data=await response.json().catch(()=>({ok:false,reason:'Некорректный ответ сервера.'}));
      if(!response.ok||!data?.ok)throw new Error(data.reason||'Не удалось загрузить уголовные дела.');
      state=data;render();
    }catch(error){if(!silent)toast(error.message||'Ошибка загрузки дел.','error')}
  }

  async function action(name,payload={},confirmation=''){
    if(busy)return null;
    if(confirmation&&!confirm(confirmation))return null;
    busy=true;
    try{
      const response=await fetch('/government-v163/api/action',{method:'POST',cache:'no-store',headers,body:JSON.stringify({action:name,chat_id:chatId,...payload})});
      const data=await response.json().catch(()=>({ok:false,reason:'Некорректный ответ сервера.'}));
      if(!response.ok||!data?.ok)throw new Error(data.reason||'Действие не выполнено.');
      toast(data.message||'Готово.');tg?.HapticFeedback?.notificationOccurred?.('success');
      await load(true);setTimeout(()=>document.getElementById('refreshButton')?.click(),100);
      return data;
    }catch(error){toast(error.message||'Действие не выполнено.','error');tg?.HapticFeedback?.notificationOccurred?.('error');return null}
    finally{busy=false}
  }

  const q=()=>state?.theft_quest_v163||{cases:[]};
  const statusLabel=value=>({investigation:'ИДЁТ СЛЕДСТВИЕ',caught:'ВИНОВНИК ПОЙМАН',escaped:'КАЗНОКРАД СКРЫЛСЯ',prosecution_failed:'ОБВИНЕНИЕ ПРОВАЛЕНО'})[value]||String(value||'');
  const taskStatus=value=>({pending:'ОЖИДАЕТ',completed:'ЗАВЕРШЕНО',failed:'НИЗКАЯ ТОЧНОСТЬ'})[value]||String(value||'');

  function progress(caseItem){
    return `<div class="quest-stage-grid">${(caseItem.tasks||[]).map(task=>`<article class="quest-stage ${esc(task.status)} ${task.unlocked?'':'locked'}"><span>${esc(task.icon)}</span><div><b>${esc(task.title)}</b><small>${esc(taskStatus(task.status))}${task.assignee_name?` · ${esc(task.assignee_name)}`:''}</small></div>${task.status==='completed'?'<i>✓</i>':task.status==='failed'?'<i>!</i>':task.unlocked?'<i>→</i>':'<i>🔒</i>'}</article>`).join('')}</div>`;
  }

  function clues(caseItem){
    const items=caseItem.clues||[];
    if(!items.length)return '<div class="quest-empty"><span>🔎</span><b>Улик пока нет</b><small>Минфин и Счётная палата должны начать проверку.</small></div>';
    return `<div class="quest-clues">${items.map(item=>`<article class="quest-clue ${esc(item.confidence)}"><span>${esc(item.icon||'🔎')}</span><div><b>${esc(item.title||'Улика')}</b><p>${esc(item.text)}</p><small>${item.created_at?dt(item.created_at):''}</small></div></article>`).join('')}</div>`;
  }

  function choiceTask(caseItem,task){
    const options=task.task?.options||[];
    return `<article class="quest-work"><div class="quest-work-head"><span>${esc(task.icon)}</span><div><small>ТВОЙ ЭТАП</small><h3>${esc(task.title)}</h3></div></div>${!task.unlocked?'<div class="quest-lock">Сначала дождись материалов предыдущей структуры.</div>':!task.available?`<div class="quest-lock">Повторная попытка через ${esc(task.remaining||'несколько минут')}.</div>`:`<form data-quest-choice="${esc(caseItem.theft_id)}" data-office="${esc(task.office_key)}"><h4>${esc(task.task?.question||'Проведи проверку')}</h4><p>${esc(task.task?.description||'')}</p><div class="quest-option-list">${options.map(option=>`<label><input type="radio" name="answer" value="${esc(option.id)}"><span>${esc(option.text)}</span></label>`).join('')}</div><button type="submit">🔍 ЗАФИКСИРОВАТЬ РЕЗУЛЬТАТ</button></form>`}</article>`;
  }

  function auditTask(caseItem,task){
    const records=task.task?.records||[];
    return `<article class="quest-work"><div class="quest-work-head"><span>${esc(task.icon)}</span><div><small>ТВОЙ ЭТАП</small><h3>${esc(task.title)}</h3></div></div>${!task.unlocked?'<div class="quest-lock">Этап пока закрыт.</div>':!task.available?`<div class="quest-lock">Повторная попытка через ${esc(task.remaining||'несколько минут')}.</div>`:`<form data-quest-choice="${esc(caseItem.theft_id)}" data-office="auditor"><h4>${esc(task.task?.question||'Найди подделку')}</h4><p>${esc(task.task?.description||'')}</p><div class="quest-record-list">${records.map(record=>`<label><input type="radio" name="answer" value="${esc(record.id)}"><span><b>${dt(record.time)}</b><em>${fmt(record.amount)} влияния</em><code>${esc(record.signature)}</code><small>${esc(record.note)}</small></span></label>`).join('')}</div><button type="submit">🧾 ПЕРЕДАТЬ АУДИТОРСКИЙ ВЫВОД</button></form>`}</article>`;
  }

  function suspectCard(item,selectable=false,radio=false){
    const input=selectable?`<input type="${radio?'radio':'checkbox'}" name="suspect_id${radio?'':'s'}" value="${item.user_id}">`:'';
    const tags=[item.had_access?'имел доступ':'доступа не было',`активность: ${item.activity}`,`баланс: ${item.balance_trace}`];
    if(item.route_link===true)tags.push('совпадает денежный маршрут');
    if(item.route_link===false)tags.push('маршрут не совпал');
    if(item.audit_link===true)tags.push('совпала подпись журнала');
    if(item.audit_link===false)tags.push('подпись не совпала');
    if(item.anomaly)tags.push('обнаружен подозрительный след');
    return `<label class="quest-suspect">${input}<span class="quest-code">${esc(item.code)}</span><span class="quest-suspect-main"><b>${esc(item.name)}${item.username?` · @${esc(item.username)}`:''}</b><small>${esc((item.offices||[]).join(', ')||'без должности')}</small><em>${tags.map(tag=>`<i>${esc(tag)}</i>`).join('')}</em></span><strong>${fmt(item.risk)}%</strong></label>`;
  }

  function oversightTask(caseItem,task){
    return `<article class="quest-work"><div class="quest-work-head"><span>${esc(task.icon)}</span><div><small>ТВОЙ ЭТАП</small><h3>${esc(task.title)}</h3></div></div>${!task.unlocked?'<div class="quest-lock">Нужен хотя бы один вывод Минфина или Счётной палаты.</div>':`<form data-quest-oversight="${esc(caseItem.theft_id)}"><h4>Сформируй приоритетный круг</h4><p>Выбери одного или двух участников. Полные балансы скрыты — показаны только признаки изменения.</p><div class="quest-suspects">${(task.suspects||[]).map(item=>suspectCard(item,true,false)).join('')}</div><button type="submit">🚨 ПЕРЕДАТЬ СПИСОК ПРОКУРАТУРЕ</button></form>`}</article>`;
  }

  function prosecutorTask(caseItem,task){
    const evidence=(task.clues||[]).filter(item=>['finance','auditor','oversight'].includes(item.office_key));
    return `<article class="quest-work prosecutor"><div class="quest-work-head"><span>${esc(task.icon)}</span><div><small>ФИНАЛЬНЫЙ ЭТАП</small><h3>${esc(task.title)}</h3></div></div>${!task.unlocked?'<div class="quest-lock">Обвинение откроется после завершения Минфина, Счётной палаты и Надзора.</div>':!task.available?`<div class="quest-lock">Повторное обвинение доступно через ${esc(task.remaining||'15 минут')}.</div>`:`<form data-quest-accuse="${esc(caseItem.theft_id)}"><h4>Собери обвинительное заключение</h4><p>Выбери одного подозреваемого и приложи материалы всех трёх структур. Ошибка принесёт компенсацию обвинённому.</p><div class="quest-suspects radio">${(task.suspects||[]).map(item=>suspectCard(item,true,true)).join('')}</div><div class="quest-evidence-checks">${['finance','auditor','oversight'].map(key=>{const item=evidence.find(value=>value.office_key===key);const title={finance:'Материалы Минфина',auditor:'Аудиторское заключение',oversight:'Список Надзора'}[key];return `<label><input type="checkbox" name="evidence" value="${key}"><span><b>${title}</b><small>${esc(item?.text||'Материал завершённого этапа')}</small></span></label>`}).join('')}</div><button class="danger" type="submit">⚖️ ПРЕДЪЯВИТЬ ОБВИНЕНИЕ</button></form>`}</article>`;
  }

  function myWork(caseItem){
    const tasks=caseItem.my_tasks||[];
    if(!tasks.length)return '';
    return `<div class="quest-work-list">${tasks.map(task=>{
      if(['completed','failed'].includes(task.status))return `<article class="quest-work done"><div class="quest-work-head"><span>${esc(task.icon)}</span><div><small>ТВОЙ ЭТАП ЗАВЕРШЁН</small><h3>${esc(task.title)}</h3></div><i>✓</i></div></article>`;
      if(task.office_key==='finance')return choiceTask(caseItem,task);
      if(task.office_key==='auditor')return auditTask(caseItem,task);
      if(task.office_key==='oversight')return oversightTask(caseItem,task);
      return prosecutorTask(caseItem,task);
    }).join('')}</div>`;
  }

  function thiefPanel(caseItem){
    const panel=caseItem.thief_panel;if(!panel)return '';
    const frameTargets=(panel.targets||[]).map(item=>`<option value="${item.user_id}">${esc(item.code)} · ${esc(item.name)}</option>`).join('');
    return `<article class="quest-thief"><div class="quest-work-head"><span>🕶</span><div><small>СКРЫТО ОТ СЛЕДСТВИЯ</small><h3>Сокрытие следов</h3></div></div><p>Можно применить не больше ${panel.max_actions} действий. Их стоимость вычитается из будущей добычи.</p><div class="quest-loot"><small>ОСТАНЕТСЯ ПРИ ПОБЕГЕ</small><b>${fmt(panel.loot_remaining)}</b></div><div class="quest-cover-grid">${(panel.actions||[]).filter(item=>item.key!=='frame_suspect').map(item=>`<button type="button" data-cover-action="${esc(item.key)}" data-theft="${esc(caseItem.theft_id)}" ${item.available&&panel.used.length<panel.max_actions?'':'disabled'}><b>${esc(item.title)}</b><small>−${fmt(item.cost_percent)}% добычи</small></button>`).join('')}</div><form data-cover-frame="${esc(caseItem.theft_id)}"><label>КОГО ПОДСТАВИТЬ<select name="target_id">${frameTargets}</select></label><button type="submit" ${(panel.actions||[]).find(item=>item.key==='frame_suspect')?.available&&panel.used.length<panel.max_actions?'':'disabled'}>🎭 СОЗДАТЬ ЛОЖНЫЙ СЛЕД · −15%</button></form></article>`;
  }

  function delegation(caseItem){
    if(!caseItem.can_delegate||!(caseItem.delegate_tasks||[]).length)return '';
    const roles=(caseItem.delegate_tasks||[]).map(key=>{const role=(q().roles||[]).find(item=>item.key===key);return `<option value="${esc(key)}">${esc(role?.icon||'🏛')} ${esc(role?.title||key)}</option>`}).join('');
    const people=(caseItem.delegate_targets||[]).map(item=>`<option value="${item.user_id}">${esc(item.name)}</option>`).join('');
    return `<details class="quest-delegate"><summary>🎖 Назначить временного следователя</summary><form data-quest-delegate="${esc(caseItem.theft_id)}"><label>ЭТАП<select name="office_key">${roles}</select></label><label>УЧАСТНИК<select name="target_id">${people}</select></label><button type="submit">НАЗНАЧИТЬ</button></form></details>`;
  }

  function caseMarkup(item){
    const active=item.status==='investigation';
    return `<article class="quest-case ${esc(item.status)}"><header><div class="quest-case-icon">${active?'🕵️':item.status==='caught'?'🚨':'🕶'}</div><div><small>УГОЛОВНОЕ ДЕЛО №${String(item.case_no).padStart(4,'0')}</small><h2>Хищение ${fmt(item.amount)} влияния</h2><p>${fmt(item.percent)}% казны · подозреваемых ${fmt(item.suspect_count)}</p></div><span class="quest-status">${esc(statusLabel(item.status))}</span></header>${active?`<div class="quest-time"><span>До исчезновения следов</span><b>${esc(item.remaining)}</b></div>${progress(item)}<section class="quest-section"><div><small>ДОСКА СЛЕДСТВИЯ</small><h3>Найденные улики</h3></div>${clues(item)}</section>${myWork(item)}${thiefPanel(item)}${delegation(item)}`:`<div class="quest-result"><span>${item.status==='caught'?'Дело раскрыто, виновник наказан и средства возвращены.':'Следствие не успело доказать обвинение.'}</span><small>Открыто ${dt(item.created_at)}</small></div>`}</article>`;
  }

  function render(){
    const root=ensureRoot();if(!root)return;
    document.querySelectorAll('#shadowTheftCasesV153,.v153-case-list .v153-case.theft').forEach(node=>node.style.display='none');
    const cases=q().cases||[];
    root.innerHTML=`<div class="quest-heading"><div><small>REALITY 163 · ДЕТЕКТИВНАЯ СИСТЕМА</small><h2>Уголовные дела казны</h2><p>Каждая структура получает собственную часть расследования. Полные балансы участников никому не раскрываются.</p></div><span>● LIVE</span></div>${cases.length?`<div class="quest-case-list">${cases.map(caseMarkup).join('')}</div>`:'<div class="quest-empty large"><span>🗄</span><b>Открытых уголовных дел нет</b><small>После подозрительного вывода из казны здесь появится общий детективный квест.</small></div>'}`;
  }

  document.addEventListener('submit',event=>{
    const choice=event.target.closest?.('[data-quest-choice]');
    if(choice){event.preventDefault();const answer=new FormData(choice).get('answer');if(answer===null)return toast('Выбери вариант ответа.','error');action('quest_task',{theft_id:choice.dataset.questChoice,office_key:choice.dataset.office,answer:String(answer)});return}
    const oversight=event.target.closest?.('[data-quest-oversight]');
    if(oversight){event.preventDefault();const selected=[...new FormData(oversight).getAll('suspect_ids')].map(Number);if(selected.length<1||selected.length>2)return toast('Выбери одного или двух подозреваемых.','error');action('quest_task',{theft_id:oversight.dataset.questOversight,office_key:'oversight',suspect_ids:selected},'Передать выбранный круг подозреваемых прокуратуре?');return}
    const accusation=event.target.closest?.('[data-quest-accuse]');
    if(accusation){event.preventDefault();const form=new FormData(accusation),suspect=Number(form.get('suspect_id')||0),evidence=form.getAll('evidence').map(String);if(!suspect)return toast('Выбери обвиняемого.','error');if(evidence.length<3)return toast('Приложи материалы всех трёх структур.','error');action('quest_accuse',{theft_id:accusation.dataset.questAccuse,suspect_id:suspect,evidence_keys:evidence},'Это финальное обвинение. Ошибка даст подозреваемому компенсацию. Продолжить?');return}
    const frame=event.target.closest?.('[data-cover-frame]');
    if(frame){event.preventDefault();const target=Number(new FormData(frame).get('target_id')||0);action('quest_cover',{theft_id:frame.dataset.coverFrame,action_key:'frame_suspect',target_id:target},'Создать ложный след против выбранного участника?');return}
    const delegate=event.target.closest?.('[data-quest-delegate]');
    if(delegate){event.preventDefault();const data=Object.fromEntries(new FormData(delegate).entries());action('quest_delegate',{theft_id:delegate.dataset.questDelegate,office_key:data.office_key,target_id:Number(data.target_id)},'Назначить временного следователя на этот этап?')}
  },true);

  document.addEventListener('click',event=>{
    const cover=event.target.closest?.('[data-cover-action]');
    if(cover){action('quest_cover',{theft_id:cover.dataset.theft,action_key:cover.dataset.coverAction},'Потратить часть будущей добычи на сокрытие следов?');return}
    if(event.target.closest?.('[data-tab="powers"],#refreshButton'))setTimeout(()=>load(true),80);
  },true);

  document.addEventListener('change',event=>{
    if(!event.target.matches?.('[data-quest-oversight] input[type="checkbox"]'))return;
    const form=event.target.closest('form');const checked=form?.querySelectorAll('input[type="checkbox"]:checked')||[];
    if(checked.length>2){event.target.checked=false;toast('Надзор может выбрать максимум двух подозреваемых.','error')}
  },true);

  document.addEventListener('visibilitychange',()=>{if(!document.hidden)load(true)});
  window.addEventListener('focus',()=>load(true));
  ensureRoot();load(false);clearInterval(timer);timer=setInterval(()=>{if(!document.hidden)load(true)},3000);
})();
