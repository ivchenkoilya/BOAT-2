(()=>{
  'use strict';
  if(window.__governmentElectionOfferDurationV154)return;
  window.__governmentElectionOfferDurationV154=true;

  let frame=0;

  function apply(){
    const brand=document.querySelector('.brand small');
    if(brand&&brand.textContent==='REALITY 153')brand.textContent='REALITY 154';

    document.querySelectorAll('#shadowModalV153 .v153-warning').forEach(node=>{
      const text='Предложение действует до завершения выборов. При принятии голос будет автоматически отдан тебе и заблокирован.';
      if(node.textContent!==text)node.textContent=text;
    });
  }

  function schedule(){
    cancelAnimationFrame(frame);
    frame=requestAnimationFrame(apply);
  }

  new MutationObserver(schedule).observe(document.documentElement,{subtree:true,childList:true});
  document.addEventListener('click',event=>{
    if(event.target.closest?.('[data-buy-vote]'))setTimeout(schedule,0);
  },true);
  schedule();
})();
