(()=>{
  'use strict';
  if(window.__governmentCreatorControlV151)return;
  window.__governmentCreatorControlV151=true;

  let frame=0;

  function moveTheftToTreasury(){
    const theft=document.getElementById('crisisTheft');
    const taxPolicy=document.getElementById('taxPolicy');
    if(!theft||!taxPolicy)return;

    let host=document.getElementById('treasuryTheftV151');
    if(!host){
      host=document.createElement('section');
      host.id='treasuryTheftV151';
      host.className='treasury-theft-v151';
      host.innerHTML=`<div class="section-head"><div><small>ТЕНЕВАЯ КАЗНА</small><h2>Попытка хищения</h2></div><span class="treasury-theft-mark-v151">🕶</span></div><div id="treasuryTheftContentV151"></div>`;
      const contributions=document.getElementById('treasuryContributionV150');
      if(contributions)contributions.insertAdjacentElement('beforebegin',host);
      else taxPolicy.insertAdjacentElement('afterend',host);
    }

    const content=document.getElementById('treasuryTheftContentV151');
    if(content&&theft.parentElement!==content)content.appendChild(theft);

    const crisisHeading=document.querySelector('#crisisV131 .crisis-heading');
    if(crisisHeading){
      const small=crisisHeading.querySelector('small');
      const title=crisisHeading.querySelector('h2');
      if(small)small.textContent='ПОЛИТИЧЕСКИЕ КРИЗИСЫ';
      if(title)title.textContent='Борьба за власть';
    }
    document.querySelector('#crisisV131 .crisis-grid')?.classList.add('theft-moved-v151');
  }

  function markCreatorMode(){
    const banner=document.getElementById('roleAccessBannerV148');
    if(!banner?.classList.contains('creator-mode-v151'))return;
    document.documentElement.classList.add('government-creator-mode-v151');
  }

  function apply(){
    moveTheftToTreasury();
    markCreatorMode();
  }

  function schedule(){
    cancelAnimationFrame(frame);
    frame=requestAnimationFrame(apply);
  }

  const observer=new MutationObserver(schedule);
  observer.observe(document.documentElement,{subtree:true,childList:true});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)schedule();});
  window.addEventListener('focus',schedule);
  schedule();
})();