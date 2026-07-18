(()=>{
  'use strict';

  const patched=new WeakSet();

  function stabilize(element){
    if(!element||patched.has(element))return;
    const descriptor=Object.getOwnPropertyDescriptor(Element.prototype,'innerHTML');
    if(!descriptor?.get||!descriptor?.set)return;
    let last=descriptor.get.call(element);
    Object.defineProperty(element,'innerHTML',{
      configurable:true,
      get(){return descriptor.get.call(this)},
      set(value){
        const next=String(value);
        if(next===last)return;
        last=next;
        descriptor.set.call(this,next);
      }
    });
    patched.add(element);
  }

  function scan(){
    stabilize(document.getElementById('raidVictoryRanking'));
    document.querySelectorAll('.raid-v60-victory-stats').forEach(stabilize);
  }

  scan();
  new MutationObserver(scan).observe(document.body,{childList:true,subtree:true});
})();
