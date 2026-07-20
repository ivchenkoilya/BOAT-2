(async()=>{
'use strict';
const error=document.getElementById('startError');
const startButton=document.getElementById('start');
try{
  const response=await fetch('/games/night-hunter/game-v115.js?v=1151',{cache:'no-store'});
  if(!response.ok)throw new Error('не загружен визуальный слой Reality 115');
  let source=await response.text();
  const marker='const reality115Setup=String.raw`';
  const start=source.indexOf(marker);
  const end=source.indexOf('`;\n  const setupAnchor',start);
  if(start<0||end<0)throw new Error('не найдена точка подготовки детализированного цеха');
  const bodyStart=start+marker.length;
  const prepared=source.slice(bodyStart,end).replace(/\\n/g,'\\\\n');
  source=source.slice(0,bodyStart)+prepared+source.slice(end);
  await (0,eval)(source);
}catch(e){
  if(error){error.textContent='Reality 115 не загрузилась: '+e.message;error.style.display='block'}
  if(startButton){startButton.disabled=true;startButton.textContent='ОШИБКА ЗАГРУЗКИ'}
}
})();
