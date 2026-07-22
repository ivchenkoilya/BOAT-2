(()=>{
  'use strict';
  if(window.__governmentUiHotfixV170)return;
  window.__governmentUiHotfixV170=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  let state=null;
  let loading=false;

  function ensureOversightAssets(){
    let link=document.querySelector('link[href*="oversight-deputy-v167.css"]');
    if(!link){
      link=document.createElement('link');
      link.rel='stylesheet';
      document.head.appendChild(link);
    }
    link.href='/government-v167/oversight-deputy-v167.css?v=170';

    if(!window.__oversightDeputyV167&&!document.querySelector('script[src*="oversight-deputy-v167.js"]')){
      const script=document.createElement('script');
      script.src='/government-v167/oversight-deputy-v167.js?v=170';
      script.defer=true;
      document.body.appendChild(script);
    }
  }

  function openDeputyPanel(){
    document.querySelector('[data-tab="powers"]')?.click();
    setTimeout(()=>{
      placeDeputyPanel();
      document.getElementById('oversightDeputyV167')?.scrollIntoView({behavior:'smooth',block:'start'});
    },260);
  }

  function placeDeputyPanel(){
    const panel=document.getElementById('oversightDeputyV167');
    const powers=document.querySelector('.screen[data-screen="powers"]');
    const cards=document.getElementById('myPowerCards');
    if(!panel||!powers||!cards)return false;
    if(panel.previousElementSibling!==cards)cards.insertAdjacentElement('afterend',panel);
    panel.classList.add('od-mounted-powers-v170');
    document.getElementById('oversightDeputyQuickV169')?.remove();
    return true;
  }

  function patchAppointmentSelect(){
    const select=document.querySelector('#powerFormFields select[name="office_key"]');
    if(!select||select.querySelector('option[value="oversight_deputy"]'))return;
    const spec=state?.office_specs?.oversight_deputy||{
      emoji:'🕵️',
      title:'Заместитель главы Надзора за гондонами',
    };
    const option=document.createElement('option');
    option.value='oversight_deputy';
    option.textContent=`${spec.emoji||'🕵️'} ${spec.title}`;
    const oversight=select.querySelector('option[value="oversight"]');
    if(oversight)oversight.insertAdjacentElement('afterend',option);
    else select.appendChild(option);
  }

  function deputyCard(){
    const grid=document.getElementById('institutionGrid');
    if(!grid||!state)return;
    document.getElementById('oversightDeputyInstitutionV169')?.remove();
    const spec=state.office_specs?.oversight_deputy||{
      emoji:'🕵️',
      title:'Заместитель главы Надзора за гондонами',
      threshold:200000,
    };
    const holder=(state.offices||[]).find(item=>item.office_key==='oversight_deputy');
    const card=document.createElement('article');
    card.id='oversightDeputyInstitutionV169';
    card.className=`institution-card ${holder?'active':''}`;
    card.tabIndex=0;
    card.setAttribute('role','button');
    card.setAttribute('aria-label','Открыть полномочия заместителя главы Надзора');
    card.innerHTML=`<span>${esc(spec.emoji||'🕵️')}</span><b>${esc(spec.title)}</b><small>${holder?`${esc(holder.name)} · ещё ${esc(holder.remaining||'действует')}`:`Свободно · порог ${fmt(spec.threshold)} карьеры · назначает Президент или глава Надзора через Госдуму`}</small>`;
    card.addEventListener('click',openDeputyPanel);
    card.addEventListener('keydown',event=>{
      if(event.key==='Enter'||event.key===' '){event.preventDefault();openDeputyPanel()}
    });
    grid.prepend(card);
  }

  function repairCrisisDom(){
    const conflict=document.getElementById('crisisConflict');
    if(conflict){
      conflict.style.height='auto';
      conflict.querySelectorAll('.crisis-panel').forEach(panel=>{
        panel.style.height='auto';
        panel.style.minHeight='0';
      });
    }
    document.querySelectorAll('#crisisV131 .crisis-panel').forEach(panel=>{
      panel.style.height='auto';
      panel.style.minHeight='0';
    });
  }

  async function load(){
    if(!chatId||loading)return;
    loading=true;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_ui170=${Date.now()}`,{
        cache:'no-store',
        headers:{'X-Telegram-Init-Data':tg?.initData||''},
      });
      const data=await response.json();
      if(response.ok&&data?.ok){
        state=data;
        deputyCard();
        placeDeputyPanel();
        patchAppointmentSelect();
      }
    }catch(_error){}
    finally{loading=false}
  }

  ensureOversightAssets();
  repairCrisisDom();
  load();

  document.addEventListener('click',event=>{
    if(event.target.closest?.('[data-tab="powers"]')){
      setTimeout(()=>{repairCrisisDom();deputyCard();placeDeputyPanel();load()},180);
    }
    if(event.target.closest?.('[data-power-action="appointment"]')){
      setTimeout(patchAppointmentSelect,30);
      setTimeout(patchAppointmentSelect,180);
    }
    if(event.target.closest?.('[data-open-oversight-deputy]')){
      openDeputyPanel();
      return;
    }
    if(event.target.closest?.('#refreshButton')){
      setTimeout(()=>{repairCrisisDom();placeDeputyPanel();load()},260);
    }
  },true);

  const observer=new MutationObserver(()=>{
    repairCrisisDom();
    if(state&&document.getElementById('institutionGrid')&&!document.getElementById('oversightDeputyInstitutionV169'))deputyCard();
    placeDeputyPanel();
    patchAppointmentSelect();
  });
  observer.observe(document.documentElement,{childList:true,subtree:true});
})();
