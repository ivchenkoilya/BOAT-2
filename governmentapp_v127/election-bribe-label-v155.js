(()=>{
  'use strict';
  if(window.__governmentElectionBribeLabelV155)return;
  window.__governmentElectionBribeLabelV155=true;

  let frame=0;

  function apply(){
    document.querySelectorAll('[data-buy-vote]').forEach(button=>{
      const text='😈 ПОДКУПИТЬ ГОЛОСА';
      if(button.textContent!==text)button.textContent=text;
    });

    const modal=document.getElementById('shadowModalV153');
    if(modal&&!modal.hidden){
      const icon=modal.querySelector('.v153-modal-icon');
      if(icon&&icon.textContent!=='😈')icon.textContent='😈';
      const title=modal.querySelector('#shadowModalContentV153 h2');
      if(title&&title.textContent!=='Подкупить голоса')title.textContent='Подкупить голоса';
    }
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
