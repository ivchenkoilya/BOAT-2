(()=>{
  'use strict';
  if(window.__governmentRolePermissionsV148)return;
  window.__governmentRolePermissionsV148=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'X-Telegram-Init-Data':tg?.initData||''};
  const roleActions={
    president:['decree','amnesty','appointment','security_meeting','emergency'],
    chair:['extend_bill','return_bill','no_confidence'],
    deputy:['amendment','inspection_request'],
    finance:['budget_report','tax_refund','debtors_report'],
    oversight:['warning','open_case','inspection_request'],
    supreme_court:['court_case','court_ruling','court_compensation','case_refer'],
    prosecutor:['investigation','suspend_official','treasury_audit','tax_audit','budget_audit','case_refer'],
    central_bank:['economic_policy','economic_mode','economic_report'],
    auditor:['treasury_audit','tax_audit','budget_audit'],
    cec:['cec_election','recount','disqualify'],
    ombudsman:['complaints','protection','public_appeal','case_refer'],
    security:['security_meeting','emergency','security_report'],
    press:['statement','poll','daily_brief']
  };
  let offices=[];
  let allowed=new Set();
  let frame=0;

  const escapeHtml=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));

  function toast(text){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=text;
    node.className='toast show error';
    clearTimeout(node.__roleTimer);
    node.__roleTimer=setTimeout(()=>node.className='toast',3600);
  }

  function rebuildAllowed(){
    allowed=new Set();
    offices.forEach(role=>(roleActions[role]||[]).forEach(action=>allowed.add(action)));
  }

  function officeTitle(key){
    const fallback={
      president:'Президент реальности',chair:'Председатель Госдумы',deputy:'Депутат Госдумы',
      finance:'Министр финансов',oversight:'Глава Надзора',supreme_court:'Председатель Верховного суда',
      prosecutor:'Генеральный прокурор',central_bank:'Председатель Центрального банка',
      auditor:'Глава Счётной палаты',cec:'Председатель ЦИК',ombudsman:'Уполномоченный по правам участников',
      security:'Секретарь Совета безопасности',press:'Пресс-секретарь государства'
    };
    return fallback[key]||key;
  }

  function renderAccessBanner(){
    const host=document.getElementById('myPowerCards');
    if(!host)return;
    let banner=document.getElementById('roleAccessBannerV148');
    if(!banner){
      banner=document.createElement('article');
      banner.id='roleAccessBannerV148';
      banner.className='role-access-banner-v148';
      host.insertAdjacentElement('beforebegin',banner);
    }
    const roles=offices.length?offices.map(key=>`<span>${escapeHtml(officeTitle(key))}</span>`).join(''):'<span class="none">Государственной должности нет</span>';
    const markup=`<div class="role-access-icon-v148">🔐</div><div><small>ПЕРСОНАЛЬНЫЙ ДОСТУП</small><b>Активны только полномочия вашей должности</b><div class="role-access-list-v148">${roles}</div><p>Статус владельца бота не даёт президентские или иные государственные права. Для управления системой используется отдельный админ-центр.</p></div>`;
    if(banner.innerHTML!==markup)banner.innerHTML=markup;
  }

  function applyAccess(){
    const brand=document.querySelector('.brand small');
    if(brand&&brand.textContent!=='REALITY 148')brand.textContent='REALITY 148';
    renderAccessBanner();
    document.querySelectorAll('.power-card').forEach(card=>{
      card.classList.toggle('role-current-v148',Boolean(card.querySelector('.power-action')));
    });
    document.querySelectorAll('[data-power-action]').forEach(button=>{
      const key=String(button.dataset.powerAction||'');
      const available=allowed.has(key);
      button.classList.toggle('role-allowed-v148',available);
      button.classList.toggle('role-locked-v148',!available);
      button.disabled=!available;
      button.setAttribute('aria-disabled',available?'false':'true');
      if(!available)button.title='Недоступно для вашей государственной должности';
    });
  }

  function scheduleApply(){
    cancelAnimationFrame(frame);
    frame=requestAnimationFrame(applyAccess);
  }

  async function loadRoles(){
    if(!chatId)return;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}`,{cache:'no-store',headers});
      const data=await response.json();
      if(!response.ok||!data?.ok)return;
      offices=Array.isArray(data?.role_access?.offices)?data.role_access.offices:Array.isArray(data?.user?.offices)?data.user.offices:[];
      rebuildAllowed();
      scheduleApply();
    }catch(_error){}
  }

  document.addEventListener('click',event=>{
    const button=event.target.closest?.('[data-power-action]');
    if(!button)return;
    const key=String(button.dataset.powerAction||'');
    if(allowed.has(key))return;
    event.preventDefault();
    event.stopImmediatePropagation();
    toast('Это полномочие недоступно для вашей текущей государственной должности.');
  },true);

  const observer=new MutationObserver(scheduleApply);
  observer.observe(document.documentElement,{subtree:true,childList:true});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)loadRoles();});
  window.addEventListener('focus',loadRoles);
  loadRoles();
  scheduleApply();
})();
