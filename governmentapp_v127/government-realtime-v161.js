(()=>{
  'use strict';
  if(window.__governmentRealtimeV161)return;
  window.__governmentRealtimeV161=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'X-Telegram-Init-Data':tg?.initData||''};
  const rawFetch=window.fetch.bind(window);
  let stateSignature='';
  let polling=false;
  let refreshTimers=[];

  function markVersion(){
    const brand=document.querySelector('.brand small');
    if(brand)brand.textContent='REALITY 161';
  }

  function refreshBurst(){
    refreshTimers.forEach(clearTimeout);
    refreshTimers=[0,140,420,950].map(delay=>setTimeout(()=>{
      markVersion();
      document.getElementById('refreshButton')?.click();
    },delay));
  }

  function signature(data){
    const shadow=data?.election_shadow_v153||{};
    const crisis=data?.crisis_v131||{};
    const normalize=(items,fields)=>(Array.isArray(items)?items:[])
      .map(item=>fields.map(field=>item?.[field]??''))
      .sort((a,b)=>String(a[0]).localeCompare(String(b[0])));
    return JSON.stringify({
      offers:normalize(shadow.incoming_offers,['offer_id','status','amount','expires_at','buyer_revealed','secret_message']),
      campaigns:normalize(shadow.campaigns,['election_id','offers','pending','accepted','reported','spent']),
      sold:normalize(shadow.my_sold_vote_history,['offer_id','status','amount','accepted_at','candidate_id']),
      offices:[...(data?.user?.offices||[])].sort(),
      theftCan:Boolean(crisis?.theft?.can_attempt),
      theftItems:normalize(crisis?.theft?.items,['theft_id','status','investigations','amount']),
      treasury:Number(data?.treasury?.balance||0)
    });
  }

  async function poll(){
    if(!chatId||document.hidden||polling)return;
    polling=true;
    try{
      const response=await rawFetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_rt161=${Date.now()}`,{
        cache:'no-store',headers
      });
      const data=await response.json();
      if(response.ok&&data?.ok){
        const next=signature(data);
        if(stateSignature&&next!==stateSignature)refreshBurst();
        stateSignature=next;
      }
    }catch(_error){}
    finally{polling=false;markVersion();}
  }

  window.fetch=async function(input,init={}){
    const method=String(init?.method||'GET').toUpperCase();
    let target;
    try{target=new URL(typeof input==='string'?input:input?.url||String(input),location.origin)}catch(_error){return rawFetch(input,init)}
    const governmentState=method==='GET'&&target.pathname==='/government-v127/api/state';
    if(governmentState)target.searchParams.set('_rt161',String(Date.now()));
    const nextInput=typeof input==='string'||input instanceof URL
      ?target.pathname+target.search
      :input;
    const response=await rawFetch(nextInput,{...init,cache:governmentState?'no-store':init?.cache});
    if(method==='POST'&&/^\/government-v(?:131|153|156)\/api\/action$/.test(target.pathname)){
      response.clone().json().then(data=>{if(data?.ok){setTimeout(refreshBurst,80);setTimeout(poll,500)}}).catch(()=>{});
    }
    return response;
  };

  document.addEventListener('click',event=>{
    if(event.target.closest?.('[data-tab="elections"],[data-tab="powers"],[data-tab="treasury"]')){
      setTimeout(poll,40);
      setTimeout(refreshBurst,120);
    }
  },true);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden){poll();refreshBurst();}});
  window.addEventListener('focus',()=>{poll();refreshBurst();});

  markVersion();
  poll();
  setInterval(poll,2000);
})();