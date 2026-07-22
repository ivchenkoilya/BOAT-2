(()=>{
  'use strict';
  if(window.__governmentStateBrokerV167)return;
  window.__governmentStateBrokerV167=true;

  const nativeFetch=window.fetch.bind(window);
  const STATE_PATH='/government-v127/api/state';
  const CACHE_MS=2500;
  const STALE_MS=120000;
  const NETWORK_TIMEOUT_MS=25000;
  let cached=null;
  let cachedKey='';
  let cachedAt=0;
  let inflight=null;
  let inflightKey='';

  const methodOf=init=>String(init?.method||'GET').toUpperCase();
  const urlOf=input=>{
    try{return new URL(typeof input==='string'?input:input?.url||'',location.href)}catch(_error){return null}
  };
  const headersOf=init=>{
    try{return new Headers(init?.headers||{})}catch(_error){return new Headers()}
  };
  const isGovernmentMutation=(url,init)=>Boolean(url&&methodOf(init)!=='GET'&&url.pathname.startsWith('/government-')&&url.pathname.includes('/api/'));
  const isStateRequest=(url,init)=>Boolean(url&&methodOf(init)==='GET'&&url.pathname===STATE_PATH);
  const stateKey=(url,init)=>`${url.searchParams.get('chat_id')||''}:${headersOf(init).get('X-Telegram-Init-Data')||''}`;
  const cloneResponse=snapshot=>new Response(snapshot.body,{status:snapshot.status,statusText:snapshot.statusText,headers:snapshot.headers});

  function publish(snapshot,stale=false){
    if(!snapshot?.data?.ok)return;
    window.__governmentStateV167=snapshot.data;
    window.__governmentStateV167At=Date.now();
    window.__governmentTreasuryState=snapshot.data;
    window.__governmentTreasuryStateAt=Date.now();
    document.dispatchEvent(new CustomEvent('government:state',{detail:snapshot.data}));
    if(stale)document.dispatchEvent(new CustomEvent('government:state-stale',{detail:snapshot.data}));
  }

  async function networkSnapshot(input,init,key){
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),NETWORK_TIMEOUT_MS);
    const requestInit={...(init||{}),cache:'no-store',signal:controller.signal};
    try{
      const response=await nativeFetch(input,requestInit);
      const body=await response.text();
      let data=null;
      try{data=JSON.parse(body)}catch(_error){}
      const snapshot={
        body,
        data,
        status:response.status,
        statusText:response.statusText,
        headers:Array.from(response.headers.entries()),
        key,
        savedAt:Date.now()
      };
      if(response.ok&&data?.ok){
        cached=snapshot;cachedKey=key;cachedAt=Date.now();publish(snapshot,false);
      }
      return snapshot;
    }finally{clearTimeout(timeout)}
  }

  function stateSnapshot(input,init,force=false){
    const url=urlOf(input);
    const key=stateKey(url,init);
    const now=Date.now();
    if(!force&&cached&&cachedKey===key&&now-cachedAt<CACHE_MS)return Promise.resolve(cached);
    if(inflight&&inflightKey===key)return inflight;
    const previous=cached&&cachedKey===key&&now-cachedAt<STALE_MS?cached:null;
    const promise=networkSnapshot(input,init,key)
      .catch(error=>{
        if(previous){publish(previous,true);return previous}
        throw error;
      })
      .finally(()=>{
        if(inflight===promise){inflight=null;inflightKey=''}
      });
    inflight=promise;inflightKey=key;
    return promise;
  }

  window.fetch=function(input,init={}){
    const url=urlOf(input);
    if(isStateRequest(url,init)){
      const force=Boolean(window.__governmentForceNextStateV167||url.searchParams.has('_force_v167'));
      window.__governmentForceNextStateV167=false;
      const cleanInit={...(init||{})};
      delete cleanInit.signal;
      return stateSnapshot(input,cleanInit,force).then(cloneResponse);
    }
    if(isGovernmentMutation(url,init)){
      return nativeFetch(input,init).then(response=>{
        if(response.ok){cached=null;cachedKey='';cachedAt=0;window.__governmentTreasuryState=null;window.__governmentTreasuryStateAt=0}
        return response;
      });
    }
    return nativeFetch(input,init);
  };

  window.__governmentFetchStateV167=async function(force=false){
    const tg=window.Telegram?.WebApp;
    const params=new URLSearchParams(location.search);
    const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
    const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
    if(!chatId)throw new Error('Не определена государственная беседа.');
    const suffix=force?`&_force_v167=${Date.now()}`:'';
    const response=await window.fetch(`${STATE_PATH}?chat_id=${encodeURIComponent(chatId)}${suffix}`,{
      cache:'no-store',headers:{'X-Telegram-Init-Data':tg?.initData||''}
    });
    const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
    if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось обновить государство.');
    return data;
  };
})();
