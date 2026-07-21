(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const $=id=>document.getElementById(id);
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
  let state=null,busy=false,toastTimer=null,refreshTimer=null;

  function toast(text,type='success'){
    const node=$('toast');if(!node)return;
    node.textContent=text;node.className=`toast show ${type}`;
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>node.className='toast',3500);
  }

  async function api(path,options={}){
    const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),15000);
    try{
      const response=await fetch(path,{cache:'no-store',...options,signal:controller.signal,headers:{...headers,...(options.headers||{})}});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
      return data;
    }catch(error){if(error.name==='AbortError')throw new Error('Сервер долго не отвечает.');throw error}
    finally{clearTimeout(timeout)}
  }

  async function load(silent=false){
    if(busy&&!silent)return;
    try{
      state=await api(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}`);
      render();
    }catch(error){if(!silent)toast(error.message||'Не удалось загрузить полномочия.','error')}
  }

  async function action(name,payload={},confirmation=''){
    if(busy)return;
    if(confirmation&&!confirm(confirmation))return;
    busy=true;
    try{
      const data=await api('/government-v128/api/action',{method:'POST',body:JSON.stringify({action:name,chat_id:chatId,...payload})});
      closeModal();toast(data.message||'Полномочие исполнено.');tg?.HapticFeedback?.notificationOccurred?.('success');
      await load(true);$('refreshButton')?.click();
    }catch(error){toast(error.message||'Действие не выполнено.','error');tg?.HapticFeedback?.notificationOccurred?.('error')}
    finally{busy=false}
  }

  function institutions(){return state?.institutions||{}}
  function users(selected=0){return (state?.eligible_users||[]).map(user=>`<option value="${user.user_id}" ${Number(selected)===Number(user.user_id)?'selected':''}>${esc(user.name)} · ⭐ ${fmt(user.career_points)}</option>`).join('')}
  function activeBills(){return (state?.bills||[]).filter(b=>['voting','president_review','vetoed'].includes(b.status))}
  function billOptions(){return activeBills().map(b=>`<option value="${esc(b.bill_id)}">№${b.number} · ${esc(b.title)} · ${esc(b.status)}</option>`).join('')}
  function electionOptions(){return (state?.elections||[]).filter(e=>['nomination','voting','resolved'].includes(e.phase)).map(e=>`<option value="${esc(e.election_id)}">${esc(e.office_title)} · ${esc(e.phase)}</option>`).join('')}
  function candidateOptions(){
    const options=[];
    for(const election of (state?.elections||[]).filter(e=>['nomination','voting'].includes(e.phase))){
      for(const candidate of election.candidates||[])options.push(`<option value="${esc(election.election_id)}|${candidate.user_id}">${esc(election.office_title)} · ${esc(candidate.name)}</option>`);
    }
    return options.join('');
  }
  function officeOptions(includeElected=false){
    const allowed=includeElected?Object.keys(state?.office_specs||{}):['finance','oversight','supreme_court','prosecutor','central_bank','auditor','cec','ombudsman','security','press'];
    return allowed.filter(key=>state?.office_specs?.[key]).map(key=>`<option value="${key}">${state.office_specs[key].emoji} ${esc(state.office_specs[key].title)}</option>`).join('');
  }
  function caseOptions(filter=''){
    return (institutions().cases||[]).filter(item=>!filter||item.status===filter||item.institution===filter).map(item=>`<option value="${esc(item.case_id)}">${esc(item.title)} · ${esc(item.status)}</option>`).join('');
  }
  function field(label,body){return `<div class="field"><label>${label}</label>${body}</div>`}
  function input(name,placeholder='',type='text',value=''){return `<input name="${name}" type="${type}" value="${esc(value)}" placeholder="${esc(placeholder)}">`}
  function textarea(name,placeholder=''){return `<textarea name="${name}" placeholder="${esc(placeholder)}"></textarea>`}
  function select(name,options){return `<select name="${name}">${options}</select>`}

  function actionForm(key){
    const target=field('УЧАСТНИК',select('target_user_id',users()));
    const reason=field('ОСНОВАНИЕ',textarea('reason','Укажи причину и обстоятельства'));
    const title=field('НАЗВАНИЕ',input('title','Краткое название дела'));
    const description=field('ОПИСАНИЕ',textarea('description','Факты, основания и требуемое решение'));
    const bill=field('ЗАКОНОПРОЕКТ',select('bill_id',billOptions()));
    const noFields=new Set(['budget_report','debtors_report','treasury_audit','tax_audit','budget_audit','economic_report','daily_brief']);
    if(noFields.has(key))return '<p class="hint">Действие будет выполнено сразу и опубликовано в беседе.</p>';
    if(key==='decree')return field('ТЕКСТ УКАЗА',textarea('text','Распоряжение Президента реальности'));
    if(key==='amnesty')return target+reason;
    if(key==='appointment')return field('ДОЛЖНОСТЬ',select('office_key',officeOptions(false)))+target+reason;
    if(key==='extend_bill')return bill;
    if(key==='return_bill')return bill+reason;
    if(['no_confidence','inspection_request','open_case','court_case','investigation'].includes(key))return title+target+description;
    if(key==='amendment')return bill+field('ТЕКСТ ПОПРАВКИ',textarea('text','Предлагаемая новая формулировка'));
    if(key==='tax_refund')return target+field('СУММА',input('amount','До 10 000','number','1000'))+reason;
    if(key==='warning')return target+reason;
    if(key==='court_ruling')return field('СУДЕБНОЕ ДЕЛО',select('case_id',caseOptions()))+field('РЕШЕНИЕ',select('decision','<option value="lawful">✅ Признать законным</option><option value="unlawful">❌ Признать незаконным</option><option value="dismissed">⚪ Прекратить дело</option>'))+field('МОТИВИРОВКА',textarea('text','Почему суд принял это решение'));
    if(key==='court_compensation')return field('ДЕЛО С НЕЗАКОННЫМ РЕШЕНИЕМ',select('case_id',caseOptions()))+target+field('КОМПЕНСАЦИЯ',input('amount','До 5 000','number','1000'));
    if(key==='suspend_official')return target+field('ДОЛЖНОСТЬ',select('office_key',officeOptions(true)))+reason;
    if(key==='economic_policy')return field('КОМИССИЯ ПЕРЕВОДОВ, %',input('transfer_fee_percent','0–10%','number',String((institutions().policy?.transfer_fee_percent)||0)))+field('МАКСИМАЛЬНАЯ СТАВКА',input('max_wager','Не меньше 100','number',String(institutions().policy?.max_wager||50000)))+field('ЛИМИТ НОВОГО ЗАЙМА',input('loan_limit','Не меньше 1 000','number',String(institutions().policy?.loan_limit||1000000)));
    if(key==='economic_mode')return field('РЕЖИМ',select('mode','<option value="stability">🟢 Стабильность</option><option value="growth">📈 Рост</option><option value="crisis">📉 Кризис</option><option value="freeze">🧊 Заморозка</option><option value="inflation">🔥 Инфляция</option>'))+field('СРОК',select('duration','<option value="3600">1 час</option><option value="10800">3 часа</option><option value="21600" selected>6 часов</option><option value="43200">12 часов</option><option value="86400">24 часа</option>'));
    if(key==='cec_election')return field('ДОЛЖНОСТЬ',select('office_key','<option value="president">🦅 Президент</option><option value="deputy">🗳 Депутаты</option><option value="chair">🏛 Председатель Госдумы</option>'));
    if(key==='recount')return field('ВЫБОРЫ',select('election_id',electionOptions()));
    if(key==='disqualify')return field('КАНДИДАТ',select('candidate_pair',candidateOptions()))+reason;
    if(key==='complaints')return '<p class="hint">Очередь жалоб находится ниже. Выбери дело и передай его в суд, прокуратуру или закрой.</p>';
    if(key==='protection')return target+reason;
    if(key==='public_appeal'||key==='statement'||key==='security_report')return field('ТЕКСТ',textarea('text','Официальный текст для публикации'));
    if(key==='security_meeting')return reason;
    if(key==='emergency')return field('СРОК',select('duration','<option value="3600">1 час</option><option value="10800" selected>3 часа</option><option value="21600">6 часов</option>'))+reason;
    if(key==='poll')return field('ВОПРОС',input('question','Вопрос для участников'))+field('ВАРИАНТЫ',textarea('options','Каждый вариант с новой строки'));
    return reason;
  }

  function openModal(button){
    const key=button.dataset.powerAction;const title=button.dataset.powerTitle||key;const office=button.dataset.officeTitle||'';
    $('powerModalTitle').textContent=title;$('powerModalOffice').textContent=office;$('powerForm').dataset.action=key;
    $('powerFormFields').innerHTML=actionForm(key);$('powerModal').classList.add('open');document.body.style.overflow='hidden';
  }
  function closeModal(){$('powerModal')?.classList.remove('open');document.body.style.overflow=''}

  function officeHolder(key){return (state?.offices||[]).find(item=>item.office_key===key)}
  function renderStructures(){
    const specs=state?.office_specs||{};
    const keys=['supreme_court','prosecutor','central_bank','auditor','cec','ombudsman','security','press'];
    $('institutionGrid').innerHTML=keys.map(key=>{
      const spec=specs[key];if(!spec)return '';
      const holder=officeHolder(key);return `<article class="institution-card ${holder?'active':''}"><span>${spec.emoji}</span><b>${esc(spec.title)}</b><small>${holder?`${esc(holder.name)} · ещё ${esc(holder.remaining)}`:`Свободно · порог ${fmt(spec.threshold)} карьеры`}</small></article>`;
    }).join('');
  }

  function renderPowerCards(){
    const grouped={};for(const item of institutions().my_powers||[])(grouped[item.office_key]??=[]).push(item);
    const entries=Object.entries(grouped);
    $('myPowerCards').innerHTML=entries.length?entries.map(([office,actions])=>{
      const spec=state.office_specs?.[office]||{emoji:'🏛',title:office};
      return `<article class="power-card"><div class="power-card-head"><span>${spec.emoji}</span><div><b>${esc(spec.title)}</b><small>Личная панель управления · действия записываются в журнал</small></div></div><div class="power-actions">${actions.map(item=>`<button class="power-action" data-power-action="${item.key}" data-power-title="${esc(item.title)}" data-office-title="${esc(item.office_title)}"><span>${item.emoji}</span><b>${esc(item.title)}</b><small>${esc(item.hint)}</small></button>`).join('')}</div></article>`;
    }).join(''):'<article class="power-card locked"><div class="power-card-head"><span>🔒</span><div><b>Государственных полномочий нет</b><small>Спецкнопки появятся после избрания или назначения на должность</small></div></div></article>';
  }

  function renderPolicy(){
    const p=institutions().policy||{};
    const mode={stability:'🟢 Стабильность',growth:'📈 Рост',crisis:'📉 Кризис',freeze:'🧊 Заморозка',inflation:'🔥 Инфляция'}[p.economic_mode]||p.economic_mode;
    $('powerPolicy').innerHTML=`<article class="panel"><div class="panel-title"><span>🏦</span><div><b>Действующая экономическая политика</b><small>Эти ограничения применяются сервером автоматически</small></div></div><div class="policy-grid"><div class="policy-item"><small>РЕЖИМ</small><b>${esc(mode)}</b></div><div class="policy-item"><small>КОМИССИЯ</small><b>${p.transfer_fee_percent||0}%</b></div><div class="policy-item"><small>МАКС. СТАВКА</small><b>${fmt(p.max_wager)}</b></div><div class="policy-item"><small>ЛИМИТ ЗАЙМА</small><b>${fmt(p.loan_limit)}</b></div></div>${p.emergency?'<p class="hint">⚠️ Действует чрезвычайный режим Совета безопасности.</p>':''}</article>`;
  }

  function caseActions(item){
    const offices=institutions().my_offices||[];const admin=institutions().is_admin;
    if(!(admin||offices.some(key=>['ombudsman','prosecutor','supreme_court'].includes(key))))return '';
    return `<div class="case-actions"><button data-case-refer="prosecutor" data-case="${esc(item.case_id)}">🛡 В прокуратуру</button><button data-case-refer="supreme_court" data-case="${esc(item.case_id)}">⚖️ В суд</button><button data-case-refer="closed" data-case="${esc(item.case_id)}">✅ Закрыть</button></div>`;
  }
  function renderCases(){
    const cases=institutions().cases||[];
    $('powerCases').innerHTML=cases.length?cases.map(item=>`<article class="case-card"><div class="case-card-head"><span><b>📁 ${esc(item.title)}</b><small>${esc(item.institution)} · ${esc(item.status)} · ${date(item.created_at)}</small></span><span class="badge ${item.status==='open'?'gold':item.status==='closed'?'green':''}">${esc(item.case_type)}</span></div><p>${esc(item.description)}</p>${caseActions(item)}</article>`).join(''):'<div class="empty">Государственных дел и жалоб пока нет.</div>';
  }
  function renderLog(){
    const logs=institutions().power_log||[];
    $('powerLog').innerHTML=logs.length?`<div class="log-list">${logs.map(item=>`<div class="log-item"><span><b>${esc(item.title)}</b><small>${esc(state.office_specs?.[item.office_key]?.title||item.office_key)} · ${date(item.created_at)}${item.detail?` · ${esc(item.detail)}`:''}</small></span><strong>${state.office_specs?.[item.office_key]?.emoji||'🏛'}</strong></div>`).join('')}</div>`:'<div class="empty">Журнал полномочий пока пуст.</div>';
  }

  function render(){
    if(!state?.institutions)return;
    const offices=institutions().my_offices||[];
    $('powerHero').innerHTML=`<article class="powers-hero"><div class="powers-head"><span>${offices.length?(state.office_specs?.[offices[0]]?.emoji||'🏛'):'🔐'}</span><div><small>REALITY 128 · ПАНЕЛЬ ПОЛНОМОЧИЙ</small><b>${offices.length?offices.map(key=>state.office_specs?.[key]?.title||key).join(' · '):'Гражданский доступ'}</b></div></div><div class="powers-summary"><div><small>ДОСТУПНЫЕ ДЕЙСТВИЯ</small><b>${(institutions().my_powers||[]).length}</b></div><div><small>ОТКРЫТЫЕ ДЕЛА</small><b>${(institutions().cases||[]).filter(x=>x.status==='open'||x.status==='referred').length}</b></div></div></article>`;
    renderStructures();renderPowerCards();renderPolicy();renderCases();renderLog();
  }

  function payloadFromForm(form){
    const data=Object.fromEntries(new FormData(form).entries());const actionKey=form.dataset.action;
    if(actionKey==='economic_policy')data.transfer_fee_bps=Math.round(Number(data.transfer_fee_percent||0)*100);
    for(const key of ['target_user_id','amount','duration','max_wager','loan_limit'])if(key in data)data[key]=Number(data[key]||0);
    if(actionKey==='disqualify'){
      const [electionId,candidateId]=String(data.candidate_pair||'|0').split('|');data.election_id=electionId;data.candidate_id=Number(candidateId||0);delete data.candidate_pair;
    }
    if(actionKey==='poll')data.options=String(data.options||'').split(/\n+/).map(x=>x.trim()).filter(Boolean);
    return data;
  }

  document.addEventListener('click',event=>{
    const power=event.target.closest('[data-power-action]');if(power){openModal(power);return}
    if(event.target.closest('[data-power-close]')){closeModal();return}
    if(event.target=== $('powerModal')){closeModal();return}
    const refer=event.target.closest('[data-case-refer]');if(refer){action('case_refer',{case_id:refer.dataset.case,destination:refer.dataset.caseRefer},'Изменить направление государственного дела?');return}
    if(event.target.closest('#refreshButton'))load(true);
  });

  document.addEventListener('submit',event=>{
    if(event.target.id==='powerForm'){
      event.preventDefault();const actionKey=event.target.dataset.action;const payload=payloadFromForm(event.target);
      action(actionKey,payload,'Подтвердить применение государственного полномочия?');return;
    }
    if(event.target.id==='citizenComplaintForm'){
      event.preventDefault();const data=Object.fromEntries(new FormData(event.target).entries());
      action('submit_complaint',{title:data.title||'',description:data.description||'',target_user_id:Number(data.target_user_id||0)},'Зарегистрировать официальную жалобу?');return;
    }
  });

  document.addEventListener('visibilitychange',()=>{if(!document.hidden)load(true)});
  load();clearInterval(refreshTimer);refreshTimer=setInterval(()=>{if(!document.hidden&&!busy)load(true)},30000);
})();