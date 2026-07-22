(()=>{
  'use strict';
  if(window.__governmentUiHotfixV169)return;
  window.__governmentUiHotfixV169=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  let state=null;
  let loading=false;

  function ensureOversightAssets(){
    if(!document.querySelector('link[href*="oversight-deputy-v167.css"]')){
      const link=document.createElement('link');
      link.rel='stylesheet';
      link.href='/government-v167/oversight-deputy-v167.css?v=169';
      document.head.appendChild(link);
    }
    if(!window.__oversightDeputyV167&&!document.querySelector('script[src*="oversight-deputy-v167.js"]')){
      const script=document.createElement('script');
      script.src='/government-v167/oversight-deputy-v167.js?v=169';
      script.defer=true;
      document.body.appendChild(script);
    }
  }

  function openOversight(){
    const tab=document.querySelector('[data-tab="oversight"]');
    tab?.click();
    setTimeout(()=>{
      const target=document.getElementById('oversightDeputyV167')||document.querySelector('.screen[data-screen="oversight"]');
      target?.scrollIntoView({behavior:'smooth',block:'start'});
    },420);
  }

  function quickDeputyCard(){
    const hero=document.getElementById('powerHero');
    if(!hero||!state)return;
    document.getElementById('oversightDeputyQuickV169')?.remove();
    const spec=state.office_specs?.oversight_deputy||{emoji:'🕵️',title:'Заместитель главы Надзора за гондонами',threshold:200000};
    const holder=(state.offices||[]).find(item=>item.office_key==='oversight_deputy');
    const card=document.createElement('article');
    card.id='oversightDeputyQuickV169';
    card.className='panel oversight-deputy-quick-v169';
    card.innerHTML=`<div class="panel-title"><span>${esc(spec.emoji||'🕵️')}</span><div><b>${esc(spec.title)}</b><small>${holder?`Должность занимает ${esc(holder.name)} · осталось ${esc(holder.remaining||'действует')}`:`Новая должность свободна · назначение проходит через голосование Госдумы`}</small></div></div><button class="action wide" type="button" data-open-oversight-deputy>🕵️ ОТКРЫТЬ ПАНЕЛЬ ЗАМЕСТИТЕЛЯ</button>`;
    hero.insertAdjacentElement('afterend',card);
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
    card.setAttribute('aria-label','Открыть управление заместителя главы Надзора');
    card.innerHTML=`<span>${esc(spec.emoji||'🕵️')}</span><b>${esc(spec.title)}</b><small>${holder?`${esc(holder.name)} · ещё ${esc(holder.remaining||'действует')}`:`Свободно · порог ${fmt(spec.threshold)} карьеры · назначение через Госдуму`}</small>`;
    card.addEventListener('click',openOversight);
    card.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();openOversight()}});
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
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_ui169=${Date.now()}`,{
        cache:'no-store',
        headers:{'X-Telegram-Init-Data':tg?.initData||''},
      });
      const data=await response.json();
      if(response.ok&&data?.ok){state=data;quickDeputyCard();deputyCard()}
    }catch(_error){}
    finally{loading=false}
  }

  ensureOversightAssets();
  repairCrisisDom();
  load();

  document.addEventListener('click',event=>{
    if(event.target.closest?.('[data-tab="powers"]'))setTimeout(()=>{repairCrisisDom();quickDeputyCard();deputyCard();load()},180);
    if(event.target.closest?.('[data-open-oversight-deputy]')){openOversight();return;}
    if(event.target.closest?.('#refreshButton'))setTimeout(()=>{repairCrisisDom();load()},260);
  },true);

  const observer=new MutationObserver(()=>{
    repairCrisisDom();
    if(state&&document.getElementById('powerHero')&&!document.getElementById('oversightDeputyQuickV169'))quickDeputyCard();
    if(state&&document.getElementById('institutionGrid')&&!document.getElementById('oversightDeputyInstitutionV169'))deputyCard();
  });
  observer.observe(document.documentElement,{childList:true,subtree:true});
})();
