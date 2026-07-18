(()=>{
  'use strict';

  function patchHelp(){
    const scroll=document.querySelector('#raidHelpV61 .raid-v61-help-scroll');
    if(!scroll)return;

    const current=scroll.innerHTML;
    const next=current
      .replaceAll('ТАКТИЧЕСКИЙ РЕЙД · REALITY 61','ТАКТИЧЕСКИЙ РЕЙД · REALITY 65')
      .replaceAll('У босса 75 000 HP','У босса 100 000 HP')
      .replaceAll('способность роли — 5','способность роли — 4')
      .replaceAll('Максимум шкалы — 120','Максимум шкалы — 150');

    if(next!==current)scroll.innerHTML=next;
  }

  patchHelp();
  window.setInterval(()=>{
    const overlay=document.getElementById('raidHelpV61');
    if(overlay?.classList.contains('open'))patchHelp();
  },500);
})();
