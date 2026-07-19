(async()=>{
  'use strict';
  const letters=['a','b','c','d','e','f','g'];
  const paths=letters.map(letter=>`/games/night-hunter/game-v95-${letter}.part?v=95`);
  const errorBox=document.getElementById('startError');
  const startButton=document.getElementById('start');
  try{
    const responses=await Promise.all(paths.map(path=>fetch(path,{cache:'no-store'})));
    for(const response of responses){
      if(!response.ok)throw new Error(`Файл игры не найден: HTTP ${response.status}`);
    }
    const source=(await Promise.all(responses.map(response=>response.text()))).join('');
    const blob=new Blob([source],{type:'text/javascript'});
    const blobUrl=URL.createObjectURL(blob);
    const script=document.createElement('script');
    script.src=blobUrl;
    script.onload=()=>URL.revokeObjectURL(blobUrl);
    script.onerror=()=>{
      URL.revokeObjectURL(blobUrl);
      if(errorBox){errorBox.style.display='block';errorBox.textContent='Не удалось запустить игровую логику.'}
      if(startButton)startButton.disabled=true;
    };
    document.head.appendChild(script);
  }catch(error){
    if(errorBox){errorBox.style.display='block';errorBox.textContent='Не удалось загрузить игру: '+(error?.message||error)}
    if(startButton){startButton.disabled=true;startButton.textContent='ОШИБКА ЗАГРУЗКИ'}
  }
})();
