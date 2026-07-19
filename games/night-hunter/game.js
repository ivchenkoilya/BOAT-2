(()=>{
  'use strict';
  const errorBox=document.getElementById('startError');
  const startButton=document.getElementById('start');
  const script=document.createElement('script');
  script.src='/games/night-hunter/game-v96.js?v=96';
  script.async=true;
  script.onerror=()=>{
    if(errorBox){errorBox.style.display='block';errorBox.textContent='Не удалось загрузить игровую логику Reality 96.'}
    if(startButton){startButton.disabled=true;startButton.textContent='ОШИБКА ЗАГРУЗКИ'}
  };
  document.head.appendChild(script);
})();
