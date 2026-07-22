(()=>{
  'use strict';
  if(window.__financeRealtimeV161)return;
  window.__financeRealtimeV161=true;

  const rawFetch=window.fetch.bind(window);
  let refreshTimers=[];

  function markVersion(){
    const brand=document.querySelector('.brand small');
    if(brand)brand.textContent='ГЛАВНЫЙ ГЕРОЙ · REALITY 161';
  }

  function refreshBurst(){
    refreshTimers.forEach(clearTimeout);
    refreshTimers=[40,220,650,1400].map(delay=>setTimeout(()=>{
      markVersion();
      document.getElementById('refreshButton')?.click();
    },delay));
  }

  window.fetch=async function(input,init={}){
    const method=String(init?.method||'GET').toUpperCase();
    let target;
    try{target=new URL(typeof input==='string'?input:input?.url||String(input),location.origin)}catch(_error){return rawFetch(input,init)}
    const financeApi=target.pathname.startsWith('/finance-v')&&target.pathname.includes('/api/');
    if(method==='GET'&&financeApi)target.searchParams.set('_rt161',String(Date.now()));
    const nextInput=typeof input==='string'||input instanceof URL
      ?target.pathname+target.search
      :input;
    const response=await rawFetch(nextInput,{...init,cache:financeApi?'no-store':init?.cache});
    if(method==='POST'&&financeApi){
      response.clone().json().then(data=>{if(data?.ok)refreshBurst()}).catch(()=>{});
    }
    return response;
  };

  document.addEventListener('click',event=>{
    if(event.target.closest?.('#modalConfirm'))setTimeout(refreshBurst,120);
    if(event.target.closest?.('[data-nav="deposits"],[data-open="deposits"],[data-nav="portfolio"],[data-open="portfolio"]'))setTimeout(refreshBurst,80);
  },true);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshBurst();});
  window.addEventListener('focus',refreshBurst);

  markVersion();
})();