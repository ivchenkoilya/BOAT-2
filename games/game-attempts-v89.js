(()=>{
  'use strict';
  const originalFetch=window.fetch.bind(window);
  const rewrite=value=>{
    const text=String(value||'');
    if(text.includes('/games/api/state'))return text.replace('/games/api/state','/games-v89/api/state');
    if(text.includes('/games/api/start'))return text.replace('/games/api/start','/games-v89/api/start');
    return text;
  };
  window.fetch=(input,init)=>{
    if(typeof input==='string'||input instanceof URL){
      return originalFetch(rewrite(input),init);
    }
    if(input instanceof Request){
      const changed=rewrite(input.url);
      if(changed!==input.url)return originalFetch(new Request(changed,input),init);
    }
    return originalFetch(input,init);
  };
})();
