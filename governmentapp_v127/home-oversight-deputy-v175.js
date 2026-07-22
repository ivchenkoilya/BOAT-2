(()=>{
  'use strict';
  if(window.__governmentHomeOversightDeputyV175)return;
  window.__governmentHomeOversightDeputyV175=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  let state=null;
  let loading=false;
  let timers=[];

  function clearTimers(){
    timers.forEach(clearTimeout);
    timers=[];
  }

  function scheduleRender(){
    clearTimers();
    [0,180,520,1000,1800].forEach(delay=>timers.push(setTimeout(renderCard,delay)));
  }

  function cardHtml(spec,office){
    if(!office){
      return `<article class="office-card vacant" id="homeOversightDeputyV175" data-office-key="oversight_deputy"><div class="office-title"><span>${esc(spec.emoji||'🕵️')}</span><div><b>${esc(spec.title||'Заместитель главы Надзора за гондонами')}</b><small>Порог: ${fmt(spec.threshold)} карьеры</small></div></div><div class="office-person">Должность свободна</div><div class="office-meta">Президент назначает напрямую; глава Надзора предлагает кандидатуру через Госдуму.</div></article>`;
    }
    const trust=Math.max(0,Math.min(100,Number(office.trust)||0));
    return `<article class="office-card" id="homeOversightDeputyV175" data-office-key="oversight_deputy"><div class="office-title"><span>${esc(office.emoji||spec.emoji||'🕵️')}</span><div><b>${esc(office.title||spec.title||'Заместитель главы Надзора за гондонами')}</b><small>Полномочия: ещё ${esc(office.remaining||'действуют')}</small></div></div><div class="office-person">${esc(office.name||'Участник')}</div><div class="office-meta">⭐ ${fmt(office.career_points)} · доверие ${fmt(office.trust)}%</div><div class="trust"><i style="width:${trust}%"></i></div></article>`;
  }

  function renderCard(){
    const grid=document.getElementById('officeGrid');
    if(!grid||!state)return;
    document.getElementById('homeOversightDeputyV175')?.remove();
    const spec=state.office_specs?.oversight_deputy;
    if(!spec)return;
    const office=(state.offices||[]).find(item=>item.office_key==='oversight_deputy'&&Number(item.seat_no||1)===1);
    grid.insertAdjacentHTML('beforeend',cardHtml(spec,office));
  }

  async function loadState(){
    if(!chatId||loading)return;
    loading=true;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_home175=${Date.now()}`,{
        cache:'no-store',
        headers:{'X-Telegram-Init-Data':tg?.initData||''},
      });
      const data=await response.json();
      if(response.ok&&data?.ok){
        state=data;
        scheduleRender();
      }
    }catch(_error){}
    finally{loading=false}
  }

  document.addEventListener('click',event=>{
    if(event.target.closest?.('#refreshButton')){
      setTimeout(loadState,220);
      setTimeout(loadState,850);
    }
    if(event.target.closest?.('[data-tab="home"]')){
      setTimeout(renderCard,120);
      setTimeout(loadState,420);
    }
  },true);

  window.addEventListener('pageshow',()=>setTimeout(loadState,120));
  document.addEventListener('visibilitychange',()=>{
    if(!document.hidden)setTimeout(loadState,120);
  });

  loadState();
})();
